from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import ProductCache, ProductFavorite, User
from app.core.security import validate_barcode
from app.products.service import get_or_fetch_product, product_to_schema
from app.schemas.products import ProductOut

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[ProductOut])
async def list_favorites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProductOut]:
    result = await session.execute(
        select(ProductCache)
        .join(ProductFavorite, ProductFavorite.barcode == ProductCache.barcode)
        .where(ProductFavorite.user_id == user.id)
        .order_by(ProductFavorite.created_at.desc())
    )
    return [product_to_schema(product) for product in result.scalars().all()]


@router.post("/{barcode}", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    barcode: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    cleaned = validate_barcode(barcode)
    product = await get_or_fetch_product(session, cleaned)
    existing = await session.scalar(
        select(ProductFavorite).where(
            ProductFavorite.user_id == user.id,
            ProductFavorite.barcode == cleaned,
        )
    )
    if existing is None:
        session.add(ProductFavorite(user_id=user.id, barcode=cleaned))
        await session.commit()
    return product_to_schema(product)


@router.delete("/{barcode}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    barcode: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    favorite = await session.scalar(
        select(ProductFavorite).where(
            ProductFavorite.user_id == user.id,
            ProductFavorite.barcode == validate_barcode(barcode),
        )
    )
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found.")
    await session.delete(favorite)
    await session.commit()
