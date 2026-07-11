from datetime import UTC, datetime
from hashlib import sha256
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import DataPipelineRun, RagChunk, RagDocument, RagRelease
from app.rag.chunking import chunk_document
from app.rag.contracts import IndexedChunk, SourceDocument
from app.rag.embeddings import create_embedding_provider
from app.rag.service import has_prompt_injection_risk, load_documents, validate_metadata


async def collect_approved_sources(session: AsyncSession) -> list[SourceDocument]:
    sources = {
        document.filename: SourceDocument(
            filename=document.filename,
            title=document.title,
            body=document.body,
            metadata=document.metadata,
        )
        for document in load_documents()
    }
    result = await session.execute(select(RagDocument).where(RagDocument.status == "approved"))
    for document in result.scalars().all():
        sources[document.filename] = SourceDocument(
            filename=document.filename,
            title=document.title,
            body=document.content,
            metadata=document.metadata_json or {},
            document_id=document.id,
        )
    return list(sources.values())


async def ingest_knowledge_release(
    session: AsyncSession,
    *,
    version: str | None = None,
) -> RagRelease:
    settings = get_settings()
    embedder = create_embedding_provider(
        provider=settings.rag_embedding_provider,
        dimensions=settings.rag_embedding_dimensions,
        sentence_transformer_model=settings.rag_sentence_transformer_model,
    )
    config = {
        "chunk_size_tokens": settings.rag_chunk_size_tokens,
        "chunk_overlap_tokens": settings.rag_chunk_overlap_tokens,
        "embedding_dimensions": settings.rag_embedding_dimensions,
        "embedding_provider": settings.rag_embedding_provider,
        "embedding_model": embedder.model_name,
    }
    run = DataPipelineRun(pipeline="knowledge_ingestion", status="running", config_json=config)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    started = perf_counter()
    try:
        sources = await collect_approved_sources(session)
        run.input_count = len(sources)
        accepted: list[SourceDocument] = []
        rejections: list[dict[str, str | list[str]]] = []
        for source in sources:
            missing = validate_metadata(source.metadata)
            if missing:
                rejections.append({"filename": source.filename, "reason": "missing_metadata", "fields": missing})
            elif has_prompt_injection_risk(source.body):
                rejections.append({"filename": source.filename, "reason": "prompt_injection_risk"})
            elif not source.body.strip():
                rejections.append({"filename": source.filename, "reason": "empty_content"})
            else:
                accepted.append(source)
        if not accepted:
            raise ValueError("No valid approved documents are available for ingestion.")

        drafts = [
            chunk
            for source in accepted
            for chunk in chunk_document(
                source,
                max_tokens=settings.rag_chunk_size_tokens,
                overlap_tokens=settings.rag_chunk_overlap_tokens,
            )
        ]
        existing_chunks = await session.execute(
            select(RagChunk).where(
                RagChunk.content_hash.in_([draft.content_hash for draft in drafts]),
                RagChunk.embedding_model == embedder.model_name,
            )
        )
        reusable = {chunk.content_hash: chunk.embedding for chunk in existing_chunks.scalars().all() if chunk.embedding}
        missing_contents = [draft.content for draft in drafts if draft.content_hash not in reusable]
        generated = iter(embedder.embed(missing_contents))
        embeddings = [reusable.get(draft.content_hash) or next(generated) for draft in drafts]
        reused_embedding_count = sum(draft.content_hash in reusable for draft in drafts)
        manifest_material = "\n".join(
            f"{source.filename}:{sha256(source.body.encode()).hexdigest()}"
            for source in sorted(accepted, key=lambda item: item.filename)
        )
        manifest_hash = sha256((manifest_material + repr(sorted(config.items()))).encode()).hexdigest()
        release_version = version or f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{manifest_hash[:8]}"
        existing = await session.scalar(select(RagRelease).where(RagRelease.version == release_version))
        if existing is not None:
            raise ValueError(f"Knowledge release {release_version} already exists.")
        release = RagRelease(
            version=release_version,
            status="draft",
            manifest_hash=manifest_hash,
            pipeline_run_id=run.id,
            document_count=len(accepted),
            chunk_count=len(drafts),
            metrics_json={
                "total_tokens": sum(draft.token_count for draft in drafts),
                "average_chunk_tokens": round(sum(draft.token_count for draft in drafts) / len(drafts), 2),
                "embedding_model": embedder.model_name,
                "rejections": rejections,
                "reused_embedding_count": reused_embedding_count,
                "generated_embedding_count": len(drafts) - reused_embedding_count,
            },
        )
        session.add(release)
        await session.flush()
        session.add_all(
            [
                RagChunk(
                    release_id=release.id,
                    source_document_id=draft.source_document_id,
                    source_filename=draft.source_filename,
                    source_title=draft.source_title,
                    source_url=draft.source_url,
                    chunk_index=draft.chunk_index,
                    heading_path=list(draft.heading_path),
                    content=draft.content,
                    content_hash=draft.content_hash,
                    token_count=draft.token_count,
                    metadata_json=draft.metadata,
                    embedding=embedding,
                    embedding_model=embedder.model_name,
                )
                for draft, embedding in zip(drafts, embeddings, strict=True)
            ]
        )
        run.status = "succeeded"
        run.output_count = len(drafts)
        run.rejected_count = len(rejections)
        run.metrics_json = {
            "release_version": release_version,
            "manifest_hash": manifest_hash,
            "documents_accepted": len(accepted),
            "reused_embedding_count": reused_embedding_count,
            "generated_embedding_count": len(drafts) - reused_embedding_count,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }
        run.finished_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(release)
        return release
    except Exception as exc:
        await session.rollback()
        persisted_run = await session.get(DataPipelineRun, run.id)
        if persisted_run is not None:
            persisted_run.status = "failed"
            persisted_run.error_message = str(exc)[:1000]
            persisted_run.finished_at = datetime.now(UTC)
            persisted_run.metrics_json = {"duration_ms": round((perf_counter() - started) * 1000, 2)}
            await session.commit()
        raise


