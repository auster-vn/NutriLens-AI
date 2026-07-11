from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import RagRelease
from app.products.scoring import DISCLAIMER
from app.rag.chunking import chunk_document
from app.rag.contracts import IndexedChunk, RetrievalHit
from app.rag.embeddings import create_embedding_provider
from app.rag.experiment import RetrievalExperiment
from app.rag.pipeline import active_release, collect_approved_sources
from app.rag.retrieval import HybridRetriever
from app.rag.service import NUTRITION_TERMS, classify_route
from app.rag.text import tokenize
from app.schemas.rag import ChatResponse, Citation


@dataclass(frozen=True)
class RetrievalContext:
    hits: list[RetrievalHit]
    strategy: str
    release_id: str | None
    release_version: str | None
    retrieval_ms: float
    trace: dict


async def retrieve(
    session: AsyncSession,
    question: str,
    limit: int = 5,
    *,
    release_id: str | None = None,
) -> RetrievalContext:
    started = perf_counter()
    settings = get_settings()
    embedder = _embedding_provider()
    result = None
    release = await session.get(RagRelease, release_id) if release_id else await active_release(session)
    if release_id and release is None:
        raise ValueError("Knowledge release not found.")
    if release is not None:
        experiment = RetrievalExperiment(settings, embedder)
        try:
            result = await experiment.run(session, release.id, question, limit)
            chunks = None
        except ValueError:
            result = None
        if result is not None:
            strategy = f"hybrid_release:{experiment.store.backend_name}"
            release_id = release.id
            release_version = release.version
            hits = result.hits
            trace = result.trace
        else:
            chunks = await _ephemeral_chunks(session)
            strategy = "hybrid_ephemeral_model_mismatch"
            release_id = None
            release_version = None
    else:
        chunks = await _ephemeral_chunks(session)
        strategy = "hybrid_ephemeral"
        release_id = None
        release_version = None
    if release is None or result is None:
        retriever = HybridRetriever(
            chunks,
            embedder,
            rrf_k=settings.rag_rrf_k,
            lexical_weight=settings.rag_lexical_weight,
            semantic_weight=settings.rag_semantic_weight,
        )
        hits = retriever.search(question, limit=max(limit * 3, 10))
        trace = {"candidate_count": len(chunks), "returned_count": len(hits), "release_id": None}
    # Feature hashing adds recall but lexical evidence remains the safety gate.
    hits = [hit for hit in hits if hit.lexical_score > 0]
    if hits:
        relative_floor = hits[0].fused_score * 0.72
        hits = [hit for hit in hits if hit.fused_score >= relative_floor]
    return RetrievalContext(
        hits=hits[:limit],
        strategy=strategy,
        release_id=release_id,
        release_version=release_version,
        retrieval_ms=round((perf_counter() - started) * 1000, 2),
        trace=trace,
    )


async def answer_with_retrieval(
    session: AsyncSession,
    question: str,
    barcode: str | None = None,
    *,
    release_id: str | None = None,
) -> ChatResponse:
    context = await retrieve(session, question, limit=6, release_id=release_id)
    route = classify_route(question, barcode)
    if not set(tokenize(question)) & NUTRITION_TERMS:
        context = RetrievalContext(
            [],
            context.strategy,
            context.release_id,
            context.release_version,
            context.retrieval_ms,
            context.trace,
        )
    if not context.hits:
        return ChatResponse(
            route=route,
            answer="Mình chưa có đủ nguồn đáng tin trong kho kiến thức để trả lời chắc chắn.",
            citations=[],
            abstained=True,
            disclaimer=DISCLAIMER,
            retrieval_strategy=context.strategy,
            release_version=context.release_version,
            retrieval_ms=context.retrieval_ms,
            retrieval_trace=context.trace,
        )
    selected = _select_answer_context(context.hits)
    product_prefix = ""
    if route in {"product", "mixed"}:
        product_prefix = (
            f"Với barcode {barcode}, các số liệu sản phẩm phải lấy từ cache/Open Food Facts. "
            if barcode
            else "Nếu câu hỏi liên quan sản phẩm cụ thể, cần barcode hoặc dữ liệu sản phẩm trước khi kết luận. "
        )
    answer = product_prefix + " ".join(_sentence(hit.chunk.content) for hit in selected)
    if route == "product" and not barcode:
        answer += " Hiện chưa có barcode nên mình không thể xác nhận thông tin riêng của sản phẩm."
    return ChatResponse(
        route=route,
        answer=answer,
        citations=[_citation(hit) for hit in selected],
        abstained=False,
        disclaimer=DISCLAIMER,
        retrieval_strategy=context.strategy,
        release_version=context.release_version,
        retrieval_ms=context.retrieval_ms,
        retrieval_trace=context.trace,
    )


async def _ephemeral_chunks(session: AsyncSession) -> list[IndexedChunk]:
    settings = get_settings()
    sources = await collect_approved_sources(session)
    drafts = [
        chunk
        for source in sources
        for chunk in chunk_document(
            source,
            max_tokens=settings.rag_chunk_size_tokens,
            overlap_tokens=settings.rag_chunk_overlap_tokens,
        )
    ]
    embedder = _embedding_provider()
    embeddings = embedder.embed([draft.content for draft in drafts])
    return [
        IndexedChunk(
            id=f"ephemeral:{draft.source_filename}:{draft.chunk_index}",
            source_filename=draft.source_filename,
            source_title=draft.source_title,
            source_url=draft.source_url,
            content=draft.content,
            heading_path=draft.heading_path,
            metadata=draft.metadata,
            embedding=tuple(embedding),
            embedding_model=embedder.model_name,
        )
        for draft, embedding in zip(drafts, embeddings, strict=True)
    ]


def _embedding_provider():
    settings = get_settings()
    return create_embedding_provider(
        provider=settings.rag_embedding_provider,
        dimensions=settings.rag_embedding_dimensions,
        sentence_transformer_model=settings.rag_sentence_transformer_model,
    )


def _citation(hit: RetrievalHit) -> Citation:
    return Citation(
        source=hit.chunk.source_filename,
        title=hit.chunk.source_title,
        source_url=hit.chunk.source_url,
        snippet=hit.chunk.content[:420],
        chunk_id=hit.chunk.id,
        heading_path=list(hit.chunk.heading_path),
        lexical_score=round(hit.lexical_score, 6),
        semantic_score=round(hit.semantic_score, 6),
        fused_score=round(hit.fused_score, 8),
    )


def _select_answer_context(hits: list[RetrievalHit], primary_limit: int = 3, max_chunks: int = 4) -> list[RetrievalHit]:
    selected = hits[:primary_limit]
    seen = {hit.chunk.id for hit in selected}
    primary_sources = {hit.chunk.source_filename for hit in selected}
    for hit in hits[primary_limit:]:
        if len(selected) >= max_chunks:
            break
        if hit.chunk.id in seen:
            continue
        if hit.chunk.source_filename in primary_sources:
            selected.append(hit)
            seen.add(hit.chunk.id)
    return selected


def _sentence(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    return cleaned if cleaned.endswith((".", "!", "?")) else cleaned + "."
