import httpx
from app.core.config import get_settings


class ProductNotFoundError(Exception):
    pass


class ProductUpstreamError(Exception):
    pass


def _split_tags(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).replace("en:", "").strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize_open_food_facts(barcode: str, payload: dict) -> dict:
    product = payload.get("product") or payload
    normalized = {
        "barcode": barcode,
        "name": product.get("product_name") or product.get("generic_name"),
        "brand": product.get("brands"),
        "categories": _split_tags(product.get("categories_tags") or product.get("categories")),
        "ingredients_text": product.get("ingredients_text"),
        "allergens": _split_tags(product.get("allergens_tags") or product.get("allergens")),
        "additives": _split_tags(product.get("additives_tags") or product.get("additives")),
        "nutriments": product.get("nutriments") or {},
        "nutriscore": product.get("nutriscore_grade"),
        "ecoscore": product.get("ecoscore_grade"),
        "image_url": product.get("image_front_url") or product.get("image_url"),
        "source": "open_food_facts",
        "raw_summary": {
            "status": payload.get("status"),
            "last_modified_t": product.get("last_modified_t"),
            "rev": product.get("rev"),
        },
    }
    normalized["completeness_score"] = _completeness_score(normalized)
    return normalized


def _completeness_score(product: dict) -> float:
    # 8 product-level fields
    field_expected = [
        "name",
        "brand",
        "categories",
        "ingredients_text",
        "allergens",
        "additives",
        "nutriscore",
        "image_url",
    ]
    # 4 critical nutriment keys — checked separately (not double-counting nutriments dict)
    required_nutriments = ["sugars_100g", "sodium_100g", "proteins_100g", "energy-kcal_100g"]
    total = len(field_expected) + len(required_nutriments)
    present = 0
    for key in field_expected:
        value = product.get(key)
        if value not in (None, "", [], {}):
            present += 1
    nutriments = product.get("nutriments") or {}
    present += sum(1 for key in required_nutriments if nutriments.get(key) is not None)
    return round((present / total) * 100, 1)


async def fetch_product(barcode: str) -> dict:
    settings = get_settings()
    url = f"{settings.open_food_facts_base_url}/api/v2/product/{barcode}.json"
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(url, headers={"User-Agent": "NutriLensAI/0.1"})
        if response.status_code == 404:
            raise ProductNotFoundError(f"Product {barcode} was not found in Open Food Facts.")
        response.raise_for_status()
        payload = response.json()
    except ProductNotFoundError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise ProductUpstreamError("Open Food Facts is temporarily unavailable.") from exc
    if not isinstance(payload, dict):
        raise ProductUpstreamError("Open Food Facts returned an invalid response.")
    if payload.get("status") == 0:
        raise ProductNotFoundError(f"Product {barcode} was not found in Open Food Facts.")
    return normalize_open_food_facts(barcode, payload)
