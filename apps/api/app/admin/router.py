from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.marts import build_analytics_marts
from app.core.database import get_session
from app.core.models import AdminOperationAudit, DataPipelineRun, RagDocument, RagEvaluationRun, RagRelease
from app.core.security import audit_safe_payload, require_admin
from app.data.orchestration import run_knowledge_release_pipeline
from app.data.quality import build_data_quality_report
from app.observability.snapshot import build_observability_snapshot
from app.rag.benchmark import load_core_benchmark
from app.rag.evaluation import compare_evaluation_metrics, evaluate_cases
from app.rag.gate import GateDecision
from app.rag.pipeline import rollback_release
from app.rag.release_control import KnowledgeReleaseControl
from app.rag.service import has_prompt_injection_risk, validate_metadata
from app.schemas.rag import (
    AdminDocumentIn,
    AdminDocumentOut,
    EvaluationGateOut,
    EvaluationRunOut,
    PipelineRunOut,
    RagIngestRequest,
    RagReleaseOut,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/session")
async def get_admin_session(_: None = Depends(require_admin)) -> dict:
    return {"authenticated": True}


@router.post("/documents", response_model=AdminDocumentOut)
async def create_document(
    request: AdminDocumentIn,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminDocumentOut:
    missing = validate_metadata(request.metadata)
    if missing:
        raise HTTPException(status_code=422, detail={"missing_metadata": missing})
    if has_prompt_injection_risk(request.content):
        raise HTTPException(status_code=422, detail="Document appears to contain prompt injection text.")
    existing = await session.scalar(select(RagDocument).where(RagDocument.filename == request.filename))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A document with this filename already exists.")
    document = RagDocument(
        title=request.title,
        filename=request.filename,
        metadata_json=request.metadata,
        content=request.content,
        content_hash=sha256(request.content.encode()).hexdigest(),
        status=request.metadata.get("status", "approved"),
    )
    session.add(document)
    session.add(
        AdminOperationAudit(
            operation="document.create",
            payload=audit_safe_payload({"filename": request.filename, "title": request.title}),
        )
    )
    await session.commit()
    await session.refresh(document)
    return AdminDocumentOut(
        id=document.id,
        filename=document.filename,
        title=document.title,
        metadata=document.metadata_json,
        content=document.content,
        status=document.status,
        content_hash=document.content_hash,
        version=document.version,
    )


@router.get("/documents", response_model=list[AdminDocumentOut])
async def list_documents(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AdminDocumentOut]:
    result = await session.execute(select(RagDocument).order_by(RagDocument.created_at.desc()))
    return [
        AdminDocumentOut(
            id=document.id,
            filename=document.filename,
            title=document.title,
            metadata=document.metadata_json,
            content=document.content,
            status=document.status,
            content_hash=document.content_hash,
            version=document.version,
        )
        for document in result.scalars().all()
    ]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    document = await session.get(RagDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    await session.delete(document)
    session.add(
        AdminOperationAudit(
            operation="document.delete",
            payload=audit_safe_payload({"document_id": document_id}),
        )
    )
    await session.commit()


@router.get("/audit")
async def list_audit(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(select(AdminOperationAudit).order_by(AdminOperationAudit.created_at.desc()))
    return [
        {
            "id": row.id,
            "operation": row.operation,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in result.scalars().all()
    ]


@router.post("/rag/ingest", response_model=RagReleaseOut)
async def ingest_rag(
    request: RagIngestRequest,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> RagReleaseOut:
    try:
        outcome = await KnowledgeReleaseControl(session).build(version=request.version, publish=request.publish)
        release = outcome.release
        if outcome.gate and not outcome.gate.passed:
            raise HTTPException(status_code=422, detail=outcome.gate.as_dict())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.add(
        AdminOperationAudit(
            operation="rag.ingest",
            payload={"release_id": release.id, "version": release.version, "published": request.publish},
        )
    )
    await session.commit()
    return _release_out(release)


@router.get("/rag/releases", response_model=list[RagReleaseOut])
async def list_releases(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[RagReleaseOut]:
    result = await session.execute(select(RagRelease).order_by(RagRelease.created_at.desc()))
    return [_release_out(release) for release in result.scalars().all()]


@router.post("/rag/publish", response_model=RagReleaseOut)
async def publish_rag(
    release_id: str | None = None,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> RagReleaseOut:
    if release_id is None:
        release = await session.scalar(
            select(RagRelease).where(RagRelease.status == "draft").order_by(RagRelease.created_at.desc()).limit(1)
        )
        if release is None:
            release = await KnowledgeReleaseControl(session).build_draft()
        release_id = release.id
    try:
        outcome = await KnowledgeReleaseControl(session).publish(release_id)
        if outcome.gate and not outcome.gate.passed:
            raise HTTPException(status_code=422, detail=outcome.gate.as_dict())
        release = outcome.release
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.add(AdminOperationAudit(operation="rag.publish", payload={"release_id": release.id}))
    await session.commit()
    return _release_out(release)


@router.post("/rag/gate", response_model=EvaluationGateOut)
async def run_rag_gate(
    release_id: str,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> EvaluationGateOut:
    try:
        decision = await _run_gate(session, release_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EvaluationGateOut(**decision.as_dict())


@router.post("/rag/rollback", response_model=RagReleaseOut)
async def rollback_rag(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> RagReleaseOut:
    try:
        release = await rollback_release(session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.add(AdminOperationAudit(operation="rag.rollback", payload={"release_id": release.id}))
    await session.commit()
    return _release_out(release)


@router.get("/capacity")
async def capacity(_: None = Depends(require_admin)) -> dict:
    return {
        "mode": "local-first",
        "generation": "extractive-grounded",
        "retrieval": "BM25 + feature-hash embedding + RRF",
        "release_registry": "enabled",
    }


@router.post("/evaluate", response_model=EvaluationRunOut)
async def evaluate(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> EvaluationRunOut:
    cases, dataset_hash = load_core_benchmark()
    run = await evaluate_cases(session, cases, dataset_name="core-rag-v1", dataset_hash=dataset_hash)
    return _evaluation_out(run)


@router.get("/evaluation/runs", response_model=list[EvaluationRunOut])
async def list_evaluation_runs(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[EvaluationRunOut]:
    result = await session.execute(select(RagEvaluationRun).order_by(RagEvaluationRun.created_at.desc()).limit(20))
    return [_evaluation_out(run) for run in result.scalars().all()]


@router.get("/evaluation/compare")
async def compare_evaluations(
    candidate_run_id: str,
    baseline_run_id: str,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    candidate = await session.get(RagEvaluationRun, candidate_run_id)
    baseline = await session.get(RagEvaluationRun, baseline_run_id)
    if candidate is None or baseline is None:
        raise HTTPException(status_code=404, detail="Candidate or baseline evaluation run not found.")
    return {
        "candidate_run_id": candidate.id,
        "baseline_run_id": baseline.id,
        **compare_evaluation_metrics(candidate.metrics_json or {}, baseline.metrics_json or {}),
    }


@router.get("/data/pipeline-runs", response_model=list[PipelineRunOut])
async def list_pipeline_runs(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[PipelineRunOut]:
    result = await session.execute(select(DataPipelineRun).order_by(DataPipelineRun.started_at.desc()).limit(50))
    return [
        PipelineRunOut(
            id=run.id,
            pipeline=run.pipeline,
            status=run.status,
            config=run.config_json or {},
            input_count=run.input_count,
            output_count=run.output_count,
            rejected_count=run.rejected_count,
            metrics=run.metrics_json or {},
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        for run in result.scalars().all()
    ]


@router.get("/data/quality")
async def data_quality(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await build_data_quality_report(session)


@router.post("/data/run-pipeline", response_model=PipelineRunOut)
async def run_pipeline(
    version: str | None = None,
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PipelineRunOut:
    try:
        run = await run_knowledge_release_pipeline(session, version=version, publish=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _pipeline_out(run)


@router.get("/observability")
async def observability(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await build_observability_snapshot(session)


@router.get("/analytics/marts")
async def analytics_marts(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await build_analytics_marts(session)


def _release_out(release: RagRelease) -> RagReleaseOut:
    return RagReleaseOut(
        id=release.id,
        version=release.version,
        status=release.status,
        manifest_hash=release.manifest_hash,
        pipeline_run_id=release.pipeline_run_id,
        document_count=release.document_count,
        chunk_count=release.chunk_count,
        metrics=release.metrics_json or {},
        created_at=release.created_at,
        published_at=release.published_at,
    )


def _evaluation_out(run: RagEvaluationRun) -> EvaluationRunOut:
    return EvaluationRunOut(
        id=run.id,
        release_id=run.release_id,
        dataset_name=run.dataset_name,
        dataset_hash=run.dataset_hash,
        metrics=run.metrics_json or {},
        case_results=run.case_results or [],
        created_at=run.created_at,
    )


def _pipeline_out(run: DataPipelineRun) -> PipelineRunOut:
    return PipelineRunOut(
        id=run.id,
        pipeline=run.pipeline,
        status=run.status,
        config=run.config_json or {},
        input_count=run.input_count,
        output_count=run.output_count,
        rejected_count=run.rejected_count,
        metrics=run.metrics_json or {},
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


async def _run_gate(session: AsyncSession, release_id: str) -> GateDecision:
    return await KnowledgeReleaseControl(session).evaluate(release_id)
