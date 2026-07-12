from app.auth.security import get_optional_user
from app.core.database import get_session
from app.core.models import User, UserProfile
from app.core.security import validate_barcode
from app.products.scoring import _num, score_product
from app.products.service import get_or_fetch_product, product_to_schema, score_cached_product
from app.schemas.products import (
    ProductCompareOut,
    ProductCompareRequest,
    ProductOut,
    ProductScanRequest,
    ProductScoreOut,
    ProductScoreRequest,
    ProductWithScore,
    UserProfileInput,
)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/products", tags=["products"])


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
