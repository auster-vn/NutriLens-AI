from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str
    title: str
    source_url: str | None = None
    snippet: str
    chunk_id: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    lexical_score: float | None = None
    semantic_score: float | None = None
    fused_score: float | None = None


class RagSearchRequest(BaseModel):
    question: str
    limit: int = Field(default=5, ge=1, le=10)


class RagSearchOut(BaseModel):
    query: str
    results: list[Citation]


class ChatRequest(BaseModel):
    question: str
    barcode: str | None = None


class ChatResponse(BaseModel):
    route: str
    answer: str
    citations: list[Citation]
    abstained: bool = False
    disclaimer: str
    retrieval_strategy: str = "lexical_fallback"
    release_version: str | None = None
    retrieval_ms: float | None = None
    retrieval_trace: dict | None = None


class AdminDocumentIn(BaseModel):
    filename: str
    title: str
    metadata: dict
    content: str


class AdminDocumentOut(AdminDocumentIn):
    id: str
    status: str
    content_hash: str | None = None
    version: int = 1


class RagIngestRequest(BaseModel):
    version: str | None = Field(default=None, min_length=3, max_length=64)
    publish: bool = False


class RagReleaseOut(BaseModel):
    id: str
    version: str
    status: str
    manifest_hash: str
    pipeline_run_id: str
    document_count: int
    chunk_count: int
    metrics: dict
    created_at: datetime
    published_at: datetime | None = None


class PipelineRunOut(BaseModel):
    id: str
    pipeline: str
    status: str
    config: dict
    input_count: int
    output_count: int
    rejected_count: int
    metrics: dict
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class EvaluationRunOut(BaseModel):
    id: str
    release_id: str | None
    dataset_name: str
    dataset_hash: str
    metrics: dict
    case_results: list[dict]
    created_at: datetime


class EvaluationGateOut(BaseModel):
    passed: bool
    release_id: str
    evaluation_run_id: str
    thresholds: dict[str, float]
    metrics: dict
    failures: list[dict]
