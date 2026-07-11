from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.core.models import ProductCache
from app.products.openfoodfacts import ProductUpstreamError
from app.products.service import get_or_fetch_product
from fastapi import HTTPException


def _cached_product() -> ProductCache:
    return ProductCache(
        barcode="12345678",
        name="Cached product",
        nutriments={},
        cached_at=datetime.now(UTC) - timedelta(days=30),
    )


@pytest.mark.asyncio
async def test_stale_product_falls_back_to_cache_when_upstream_is_unavailable():
    product = _cached_product()
    session = AsyncMock()
    session.get.return_value = product

    with patch(
        "app.products.service.fetch_product",
        new=AsyncMock(side_effect=ProductUpstreamError("Open Food Facts is temporarily unavailable.")),
    ):
        result = await get_or_fetch_product(session, product.barcode)

    assert result is product
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_updates_cache_timestamp():
    product = _cached_product()
    previous_cached_at = product.cached_at
    session = AsyncMock()
    session.get.return_value = product
    refreshed = {
        "barcode": product.barcode,
        "name": "Fresh product",
        "nutriments": {"sugars_100g": 2},
    }

    with patch("app.products.service.fetch_product", new=AsyncMock(return_value=refreshed)):
        result = await get_or_fetch_product(session, product.barcode)

    assert result.name == "Fresh product"
    assert result.cached_at > previous_cached_at
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upstream_failure_without_cache_returns_bad_gateway():
    session = AsyncMock()
    session.get.return_value = None

    with (
        patch(
            "app.products.service.fetch_product",
            new=AsyncMock(side_effect=ProductUpstreamError("Open Food Facts is temporarily unavailable.")),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_or_fetch_product(session, "12345678")

    assert exc_info.value.status_code == 502
