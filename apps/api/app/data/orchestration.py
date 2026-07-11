from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import DataPipelineRun
from app.rag.release_control import KnowledgeReleaseControl


async def run_knowledge_release_pipeline(
    session: AsyncSession,
    *,
    version: str | None = None,
    publish: bool = True,
) -> DataPipelineRun:
    run = DataPipelineRun(
        pipeline="knowledge_release_orchestration",
        status="running",
        config_json={"version": version, "publish": publish},
        metrics_json={"stages": []},
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    started = perf_counter()
    stages: list[dict] = []
    try:
        control = KnowledgeReleaseControl(session)
        stage_started = perf_counter()
        release = await control.build_draft(version)
        stages.append(_stage("ingest", "succeeded", stage_started, release_id=release.id))
        run = await session.get(DataPipelineRun, run.id)
        if run is None:
            raise RuntimeError("Orchestration run disappeared.")
        run.input_count = release.document_count
        run.output_count = release.chunk_count

        if publish:
            outcome = await control.publish(release.id)
            decision = outcome.gate
            if decision is None:
                raise RuntimeError("Publish did not produce an evaluation decision.")
            stages.append({
                "name": "evaluation_gate",
                "status": "succeeded" if decision.passed else "blocked",
                "duration_ms": outcome.timings_ms["evaluation_gate"],
                "evaluation_run_id": decision.evaluation_run_id,
                "failures": decision.failures,
            })
            run = await session.get(DataPipelineRun, run.id)
            if run is None:
                raise RuntimeError("Orchestration run disappeared.")
            if not decision.passed:
                run.status = "blocked"
                run.finished_at = datetime.now(UTC)
                run.metrics_json = _metrics(started, stages, release.id)
                await session.commit()
                return run

            release = outcome.release
            stages.append({
                "name": "publish",
                "status": "succeeded",
                "duration_ms": outcome.timings_ms["publish"],
                "release_id": release.id,
            })
            run = await session.get(DataPipelineRun, run.id)
            if run is None:
                raise RuntimeError("Orchestration run disappeared.")

        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        run.metrics_json = _metrics(started, stages, release.id)
        await session.commit()
        await session.refresh(run)
        return run
    except Exception as exc:
        await session.rollback()
        persisted = await session.get(DataPipelineRun, run.id)
        if persisted is not None:
            persisted.status = "failed"
            persisted.error_message = str(exc)[:1000]
            persisted.finished_at = datetime.now(UTC)
            persisted.metrics_json = _metrics(started, stages, None)
            await session.commit()
        raise


def _stage(name: str, status: str, started: float, **details) -> dict:
    return {"name": name, "status": status, "duration_ms": round((perf_counter() - started) * 1000, 2), **details}


def _metrics(started: float, stages: list[dict], release_id: str | None) -> dict:
    return {"duration_ms": round((perf_counter() - started) * 1000, 2), "release_id": release_id, "stages": stages}
