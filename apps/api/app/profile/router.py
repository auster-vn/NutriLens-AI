from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import User, UserProfile
from app.schemas.products import UserProfileInput

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _schema(profile: UserProfile) -> UserProfileInput:
    return UserProfileInput(
        age_group=profile.age_group,
        goal=profile.goal,
        allergies=profile.allergies or [],
        diet=profile.diet,
        disliked_ingredients=profile.disliked_ingredients or [],
        budget_daily=profile.budget_daily,
    )


@router.get("", response_model=UserProfileInput)
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserProfileInput:
    profile = await session.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return _schema(profile)


@router.put("", response_model=UserProfileInput)
async def update_profile(
    request: UserProfileInput,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserProfileInput:
    profile = await session.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)
    for key, value in request.model_dump().items():
        setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return _schema(profile)
