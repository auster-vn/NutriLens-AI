from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.models import ProductCache, ScanHistory
from app.products.openfoodfacts import ProductNotFoundError, ProductUpstreamError, fetch_product
from app.products.scoring import score_product
from app.schemas.products import ProductOut, ProductScoreOut, UserProfileInput
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def product_to_schema(product: ProductCache) -> ProductOut:
    return ProductOut(
        barcode=product.barcode,
        name=product.name,
        brand=product.brand,
        categories=product.categories or [],
        ingredients_text=product.ingredients_text,
        allergens=product.allergens or [],
        additives=product.additives or [],
        nutriments=product.nutriments or {},
        nutriscore=product.nutriscore,
        ecoscore=product.ecoscore,
        image_url=product.image_url,
        source=product.source,
        completeness_score=product.completeness_score,
    )


async def get_cached_product(session: AsyncSession, barcode: str) -> ProductCache | None:
    return await session.get(ProductCache, barcode)


async def upsert_product(session: AsyncSession, data: dict) -> ProductCache:
    product = await get_cached_product(session, data["barcode"])
    if product is None:
        product = ProductCache(**data)
        session.add(product)
    else:
        for key, value in data.items():
            setattr(product, key, value)
    product.cached_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(product)
    return product


async def get_or_fetch_product(session: AsyncSession, barcode: str) -> ProductCache:
    cached = await get_cached_product(session, barcode)
    if cached and not _is_stale(cached):
        return cached
    try:
        data = await fetch_product(barcode)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProductUpstreamError as exc:
        if cached is not None:
            return cached
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return await upsert_product(session, data)


def _is_stale(product: ProductCache) -> bool:
    cached_at = product.cached_at or product.updated_at
    if cached_at is None:
        return True
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=UTC)
    ttl = timedelta(hours=get_settings().product_cache_ttl_hours)
    return datetime.now(UTC) - cached_at > ttl


async def score_cached_product(
    session: AsyncSession,
    product: ProductCache,
    user_profile: UserProfileInput,
    record_scan: bool = False,
    user_id: str | None = None,
) -> ProductScoreOut:
    score = score_product(
        product.nutriments or {},
        product.allergens or [],
        product.additives or [],
        product.nutriscore,
        user_profile,
        product.ingredients_text,
    )
    if record_scan:
        session.add(
            ScanHistory(
                user_id=user_id,
                barcode=product.barcode,
                score=score.score,
                warnings=score.warnings,
            )
        )
        await session.commit()
    return score


async def list_recent_scans(session: AsyncSession, limit: int = 20) -> list[ScanHistory]:
    result = await session.execute(select(ScanHistory).order_by(ScanHistory.created_at.desc()).limit(limit))
    return list(result.scalars().all())
