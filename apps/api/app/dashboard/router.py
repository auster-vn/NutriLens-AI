from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import MealPlan, PantryItem, ProductCache, ProductFavorite, ScanHistory, User
from app.dashboard.schemas import DashboardMetric, DashboardOut, RecentScan

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _count(session: AsyncSession, model: type, user_id: str) -> int:
    value = await session.scalar(select(func.count()).select_from(model).where(model.user_id == user_id))
    return int(value or 0)


@router.get("", response_model=DashboardOut)
async def dashboard(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardOut:
    today = datetime.now(UTC).date()
    scan_count = await _count(session, ScanHistory, user.id)
    pantry_count = await _count(session, PantryItem, user.id)
    meal_count = await _count(session, MealPlan, user.id)
    favorite_count = await _count(session, ProductFavorite, user.id)
    expiring = await session.scalar(
        select(func.count())
        .select_from(PantryItem)
        .where(
            PantryItem.user_id == user.id,
            PantryItem.expiry_date >= today,
            PantryItem.expiry_date <= today + timedelta(days=7),
        )
    )
    average_score = await session.scalar(
        select(func.avg(ScanHistory.score)).where(
            ScanHistory.user_id == user.id,
            ScanHistory.score.is_not(None),
        )
    )
    history_result = await session.execute(
        select(ScanHistory, ProductCache)
        .join(ProductCache, ProductCache.barcode == ScanHistory.barcode, isouter=True)
        .where(ScanHistory.user_id == user.id)
        .order_by(ScanHistory.created_at.desc())
        .limit(100)
    )
    rows = history_result.all()
    scores = [history.score for history, _ in rows if history.score is not None]
    risks = {
        "low": sum(score >= 75 for score in scores),
        "medium": sum(45 <= score < 75 for score in scores),
        "high": sum(score < 45 for score in scores),
    }
    warning_counts = Counter(warning for history, _ in rows for warning in (history.warnings or []))
    return DashboardOut(
        metrics=[
            DashboardMetric(label="Products scanned", value=scan_count, detail="Personal scan history"),
            DashboardMetric(
                label="Average score",
                value=round(float(average_score or 0), 1),
                detail="Across scored products",
            ),
            DashboardMetric(label="Pantry items", value=pantry_count, detail=f"{int(expiring or 0)} expiring soon"),
            DashboardMetric(label="Meal plans", value=meal_count, detail="Saved planning sessions"),
            DashboardMetric(label="Favorites", value=favorite_count, detail="Products to revisit"),
        ],
        risk_distribution=risks,
        top_warnings=[{"warning": warning, "count": count} for warning, count in warning_counts.most_common(5)],
        recent_scans=[
            RecentScan(
                barcode=history.barcode,
                product_name=product.name if product else None,
                score=history.score,
                created_at=history.created_at,
            )
            for history, product in rows[:6]
        ],
    )
