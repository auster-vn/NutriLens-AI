from datetime import UTC, datetime
from hashlib import sha256

from app.auth.security import get_optional_user
from app.core.database import get_session
from app.core.models import ProductLabelExtraction, User, UserProfile
from app.core.security import validate_barcode
from app.products.label_extraction import EXTRACTOR_VERSION, LabelImageError, OcrUnavailableError, extract_label
from app.products.openfoodfacts import _completeness_score
from app.products.scoring import _num, score_product
from app.products.service import get_or_fetch_product, product_to_schema, score_cached_product, upsert_product
from app.schemas.products import (
    LabelExtractionConfirmRequest,
    LabelExtractionOut,
    ProductCompareOut,
    ProductCompareRequest,
    ProductOut,
    ProductScanRequest,
    ProductScoreOut,
    ProductScoreRequest,
    ProductWithScore,
    UserProfileInput,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/products", tags=["products"])
MAX_LABEL_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_LABEL_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def extraction_to_schema(extraction: ProductLabelExtraction) -> LabelExtractionOut:
    data = extraction.extracted_json or {}
    return LabelExtractionOut(
        id=extraction.id,
        barcode=extraction.barcode,
        status=extraction.status,
        raw_text=extraction.raw_text,
        ingredients_text=data.get("ingredients_text"),
        allergens=data.get("allergens") or [],
        additives=data.get("additives") or [],
        nutriments=data.get("nutriments") or {},
        confidence=extraction.confidence,
        validation_issues=extraction.validation_issues or [],
        ocr_provider=extraction.ocr_provider,
        extractor_version=extraction.extractor_version,
        words=extraction.words_json or [],
        preprocessing=extraction.preprocessing_json or {},
        provider_runs=extraction.provider_runs_json or [],
        blocks=data.get("blocks") or [],
        fields=data.get("fields") or {},
        ingredient_entities=data.get("ingredient_entities") or [],
    )


@router.post("/scan", response_model=ProductWithScore)
async def scan_product(
    request: ProductScanRequest,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> ProductWithScore:
    barcode = validate_barcode(request.barcode, request.barcode_format)
    profile = request.user_profile
    if profile is None and user is not None:
        stored_profile = await session.get(UserProfile, user.id)
        if stored_profile is not None:
            profile = UserProfileInput(
                age_group=stored_profile.age_group,
                goal=stored_profile.goal,
                allergies=stored_profile.allergies or [],
                diet=stored_profile.diet,
                disliked_ingredients=stored_profile.disliked_ingredients or [],
                budget_daily=stored_profile.budget_daily,
                biological_sex=stored_profile.biological_sex,
                age=stored_profile.age,
                height_cm=stored_profile.height_cm,
                weight_kg=stored_profile.weight_kg,
                activity_level=stored_profile.activity_level,
                target_weight_loss_kg_week=stored_profile.target_weight_loss_kg_week,
            )
    profile = profile or UserProfileInput()
    product = await get_or_fetch_product(session, barcode)
    score = await score_cached_product(
        session,
        product,
        profile,
        record_scan=user is not None,
        user_id=user.id if user else None,
    )
    return ProductWithScore(product=product_to_schema(product), score=score)


@router.post("/label-extractions", response_model=LabelExtractionOut, status_code=201)
async def create_label_extraction(
    barcode: str = Form(...),
    image: UploadFile = File(...),
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> LabelExtractionOut:
    normalized_barcode = validate_barcode(barcode)
    if image.content_type not in ALLOWED_LABEL_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Label image must be JPEG, PNG, or WebP.")
    image_bytes = await image.read(MAX_LABEL_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_LABEL_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Label image must not exceed 8 MB.")
    try:
        ocr, parsed = await extract_label(image_bytes)
    except LabelImageError as exc:
        if str(exc).startswith("Label image quality is too low"):
            raise HTTPException(
                status_code=422,
                detail={"code": "LABEL_IMAGE_QUALITY", "message": "Label image quality is too low."},
            ) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OcrUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    extracted_json = {
        "ingredients_text": parsed.ingredients_text,
        "allergens": parsed.allergens,
        "additives": parsed.additives,
        "nutriments": parsed.nutriments,
        "ingredient_entities": parsed.ingredient_entities,
        "fields": parsed.fields,
        "blocks": parsed.blocks,
    }
    extraction = ProductLabelExtraction(
        barcode=normalized_barcode,
        user_id=user.id if user else None,
        image_sha256=sha256(image_bytes).hexdigest(),
        image_mime=image.content_type,
        ocr_provider=ocr.provider,
        extractor_version=EXTRACTOR_VERSION,
        raw_text=ocr.text,
        words_json=[word.as_dict() for word in ocr.words],
        preprocessing_json=ocr.preprocessing.as_dict() if ocr.preprocessing else {},
        provider_runs_json=ocr.provider_runs,
        extracted_json=extracted_json,
        confidence=parsed.confidence,
        validation_issues=parsed.validation_issues,
    )
    session.add(extraction)
    await session.commit()
    await session.refresh(extraction)
    return extraction_to_schema(extraction)


@router.post("/label-extractions/{extraction_id}/confirm", response_model=ProductOut)
async def confirm_label_extraction(
    extraction_id: str,
    request: LabelExtractionConfirmRequest,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    extraction = await session.get(ProductLabelExtraction, extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Label extraction not found.")
    if extraction.user_id is not None and (user is None or extraction.user_id != user.id):
        raise HTTPException(status_code=403, detail="You cannot confirm another user's extraction.")
    product_data = {
        "barcode": extraction.barcode,
        "name": request.name.strip(),
        "brand": request.brand.strip() if request.brand else None,
        "categories": [],
        "ingredients_text": request.ingredients_text,
        "allergens": request.allergens,
        "additives": request.additives,
        "nutriments": request.nutriments,
        "nutriscore": None,
        "ecoscore": None,
        "image_url": None,
        "source": "package_ocr_user_confirmed",
        "raw_summary": {
            "extraction_id": extraction.id,
            "image_sha256": extraction.image_sha256,
            "ocr_provider": extraction.ocr_provider,
            "extractor_version": extraction.extractor_version,
            "confidence": extraction.confidence,
        },
    }
    product_data["completeness_score"] = _completeness_score(product_data)
    product = await upsert_product(session, product_data)
    extraction_data = dict(extraction.extracted_json or {})
    extraction_data["confirmed"] = {
        "name": request.name.strip(),
        "brand": request.brand.strip() if request.brand else None,
        "ingredients_text": request.ingredients_text,
        "allergens": request.allergens,
        "additives": request.additives,
        "nutriments": request.nutriments,
    }
    extraction.extracted_json = extraction_data
    extraction.status = "confirmed"
    extraction.confirmed_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    return product_to_schema(product)


@router.get("/{barcode}", response_model=ProductOut)
async def get_product(barcode: str, session: AsyncSession = Depends(get_session)) -> ProductOut:
    product = await get_or_fetch_product(session, validate_barcode(barcode))
    return product_to_schema(product)


@router.post("/score", response_model=ProductScoreOut)
async def score_product_payload(request: ProductScoreRequest) -> ProductScoreOut:
    return score_product(
        request.nutriments,
        request.allergens,
        request.additives,
        request.nutriscore,
        request.user_profile,
        request.ingredients_text,
    )


@router.post("/compare", response_model=ProductCompareOut)
async def compare_products(
    request: ProductCompareRequest,
    session: AsyncSession = Depends(get_session),
) -> ProductCompareOut:
    product_a = await get_or_fetch_product(session, validate_barcode(request.barcode_a))
    product_b = await get_or_fetch_product(session, validate_barcode(request.barcode_b))
    score_a = await score_cached_product(session, product_a, request.user_profile)
    score_b = await score_cached_product(session, product_b, request.user_profile)

    dims = _compare_dimensions(product_a.nutriments or {}, product_b.nutriments or {})
    if score_a.score == score_b.score:
        recommendation = "Hai sản phẩm khá cân bằng; hãy ưu tiên dị ứng, khẩu vị và dữ liệu còn thiếu."
    else:
        better = "A" if score_a.score > score_b.score else "B"
        recommendation = f"Nếu ưu tiên {request.user_profile.goal}, chọn sản phẩm {better}."

    return ProductCompareOut(
        product_a=ProductWithScore(product=product_to_schema(product_a), score=score_a),
        product_b=ProductWithScore(product=product_to_schema(product_b), score=score_b),
        recommendation=recommendation,
        dimensions=dims,
    )


def _compare_dimensions(a: dict, b: dict) -> list[dict]:
    labels = {
        "sugars_100g": "Đường",
        "energy-kcal_100g": "Calories",
        "proteins_100g": "Protein",
        "sodium_100g": "Sodium",
        "saturated-fat_100g": "Chất béo bão hòa",
        "fiber_100g": "Chất xơ",
    }
    return [
        {"key": key, "label": label, "a": _num(a, key), "b": _num(b, key)}
        for key, label in labels.items()
    ]
