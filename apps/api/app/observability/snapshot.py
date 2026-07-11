from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import DataPipelineRun, RagAnswerAudit, RagEvaluationRun, RagRelease


async def build_observability_snapshot(session: AsyncSession) -> dict:
    answer_row = (
        await session.execute(
            select(
                func.count(RagAnswerAudit.id),
                func.avg(RagAnswerAudit.latency_ms),
                func.avg(case((RagAnswerAudit.abstained.is_(True), 1.0), else_=0.0)),
                func.avg(case((RagAnswerAudit.citation_count > 0, 1.0), else_=0.0)),
            )
        )
    ).one()
    pipeline_row = (
        await session.execute(
            select(
                func.count(DataPipelineRun.id),
                func.sum(case((DataPipelineRun.status == "succeeded", 1), else_=0)),
                func.sum(case((DataPipelineRun.status.in_(["failed", "blocked"]), 1), else_=0)),
            )
        )
    ).one()
    active = await session.scalar(select(RagRelease).where(RagRelease.status == "published"))
    latest_evaluation = await session.scalar(
        select(RagEvaluationRun).order_by(RagEvaluationRun.created_at.desc()).limit(1)
    )
    return {
        "rag": {
            "answer_count": int(answer_row[0] or 0),
            "latency_mean_ms": round(float(answer_row[1] or 0), 2),
            "abstention_rate": round(float(answer_row[2] or 0), 4),
            "citation_coverage": round(float(answer_row[3] or 0), 4),
            "active_release": active.version if active else None,
            "latest_evaluation": latest_evaluation.metrics_json if latest_evaluation else None,
        },
        "pipelines": {
            "run_count": int(pipeline_row[0] or 0),
            "succeeded_count": int(pipeline_row[1] or 0),
            "failed_or_blocked_count": int(pipeline_row[2] or 0),
        },
    }
