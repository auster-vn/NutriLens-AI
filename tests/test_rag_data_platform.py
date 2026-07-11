from math import sqrt
from pathlib import Path

import pytest
import pytest_asyncio
from app.analytics.marts import build_analytics_marts
from app.core.models import Base, DataPipelineRun, RagChunk, RagRelease
from app.data.artifacts import MemoryArtifactStore, export_release_artifacts
from app.data.orchestration import run_knowledge_release_pipeline
from app.data.quality import build_data_quality_report
from app.observability.metrics import MetricsRegistry
from app.observability.snapshot import build_observability_snapshot
from app.rag.chunking import chunk_document
from app.rag.contracts import IndexedChunk, RetrievalHit, SourceDocument
from app.rag.embeddings import FeatureHashEmbedding, create_embedding_provider
from app.rag.evaluation import compare_evaluation_metrics, evaluate_cases
from app.rag.gate import EvaluationThresholds, evaluate_release_gate
from app.rag.pipeline import ingest_knowledge_release, rollback_release
from app.rag.release_control import KnowledgeReleaseControl
from app.rag.retrieval import HybridRetriever
from app.rag.runtime import _select_answer_context, answer_with_retrieval
from app.rag.text import tokenize
from app.rag.vector_store import PgvectorCandidateStore, SqlAlchemyCandidateStore, create_candidate_store
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def rag_session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'rag-platform.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_markdown_chunking_is_bounded_deterministic_and_preserves_heading_lineage():
    document = SourceDocument(
        filename="fiber.md",
        title="Fiber",
        metadata={"source_url": "https://example.com/fiber"},
        body="# Fiber\n\n" + " ".join(f"word{index}" for index in range(80)),
    )

    first = chunk_document(document, max_tokens=24, overlap_tokens=4)
    second = chunk_document(document, max_tokens=24, overlap_tokens=4)

    assert len(first) > 1
    assert all(chunk.token_count <= 24 for chunk in first)
    assert all(chunk.heading_path == ("Fiber",) for chunk in first)
    assert [chunk.content_hash for chunk in first] == [chunk.content_hash for chunk in second]
    assert set(first[0].content.split()[-4:]) <= set(first[1].content.split()[:4])


def test_feature_hash_embeddings_are_deterministic_normalized_and_discriminative():
    embedder = FeatureHashEmbedding(128)
    vectors = embedder.embed(["high sugar food label", "high sugar food label", "protein and muscle"])

    assert vectors[0] == vectors[1]
    assert pytest.approx(sqrt(sum(value * value for value in vectors[0])), abs=1e-8) == 1.0
    assert vectors[0] != vectors[2]


def test_embedding_provider_factory_keeps_local_default_reproducible():
    provider = create_embedding_provider(
        provider="feature_hash",
        dimensions=64,
        sentence_transformer_model="sentence-transformers/all-MiniLM-L6-v2",
    )

    assert provider.model_name == "feature-hash-v3-64d"
    assert provider.dimensions == 64


def test_vietnamese_unaccented_aliases_expand_for_retrieval():
    tokens = tokenize("Toi di ung sua va muoi", remove_stop_words=True, expand_aliases=True)

    assert "allergen" in tokens
    assert "milk" in tokens
    assert "sodium" in tokens


def test_candidate_store_selects_pgvector_only_for_postgres():
    local = create_candidate_store("auto", "sqlite+aiosqlite:///test.db", 256)
    production = create_candidate_store("auto", "postgresql+asyncpg://localhost/nutrilens", 256)

    assert isinstance(local, SqlAlchemyCandidateStore)
    assert isinstance(production, PgvectorCandidateStore)
    with pytest.raises(ValueError, match="requires.*256"):
        create_candidate_store("pgvector", "postgresql+asyncpg://localhost/nutrilens", 384)


def test_evaluation_comparison_reports_quality_and_latency_regressions():
    comparison = compare_evaluation_metrics(
        {"source_recall_at_3": 0.8, "retrieval_latency_p95_ms": 30.0},
        {"source_recall_at_3": 1.0, "retrieval_latency_p95_ms": 20.0},
    )

    assert comparison["regression_count"] == 2
    assert comparison["deltas"]["source_recall_at_3"] == -0.2


