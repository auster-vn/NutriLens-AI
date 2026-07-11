from datetime import date

from pydantic import BaseModel


class PantryItemIn(BaseModel):
    barcode: str
    quantity: float | None = None
    unit: str | None = None
    expiry_date: date | None = None
    storage_location: str | None = None


class PantryItemOut(PantryItemIn):
    id: str
    user_id: str
    product_name: str | None = None
    brand: str | None = None
    image_url: str | None = None
    expiry_status: str = "unknown"