async def _activate_release(session: AsyncSession, release_id: str) -> RagRelease:
    release = await session.get(RagRelease, release_id)
    if release is None:
        raise ValueError("Knowledge release not found.")
    if release.status not in {"draft", "retired"}:
        return release
    result = await session.execute(select(RagRelease).where(RagRelease.status == "published"))
    for current in result.scalars().all():
        current.status = "retired"
    release.status = "published"
    release.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(release)
    return release


async def rollback_release(session: AsyncSession) -> RagRelease:
    current = await session.scalar(select(RagRelease).where(RagRelease.status == "published"))
    candidates = await session.execute(
        select(RagRelease)
        .where(RagRelease.status == "retired")
        .order_by(RagRelease.published_at.desc(), RagRelease.created_at.desc())
        .limit(1)
    )
    target = candidates.scalar_one_or_none()
    if target is None:
        raise ValueError("No retired release is available for rollback.")
    if current is not None:
        current.status = "retired"
    target.status = "published"
    target.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(target)
    return target


async def active_release(session: AsyncSession) -> RagRelease | None:
    return await session.scalar(select(RagRelease).where(RagRelease.status == "published"))


async def indexed_chunks(session: AsyncSession, release_id: str) -> list[IndexedChunk]:
    result = await session.execute(
        select(RagChunk)
        .where(RagChunk.release_id == release_id)
        .order_by(RagChunk.source_filename, RagChunk.chunk_index)
    )
    return [
        IndexedChunk(
            id=chunk.id,
            source_filename=chunk.source_filename,
            source_title=chunk.source_title,
            source_url=chunk.source_url,
            content=chunk.content,
            heading_path=tuple(chunk.heading_path or []),
            metadata=chunk.metadata_json or {},
            embedding=tuple(chunk.embedding or []),
            embedding_model=chunk.embedding_model,
        )
        for chunk in result.scalars().all()
    ]
