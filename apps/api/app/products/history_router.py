from datetime import datetime

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import ProductCache, ScanHistory, User
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import outerjoin

router = APIRouter(prefix="/api/scan", tags=["scan-history"])


class ScanHistoryItem(BaseModel):
    id: str
    barcode: str
    score: int | None
    warnings: list[str]
    created_at: datetime
    product_name: str | None
    brand: str | None
    image_url: str | None


@router.get("/history", response_model=list[ScanHistoryItem])
async def scan_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 12,
) -> list[ScanHistoryItem]:
    capped_limit = max(1, min(limit, 50))
    # Use outerjoin so history entries remain visible even if product_cache is missing
    result = await session.execute(
        select(ScanHistory, ProductCache)
        .select_from(outerjoin(ScanHistory, ProductCache, ProductCache.barcode == ScanHistory.barcode))
        .where(ScanHistory.user_id == user.id)
        .order_by(ScanHistory.created_at.desc())
        .limit(capped_limit)
    )
    return [
        ScanHistoryItem(
            id=history.id,
            barcode=history.barcode,
            score=history.score,
            warnings=history.warnings or [],
            created_at=history.created_at,
            product_name=product.name if product else None,
            brand=product.brand if product else None,
            image_url=product.image_url if product else None,
        )
        for history, product in result.all()
    ]