def test_prometheus_registry_exposes_request_count_and_latency():
    registry = MetricsRegistry()
    registry.observe_http("GET", "/api/products/123", 200, 12.5)

    output = registry.render_prometheus()
    assert 'nutrilens_http_requests_total{method="GET",route="/api/products/123",status="200"} 1' in output
    assert "nutrilens_http_request_duration_seconds_sum" in output


def test_hybrid_retrieval_exposes_lexical_semantic_and_fused_scores():
    embedder = FeatureHashEmbedding(128)
    texts = ["Đường cao trên nhãn thực phẩm cần được hạn chế.", "Protein hỗ trợ duy trì mô cơ."]
    vectors = embedder.embed(texts)
    chunks = [
        IndexedChunk(
            id=str(index),
            source_filename=filename,
            source_title=filename,
            source_url=None,
            content=text,
            heading_path=(),
            metadata={},
            embedding=tuple(vector),
            embedding_model=embedder.model_name,
        )
        for index, (filename, text, vector) in enumerate(
            zip(["sugar.md", "protein.md"], texts, vectors, strict=True)
        )
    ]

    hits = HybridRetriever(chunks, embedder).search("Sản phẩm nhiều đường có sao không?")

    assert hits[0].chunk.source_filename == "sugar.md"
    assert hits[0].lexical_score > 0
    assert hits[0].semantic_score > 0
    assert hits[0].fused_score > 0


def test_answer_context_adds_same_source_companion_chunk():
    embedder = FeatureHashEmbedding(128)

    def hit(index: int, source: str) -> RetrievalHit:
        return RetrievalHit(
            chunk=IndexedChunk(
                id=f"{source}:{index}",
                source_filename=source,
                source_title=source,
                source_url=None,
                content=f"{source} chunk {index}",
                heading_path=(),
                metadata={},
                embedding=tuple(embedder.embed([source])[0]),
                embedding_model=embedder.model_name,
            ),
            fused_score=1 / (index + 1),
            lexical_score=1.0,
            semantic_score=0.5,
        )

    selected = _select_answer_context(
        [
            hit(0, "food_allergens.md"),
            hit(1, "hypertension.md"),
            hit(2, "vegetarian.md"),
            hit(3, "children.md"),
            hit(4, "food_allergens.md"),
        ]
    )

    assert [item.chunk.id for item in selected] == [
        "food_allergens.md:0",
        "hypertension.md:1",
        "vegetarian.md:2",
        "food_allergens.md:4",
    ]


@pytest.mark.asyncio
async def test_release_pipeline_supports_lineage_runtime_evaluation_and_rollback(rag_session: AsyncSession):
    first = await ingest_knowledge_release(rag_session, version="portfolio-rag-001")
    assert first.status == "draft"
    assert first.document_count >= 10
    assert first.chunk_count >= first.document_count
    assert len(first.manifest_hash) == 64
    assert await rag_session.scalar(select(func.count()).select_from(RagChunk).where(RagChunk.release_id == first.id))

    first = (await KnowledgeReleaseControl(rag_session).publish(first.id)).release
    answer = await answer_with_retrieval(rag_session, "Protein trên nhãn dinh dưỡng có ý nghĩa gì?")
    assert answer.release_version == first.version
    assert answer.retrieval_strategy == "hybrid_release:sqlalchemy_json"
    assert answer.citations[0].source == "protein_basics.md"
    assert answer.citations[0].lexical_score is not None
    assert answer.citations[0].semantic_score is not None
    assert answer.retrieval_trace["spec"]["retrieval_backend"] == "sqlalchemy_json"

    evaluation = await evaluate_cases(
        rag_session,
        [
            {
                "id": "protein-eval",
                "question": "Protein trên nhãn dinh dưỡng có ý nghĩa gì?",
                "expected_route": "rag",
                "expected_sources": ["protein_basics.md"],
                "required_facts": ["protein"],
                "should_abstain": False,
            },
            {
                "id": "abstain-eval",
                "question": "XZ-991 chữa bệnh gì?",
                "expected_route": "rag",
                "should_abstain": True,
            },
        ],
        dataset_name="test-dataset",
        dataset_hash="a" * 64,
    )
    assert evaluation.metrics_json["route_accuracy"] == 1.0
    assert evaluation.metrics_json["abstain_accuracy"] == 1.0
    assert evaluation.metrics_json["mean_reciprocal_rank"] == 1.0
    assert evaluation.metrics_json["slices"]
    assert evaluation.metrics_json["confidence_intervals"]["route_accuracy"]["upper"] == 1.0

    second = await ingest_knowledge_release(rag_session, version="portfolio-rag-002")
    assert second.metrics_json["reused_embedding_count"] == second.chunk_count
    second = (await KnowledgeReleaseControl(rag_session).publish(second.id)).release
    await rag_session.refresh(first)
    assert second.status == "published"
    assert first.status == "retired"
    restored = await rollback_release(rag_session)
    assert restored.id == first.id
    assert restored.status == "published"

    quality = await build_data_quality_report(rag_session)
    assert quality["knowledge"]["release_count"] == 2
    assert quality["knowledge"]["chunk_count"] >= first.chunk_count * 2
    assert quality["knowledge"]["empty_embeddings"] == 0
    assert await rag_session.scalar(select(func.count()).select_from(DataPipelineRun)) == 2
    assert await rag_session.scalar(select(func.count()).select_from(RagRelease)) == 2


