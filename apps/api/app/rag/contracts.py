from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceDocument:
    filename: str
    title: str
    body: str
    metadata: dict
    document_id: str | None = None


@dataclass(frozen=True)
class ChunkDraft:
    source_filename: str
    source_title: str
    source_url: str | None
    source_document_id: str | None
    chunk_index: int
    heading_path: tuple[str, ...]
    content: str
    content_hash: str
    token_count: int
    metadata: dict


@dataclass(frozen=True)
class IndexedChunk:
    id: str
    source_filename: str
    source_title: str
    source_url: str | None
    content: str
    heading_path: tuple[str, ...]
    metadata: dict
    embedding: tuple[float, ...]
    embedding_model: str


@dataclass(frozen=True)
class RetrievalHit:
    chunk: IndexedChunk
    fused_score: float
    lexical_score: float
    semantic_score: float
    lexical_rank: int | None = None
    semantic_rank: int | None = None
    debug: dict = field(default_factory=dict)
