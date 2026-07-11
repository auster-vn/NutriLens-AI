"""Optional Prefect deployment wrapper for the framework-neutral orchestrator."""

from prefect import flow

from app.core.database import SessionLocal
from app.data.orchestration import run_knowledge_release_pipeline


@flow(name="nutrilens-knowledge-release", log_prints=True)
async def knowledge_release_flow(version: str | None = None, publish: bool = True) -> dict:
    async with SessionLocal() as session:
        run = await run_knowledge_release_pipeline(session, version=version, publish=publish)
        return {"run_id": run.id, "status": run.status, "metrics": run.metrics_json}
