from dataclasses import asdict, dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.rag.contracts import RetrievalHit
from app.rag.embeddings import EmbeddingProvider
from app.rag.retrieval import HybridRetriever
from app.rag.vector_store import create_candidate_store


@dataclass(frozen=True)
class RetrievalExperimentSpec:
    embedding_model: str
    retrieval_backend: str
    candidate_limit: int
    rrf_k: int
    lexical_weight: float
    semantic_weight: float


@dataclass(frozen=True)
class RetrievalExperimentResult:
    hits: list[RetrievalHit]
    trace: dict


class RetrievalExperiment:
    def __init__(self, settings: Settings, embedder: EmbeddingProvider) -> None:
        self.settings = settings
        self.embedder = embedder
        self.store = create_candidate_store(
            settings.rag_retrieval_backend,
            settings.database_url,
            settings.rag_embedding_dimensions,
        )
        self.spec = RetrievalExperimentSpec(
            embedding_model=embedder.model_name,
            retrieval_backend=self.store.backend_name,
            candidate_limit=settings.rag_candidate_limit,
            rrf_k=settings.rag_rrf_k,
            lexical_weight=settings.rag_lexical_weight,
            semantic_weight=settings.rag_semantic_weight,
        )

    async def run(self, session: AsyncSession, release_id: str, query: str, limit: int) -> RetrievalExperimentResult:
        chunks = await self.store.load_candidates(
            session,
            release_id=release_id,
            query=query,
            query_embedding=self.embedder.embed([query])[0],
            limit=self.spec.candidate_limit,
        )
        if chunks and {chunk.embedding_model for chunk in chunks} != {self.embedder.model_name}:
            raise ValueError("Knowledge Release embedding model does not match the Retrieval Experiment.")
        hits = HybridRetriever(
            chunks,
            self.embedder,
            rrf_k=self.spec.rrf_k,
            lexical_weight=self.spec.lexical_weight,
            semantic_weight=self.spec.semantic_weight,
        ).search(query, limit=max(limit * 3, 10))
        return RetrievalExperimentResult(
            hits=hits,
            trace={
                "spec": asdict(self.spec),
                "candidate_count": len(chunks),
                "returned_count": len(hits),
                "release_id": release_id,
            },
        )
