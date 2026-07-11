import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.analytics.marts import build_analytics_marts
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.models import RagEvaluationRun, RagRelease
from app.core.schema import initialize_schema
from app.data.artifacts import LocalArtifactStore, export_release_artifacts
from app.data.orchestration import run_knowledge_release_pipeline
from app.data.quality import build_data_quality_report
from app.rag.benchmark import load_core_benchmark
from app.rag.evaluation import compare_evaluation_metrics, evaluate_cases
from app.rag.gate import evaluate_release_gate
from app.rag.release_control import KnowledgeReleaseControl
from app.rag.runtime import retrieve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NutriLens data platform operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest-rag", help="Build a draft Knowledge Release")
    ingest.add_argument("--version")
    ingest.add_argument("--publish", action="store_true")
    subparsers.add_parser("evaluate-rag", help="Evaluate the active Knowledge Release")
    gate = subparsers.add_parser("gate-rag", help="Evaluate whether a Knowledge Release can be published")
    gate.add_argument("release_id")
    comparison = subparsers.add_parser("compare-rag", help="Compare two persisted RAG evaluation runs")
    comparison.add_argument("candidate_run_id")
    comparison.add_argument("baseline_run_id")
    subparsers.add_parser("quality-report", help="Profile product and knowledge data")
    subparsers.add_parser("analytics-report", help="Build product, RAG, and pipeline analytics marts")
    subparsers.add_parser("list-releases", help="List Knowledge Releases")
    pipeline = subparsers.add_parser("run-pipeline", help="Run ingest, gate, and publish orchestration")
    pipeline.add_argument("--version")
    export = subparsers.add_parser("export-release", help="Export immutable lakehouse-ready release artifacts")
    export.add_argument("release_id")
    export.add_argument("--output", default="artifacts")
    search = subparsers.add_parser("search-rag", help="Inspect hybrid retrieval score breakdown")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    return parser


async def run(args: argparse.Namespace) -> dict | list[dict]:
    settings = get_settings()
    await initialize_schema(engine, settings.database_url)
    async with SessionLocal() as session:
        if args.command == "ingest-rag":
            outcome = await KnowledgeReleaseControl(session).build(version=args.version, publish=args.publish)
            release = outcome.release
            if outcome.gate and not outcome.gate.passed:
                return {"release": _release_dict(release), "gate": outcome.gate.as_dict()}
            return _release_dict(release)
        if args.command == "evaluate-rag":
            cases, dataset_hash = load_core_benchmark()
            evaluation = await evaluate_cases(
                session,
                cases,
                dataset_name="core-rag-v1",
                dataset_hash=dataset_hash,
            )
            return {"id": evaluation.id, "metrics": evaluation.metrics_json}
        if args.command == "gate-rag":
            cases, dataset_hash = load_core_benchmark()
            decision = await evaluate_release_gate(
                session,
                args.release_id,
                cases,
                dataset_name="core-rag-v1",
                dataset_hash=dataset_hash,
            )
            return decision.as_dict()
        if args.command == "compare-rag":
            candidate = await session.get(RagEvaluationRun, args.candidate_run_id)
            baseline = await session.get(RagEvaluationRun, args.baseline_run_id)
            if candidate is None or baseline is None:
                raise ValueError("Candidate or baseline evaluation run not found.")
            return {
                "candidate_run_id": candidate.id,
                "baseline_run_id": baseline.id,
                **compare_evaluation_metrics(candidate.metrics_json or {}, baseline.metrics_json or {}),
            }
        if args.command == "quality-report":
            return await build_data_quality_report(session)
        if args.command == "analytics-report":
            return await build_analytics_marts(session)
        if args.command == "run-pipeline":
            pipeline_run = await run_knowledge_release_pipeline(session, version=args.version, publish=True)
            return {
                "id": pipeline_run.id,
                "status": pipeline_run.status,
                "metrics": pipeline_run.metrics_json,
            }
        if args.command == "export-release":
            return await export_release_artifacts(session, args.release_id, LocalArtifactStore(Path(args.output)))
        if args.command == "list-releases":
            result = await session.execute(select(RagRelease).order_by(RagRelease.created_at.desc()))
            return [_release_dict(release) for release in result.scalars().all()]
        if args.command == "search-rag":
            context = await retrieve(session, args.query, args.limit)
            return [
                {
                    "rank": rank,
                    "chunk_id": hit.chunk.id,
                    "source": hit.chunk.source_filename,
                    "heading_path": hit.chunk.heading_path,
                    "lexical_score": round(hit.lexical_score, 6),
                    "semantic_score": round(hit.semantic_score, 6),
                    "fused_score": round(hit.fused_score, 8),
                    "content": hit.chunk.content,
                }
                for rank, hit in enumerate(context.hits, start=1)
            ]
    raise ValueError(f"Unsupported command: {args.command}")


def _release_dict(release: RagRelease) -> dict:
    return {
        "id": release.id,
        "version": release.version,
        "status": release.status,
        "manifest_hash": release.manifest_hash,
        "document_count": release.document_count,
        "chunk_count": release.chunk_count,
        "metrics": release.metrics_json,
    }


def main() -> None:
    result = asyncio.run(run(build_parser().parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
