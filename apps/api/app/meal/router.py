from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import MealPlan, User, UserProfile
from app.meal.planner import build_meal_plan
from app.schemas.meal import MealPlanOut, MealPlanRequest

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


@router.post("/generate", response_model=MealPlanOut)
async def generate_meal_plan(
    request: MealPlanRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MealPlanOut:
    profile = await session.get(UserProfile, user.id)
    excluded = list(
        dict.fromkeys(
            [
                *request.excluded_ingredients,
                *(profile.allergies if profile else []),
                *(profile.disliked_ingredients if profile else []),
            ]
        )
    )
    try:
        plan_payload = build_meal_plan(
            days=request.days,
            goal=request.goal,
            budget=request.budget,
            diet=request.diet or (profile.diet if profile else None),
            excluded=excluded,
            available=request.available_items,
            meals_per_day=request.meals_per_day,
            target_calories=request.target_calories,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
