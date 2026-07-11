import json
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import RagChunk, RagEvaluationRun, RagRelease


class ArtifactStore(Protocol):
    def put(self, key: str, payload: bytes) -> str: ...


class LocalArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, key: str, payload: bytes) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        return str(target)


class MemoryArtifactStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, payload: bytes) -> str:
        self.objects[key] = payload
        return f"memory://{key}"


async def export_release_artifacts(session: AsyncSession, release_id: str, store: ArtifactStore) -> dict:
    release = await session.get(RagRelease, release_id)
    if release is None:
        raise ValueError("Knowledge release not found.")
    chunks = (
        await session.execute(select(RagChunk).where(RagChunk.release_id == release_id).order_by(RagChunk.id))
    ).scalars().all()
    evaluations = (
        await session.execute(
            select(RagEvaluationRun)
            .where(RagEvaluationRun.release_id == release_id)
            .order_by(RagEvaluationRun.created_at)
        )
    ).scalars().all()
    prefix = f"knowledge_release={release.version}"
    manifest = {
        "release_id": release.id,
        "version": release.version,
        "status": release.status,
        "manifest_hash": release.manifest_hash,
        "document_count": release.document_count,
        "chunk_count": release.chunk_count,
        "metrics": release.metrics_json,
    }
    chunk_lines = [
        json.dumps(
            {
                "id": chunk.id,
                "source": chunk.source_filename,
                "content_hash": chunk.content_hash,
                "content": chunk.content,
                "embedding_model": chunk.embedding_model,
                "embedding": chunk.embedding,
            },
            ensure_ascii=False,
        )
        for chunk in chunks
    ]
    evaluation_lines = [
        json.dumps(
            {"id": run.id, "dataset": run.dataset_name, "metrics": run.metrics_json, "cases": run.case_results},
            ensure_ascii=False,
            default=str,
        )
        for run in evaluations
    ]
    return {
        "bronze": store.put(f"bronze/{prefix}/chunks.jsonl", "\n".join(chunk_lines).encode()),
        "silver": store.put(
            f"silver/{prefix}/evaluations.jsonl", "\n".join(evaluation_lines).encode()
        ),
        "gold": store.put(
            f"gold/{prefix}/manifest.json", json.dumps(manifest, ensure_ascii=False, default=str, indent=2).encode()
        ),
    }
