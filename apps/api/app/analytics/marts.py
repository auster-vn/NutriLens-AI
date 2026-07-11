from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.definitions import semantic_catalog
from app.core.models import DataPipelineRun, ProductCache, RagAnswerAudit, ScanHistory


async def build_analytics_marts(session: AsyncSession) -> dict:
    return {
        "semantic_catalog": semantic_catalog(),
        "fct_rag_daily": await _rag_daily(session),
        "fct_scan_daily": await _scan_daily(session),
        "fct_pipeline_daily": await _pipeline_daily(session),
        "mart_product_quality": await _product_quality(session),
    }


async def _rag_daily(session: AsyncSession) -> list[dict]:
    day = func.date(RagAnswerAudit.created_at)
    rows = await session.execute(
        select(
            day.label("day"),
            RagAnswerAudit.route,
            func.count().label("answer_count"),
            func.avg(RagAnswerAudit.latency_ms).label("latency_mean_ms"),
            func.avg(case((RagAnswerAudit.abstained.is_(True), 1.0), else_=0.0)).label("abstention_rate"),
            func.avg(case((RagAnswerAudit.citation_count > 0, 1.0), else_=0.0)).label("citation_coverage"),
        )
        .group_by(day, RagAnswerAudit.route)
        .order_by(day.desc(), RagAnswerAudit.route)
    )
    return [
        {
            "day": str(row.day),
            "route": row.route,
            "answer_count": int(row.answer_count),
            "latency_mean_ms": round(float(row.latency_mean_ms or 0), 2),
            "abstention_rate": round(float(row.abstention_rate or 0), 4),
            "citation_coverage": round(float(row.citation_coverage or 0), 4),
        }
        for row in rows
    ]


async def _scan_daily(session: AsyncSession) -> list[dict]:
    day = func.date(ScanHistory.created_at)
    rows = await session.execute(
        select(
            day.label("day"),
            func.count().label("scan_count"),
            func.count(func.distinct(ScanHistory.user_id)).label("active_users"),
            func.count(func.distinct(ScanHistory.barcode)).label("unique_products"),
            func.avg(ScanHistory.score).label("mean_score"),
        )
        .group_by(day)
        .order_by(day.desc())
    )
    return [
        {
            "day": str(row.day),
            "scan_count": int(row.scan_count),
            "active_users": int(row.active_users),
            "unique_products": int(row.unique_products),
            "mean_score": round(float(row.mean_score or 0), 2),
        }
        for row in rows
    ]


async def _pipeline_daily(session: AsyncSession) -> list[dict]:
    day = func.date(DataPipelineRun.started_at)
    rows = await session.execute(
        select(
            day.label("day"),
            DataPipelineRun.pipeline,
            func.count().label("run_count"),
            func.sum(case((DataPipelineRun.status == "succeeded", 1), else_=0)).label("succeeded_count"),
            func.sum(case((DataPipelineRun.status.in_(["failed", "blocked"]), 1), else_=0)).label("failed_count"),
            func.sum(DataPipelineRun.output_count).label("output_count"),
        )
        .group_by(day, DataPipelineRun.pipeline)
        .order_by(day.desc(), DataPipelineRun.pipeline)
    )
    return [dict(row._mapping) for row in rows]


async def _product_quality(session: AsyncSession) -> dict:
    row = (
        await session.execute(
            select(
                func.count(ProductCache.barcode),
                func.avg(ProductCache.completeness_score),
                func.sum(case((ProductCache.completeness_score >= 0.8, 1), else_=0)),
                func.sum(case((ProductCache.nutriscore.is_(None), 1), else_=0)),
            )
        )
    ).one()
    return {
        "product_count": int(row[0] or 0),
        "mean_completeness": round(float(row[1] or 0), 4),
        "high_completeness_count": int(row[2] or 0),
        "missing_nutriscore_count": int(row[3] or 0),
    }
