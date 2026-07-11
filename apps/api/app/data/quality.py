from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import DataPipelineRun, ProductCache, RagChunk, RagRelease


async def build_data_quality_report(session: AsyncSession) -> dict:
    products = list((await session.execute(select(ProductCache))).scalars().all())
    releases = list((await session.execute(select(RagRelease))).scalars().all())
    chunks = list((await session.execute(select(RagChunk))).scalars().all())
    runs = list((await session.execute(select(DataPipelineRun))).scalars().all())
    ttl = timedelta(hours=get_settings().product_cache_ttl_hours)
    now = datetime.now(UTC)
    stale_count = 0
    for product in products:
        cached_at = product.cached_at or product.updated_at
        if cached_at is None:
            stale_count += 1
        else:
            comparable = cached_at.replace(tzinfo=UTC) if cached_at.tzinfo is None else cached_at
            stale_count += now - comparable > ttl
    product_fields = ["name", "brand", "ingredients_text", "nutriscore", "image_url"]
    missing_rates = {
        field: round(sum(not getattr(product, field) for product in products) / len(products), 4) if products else 0.0
        for field in product_fields
    }
    duplicate_chunk_hashes = len(chunks) - len({(chunk.release_id, chunk.content_hash) for chunk in chunks})
    return {
        "generated_at": now.isoformat(),
        "products": {
            "count": len(products),
            "average_completeness": round(
                sum(product.completeness_score or 0 for product in products) / len(products), 2
            )
            if products
            else 0.0,
            "stale_count": stale_count,
            "missing_field_rates": missing_rates,
        },
        "knowledge": {
            "release_count": len(releases),
            "published_release": next((release.version for release in releases if release.status == "published"), None),
            "chunk_count": len(chunks),
            "duplicate_chunk_hashes_within_release": duplicate_chunk_hashes,
            "empty_embeddings": sum(not chunk.embedding for chunk in chunks),
            "average_chunk_tokens": (
                round(sum(chunk.token_count for chunk in chunks) / len(chunks), 2) if chunks else 0.0
            ),
        },
        "pipelines": {
            "run_count": len(runs),
            "succeeded": sum(run.status == "succeeded" for run in runs),
            "failed": sum(run.status == "failed" for run in runs),
            "latest_run_id": runs[-1].id if runs else None,
        },
    }
