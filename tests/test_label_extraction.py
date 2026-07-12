from collections.abc import AsyncIterator

import pytest
from app.core.database import get_session
from app.core.models import Base
from app.main import app
from app.products.label_extraction import LabelExtractionResult, OcrResult, parse_label_text
from app.products.label_ocr.contracts import OcrWord, PreprocessingMetadata
from app.products.router import MAX_LABEL_IMAGE_BYTES
from app.products.service import get_or_fetch_product
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def test_parse_vietnamese_label_extracts_structured_fields():
    result = parse_label_text(
        """THÀNH PHẦN: Sữa bò 65%, đường, bột whey, chất ổn định E407, E 412.
DINH DƯỠNG trên 100 g
Năng lượng 120 kcal
Chất đạm 4,2 g
Carbohydrate 18 g
Đường 12,5 g
Chất béo 3,1 g
Chất béo bão hòa 1,8 g
Natri 75 mg
Bảo quản nơi khô ráo""",
        0.9,
    )

    assert result.ingredients_text == "Sữa bò 65%, đường, bột whey, chất ổn định E407, E 412"
    assert result.additives == ["E407", "E412"]
    assert "milk" in result.allergens
    assert result.nutriments["proteins_100g"] == 4.2
    assert result.nutriments["sodium_100g"] == 0.075
    assert result.nutriments["energy-kcal_100g"] == 120
    assert result.confidence > 0.7


def test_parse_label_reports_impossible_nutrition_values():
    result = parse_label_text(
        "Ingredients: water, sugar\nNutrition\nCarbohydrate 10 g\nSugars 20 g\nFat 4 g\nSaturated fat 8 g",
    )

    assert "Đường lớn hơn tổng carbohydrate." in result.validation_issues
    assert "Chất béo bão hòa lớn hơn tổng chất béo." in result.validation_issues


@pytest.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_label_extraction_and_confirmation_flow(api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def fake_extract(_: bytes):
        return (
            OcrResult(
                "Ingredients: oats, milk",
                0.94,
                words=[OcrWord("Ingredients", 0.95, (10, 20, 120, 42), "tesseract", 1, 1)],
                provider_runs=[{"provider": "tesseract", "status": "succeeded"}],
                preprocessing=PreprocessingMetadata(
                    1000,
                    800,
                    1000,
                    800,
                    120,
                    130,
                    55,
                    0.02,
                    0,
                    0.9,
                    transforms=["clahe", "adaptive_threshold"],
                ),
            ),
            LabelExtractionResult("oats, milk", ["milk"], [], {"proteins_100g": 4.0}, 0.9, []),
        )

    monkeypatch.setattr("app.products.router.extract_label", fake_extract)
    extraction_response = await api_client.post(
        "/api/products/label-extractions",
        data={"barcode": "4006381333931"},
        files={"image": ("label.png", b"fake-image", "image/png")},
    )
    assert extraction_response.status_code == 201
    extraction = extraction_response.json()
    assert extraction["ingredients_text"] == "oats, milk"
    assert extraction["status"] == "needs_review"
    assert extraction["words"][0]["bbox"] == [10, 20, 120, 42]
    assert extraction["preprocessing"]["quality_score"] == 0.9
    assert extraction["provider_runs"][0]["provider"] == "tesseract"

    confirmation_response = await api_client.post(
        f"/api/products/label-extractions/{extraction['id']}/confirm",
        json={
            "name": "Oat Drink",
            "brand": "Test Brand",
            "ingredients_text": extraction["ingredients_text"],
            "allergens": extraction["allergens"],
            "nutriments": extraction["nutriments"],
        },
    )
    assert confirmation_response.status_code == 200
    product = confirmation_response.json()
    assert product["source"] == "package_ocr_user_confirmed"
    assert product["name"] == "Oat Drink"


async def test_label_upload_rejects_oversized_files(api_client: AsyncClient):
    response = await api_client.post(
        "/api/products/label-extractions",
        data={"barcode": "4006381333931"},
        files={"image": ("label.png", b"x" * (MAX_LABEL_IMAGE_BYTES + 1), "image/png")},
    )

    assert response.status_code == 413


async def test_admin_exposes_label_ocr_dashboard(api_client: AsyncClient):
    response = await api_client.get("/api/admin/label-ocr/dashboard", headers={"X-Admin-Key": "dev-admin-key"})

    assert response.status_code == 200
    assert response.json()["production"]["extraction_count"] == 0


async def test_confirmed_ocr_product_is_not_refetched_from_open_food_facts(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.models import ProductCache

    session_override = app.dependency_overrides[get_session]
    session_iterator = session_override()
    session = await anext(session_iterator)
    session.add(ProductCache(barcode="96385074", name="Verified label", source="package_ocr_user_confirmed"))
    await session.commit()

    async def fail_fetch(_: str):
        raise AssertionError("confirmed OCR products must not be refetched")

    monkeypatch.setattr("app.products.service.fetch_product", fail_fetch)
    product = await get_or_fetch_product(session, "96385074")
    assert product.name == "Verified label"
    await session_iterator.aclose()
