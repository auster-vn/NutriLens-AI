from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import outerjoin

from app.auth.security import get_current_user
from app.core.database import get_session
from app.core.models import PantryItem, ProductCache, User
from app.core.security import validate_barcode
from app.products.service import get_or_fetch_product
from app.schemas.pantry import PantryItemIn, PantryItemOut

router = APIRouter(prefix="/api/pantry", tags=["pantry"])

_EXPIRY_URGENT_DAYS = 3
_EXPIRY_SOON_DAYS = 7


def _expiry_status(expiry_date: datetime | None) -> str:
    if expiry_date is None:
        return "unknown"
    today = datetime.now(UTC).date()
    days_left = (expiry_date - today).days if hasattr(expiry_date, "year") else None
    if days_left is None:
        return "unknown"
    if days_left < 0:
        return "expired"
    if days_left < _EXPIRY_URGENT_DAYS:
        return "urgent"
    if days_left < _EXPIRY_SOON_DAYS:
        return "soon"
    return "ok"


def _out(item: PantryItem, product: ProductCache | None = None) -> PantryItemOut:
    return PantryItemOut(
        id=item.id,
        user_id=item.user_id,
        barcode=item.barcode,
        quantity=item.quantity,
        unit=item.unit,
        expiry_date=item.expiry_date,
        storage_location=item.storage_location,
        product_name=product.name if product else None,
        brand=product.brand if product else None,
        image_url=product.image_url if product else None,
        expiry_status=_expiry_status(item.expiry_date),
    )


@router.get("", response_model=list[PantryItemOut])
async def list_pantry(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PantryItemOut]:
    # Use outerjoin so pantry items are visible even if product_cache entry is missing
    result = await session.execute(
        select(PantryItem, ProductCache)
        .select_from(outerjoin(PantryItem, ProductCache, ProductCache.barcode == PantryItem.barcode))
        .where(PantryItem.user_id == user.id)
        .order_by(PantryItem.created_at.desc())
    )
    return [_out(item, product) for item, product in result.all()]


@router.post("", response_model=PantryItemOut)
async def add_pantry_item(
    request: PantryItemIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PantryItemOut:
    barcode = validate_barcode(request.barcode)
    await get_or_fetch_product(session, barcode)
    item = PantryItem(**request.model_dump(exclude={"barcode"}), barcode=barcode, user_id=user.id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    product = await session.get(ProductCache, barcode)
    return _out(item, product)


@router.put("/{item_id}", response_model=PantryItemOut)
async def update_pantry_item(
    item_id: str,
    request: PantryItemIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PantryItemOut:
    item = await session.scalar(select(PantryItem).where(PantryItem.id == item_id, PantryItem.user_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Pantry item not found.")
    barcode = validate_barcode(request.barcode)
    await get_or_fetch_product(session, barcode)
    values = request.model_dump(exclude={"barcode"})
    values["barcode"] = barcode
    for key, value in values.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    product = await session.get(ProductCache, item.barcode)
    return _out(item, product)


@router.delete("/{item_id}", status_code=204)
async def delete_pantry_item(
    item_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await session.scalar(select(PantryItem).where(PantryItem.id == item_id, PantryItem.user_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Pantry item not found.")
    await session.delete(item)
    await session.commit()