@pytest.mark.asyncio
async def test_evaluation_gate_scores_draft_release_and_persists_decision(rag_session: AsyncSession):
    release = await ingest_knowledge_release(rag_session, version="gate-candidate-001")
    cases = [
        {
            "id": "protein-gate",
            "question": "Protein trên nhãn dinh dưỡng có ý nghĩa gì?",
            "expected_route": "rag",
            "expected_sources": ["protein_basics.md"],
            "required_facts": ["protein"],
            "should_abstain": False,
        },
        {
            "id": "unknown-gate",
            "question": "XZ-991 chữa bệnh gì?",
            "expected_route": "rag",
            "should_abstain": True,
        },
    ]

    decision = await evaluate_release_gate(
        rag_session,
        release.id,
        cases,
        dataset_name="gate-test",
        dataset_hash="b" * 64,
    )

    assert decision.passed is True
    assert decision.release_id == release.id
    await rag_session.refresh(release)
    assert release.status == "draft"
    assert release.metrics_json["evaluation_gate"]["passed"] is True

    failed = await evaluate_release_gate(
        rag_session,
        release.id,
        cases,
        dataset_name="gate-test-strict",
        dataset_hash="c" * 64,
        thresholds=EvaluationThresholds(retrieval_latency_p95_ms=-1.0),
    )
    assert failed.passed is False
    assert failed.failures[0]["metric"] == "retrieval_latency_p95_ms"


@pytest.mark.asyncio
async def test_orchestration_runs_ingest_gate_and_publish_with_stage_lineage(rag_session: AsyncSession):
    run = await run_knowledge_release_pipeline(rag_session, version="orchestrated-001")

    assert run.status == "succeeded"
    assert [stage["name"] for stage in run.metrics_json["stages"]] == [
        "ingest",
        "evaluation_gate",
        "publish",
    ]
    release = await rag_session.get(RagRelease, run.metrics_json["release_id"])
    assert release is not None
    assert release.status == "published"
    assert release.metrics_json["reused_embedding_count"] == 0
    snapshot = await build_observability_snapshot(rag_session)
    assert snapshot["rag"]["active_release"] == "orchestrated-001"
    assert snapshot["pipelines"]["succeeded_count"] >= 2
    marts = await build_analytics_marts(rag_session)
    assert marts["fct_pipeline_daily"][0]["run_count"] >= 1
    assert marts["mart_product_quality"]["product_count"] == 0
    assert marts["semantic_catalog"]
    store = MemoryArtifactStore()
    artifacts = await export_release_artifacts(rag_session, release.id, store)
    assert set(artifacts) == {"bronze", "silver", "gold"}
    assert len(store.objects) == 3
