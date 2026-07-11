from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import MealPlan, User
from app.schemas.meal import MealPlanOut, MealPlanRequest

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])

BASE_MEALS = [
    {"name": "Yogurt + yến mạch + trái cây", "tags": ["high_protein", "low_sugar"], "uses": ["yogurt", "oat", "fruit"]},
    {
        "name": "Cơm gạo lứt + trứng + rau luộc",
        "tags": ["general", "weight_loss"],
        "uses": ["rice", "egg", "vegetable"],
    },
    {"name": "Đậu hũ sốt cà chua + rau xanh", "tags": ["vegetarian", "vegan"], "uses": ["tofu", "tomato", "vegetable"]},
    {
        "name": "Ức gà áp chảo + khoai lang",
        "tags": ["high_protein", "weight_loss"],
        "uses": ["chicken", "sweet potato"],
    },
    {"name": "Súp rau củ + đậu", "tags": ["low_sodium", "vegan"], "uses": ["bean", "vegetable"]},
]


@router.post("/generate", response_model=MealPlanOut)
async def generate_meal_plan(
    request: MealPlanRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealPlanOut:
    matching = [meal for meal in BASE_MEALS if request.goal in meal["tags"]]
    pool = matching or BASE_MEALS
    if request.available_items:
        pantry_terms = {item.lower() for item in request.available_items}
        pantry_matches = [
            meal
            for meal in pool
            if any(term in " ".join(meal["uses"]).lower() or term in meal["name"].lower() for term in pantry_terms)
        ]
        pool = pantry_matches + [meal for meal in pool if meal not in pantry_matches]
    meals = [
        {
            "day": day,
            "breakfast": pool[(day - 1) % len(pool)]["name"],
            "lunch": pool[day % len(pool)]["name"],
            "dinner": pool[(day + 1) % len(pool)]["name"],
        }
        for day in range(1, request.days + 1)
    ]
    shopping_list = [
        {"item": "Rau xanh", "quantity": f"{request.days * 300}g"},
        {"item": "Nguồn protein chính", "quantity": f"{request.days} phần"},
        {"item": "Trái cây ít đường", "quantity": f"{request.days} phần"},
    ]
    warnings = ["Ước tính dinh dưỡng là rule-based; cần dữ liệu sản phẩm cụ thể để chính xác hơn."]
    if request.excluded_ingredients:
        warnings.append("Đã ghi nhận nguyên liệu cần tránh: " + ", ".join(request.excluded_ingredients))
    if request.available_items:
        warnings.append("Đã ưu tiên nguyên liệu đang có trong pantry: " + ", ".join(request.available_items[:6]))
    plan_payload = {
        "days": request.days,
        "budget": request.budget,
        "goal": request.goal,
        "meals": meals,
        "shopping_list": shopping_list,
        "estimated_nutrition": {"protein": "moderate", "sugar": "controlled", "fiber": "good"},
        "warnings": warnings,
    }
    meal_plan = MealPlan(
        user_id=user.id,
        days=request.days,
        budget=request.budget,
        goal=request.goal,
        plan=plan_payload,
    )
    session.add(meal_plan)
    await session.commit()
    await session.refresh(meal_plan)
    return MealPlanOut(id=meal_plan.id, **plan_payload)


@router.get("/{plan_id}", response_model=MealPlanOut)
async def get_meal_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealPlanOut:
    meal_plan = await session.scalar(select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user.id))
    if meal_plan is None:
        raise HTTPException(status_code=404, detail="Meal plan not found.")
    return MealPlanOut(id=meal_plan.id, **meal_plan.plan)
