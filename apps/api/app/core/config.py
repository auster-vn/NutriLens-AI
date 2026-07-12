from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("postgresql"):
        return database_url

    normalized = database_url
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(normalized)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    rewritten_query: list[tuple[str, str]] = []
    sslmode: str | None = None
    for key, value in query_items:
        if key == "sslmode":
            sslmode = value
            continue
        if key == "channel_binding":
            continue
        rewritten_query.append((key, value))

    if sslmode and not any(key == "ssl" for key, _ in rewritten_query):
        rewritten_query.append(("ssl", sslmode))

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(rewritten_query), parts.fragment))


class Settings(BaseSettings):
    app_name: str = "NutriLens AI"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str = Field(default="sqlite+aiosqlite:///./nutrilens.db")
    open_food_facts_base_url: str = "https://world.openfoodfacts.org"
    admin_key: str = "dev-admin-key"
    request_timeout_seconds: float = 12.0
    product_cache_ttl_hours: int = 168
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    jwt_secret: str = "dev-only-change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 10080
    auth_cookie_name: str = "nutrilens_session"
    auth_cookie_secure: bool = False
    rag_chunk_size_tokens: int = 140
    rag_chunk_overlap_tokens: int = 24
    rag_embedding_provider: str = "feature_hash"
    rag_embedding_dimensions: int = 256
    rag_sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_rrf_k: int = 60
    rag_lexical_weight: float = 1.0
    rag_semantic_weight: float = 0.8
    rag_retrieval_backend: str = "auto"
    rag_candidate_limit: int = 80
    label_ocr_providers: str = "tesseract,paddleocr"
    label_ocr_quality_threshold: float = 0.4
    label_ocr_benchmark_min_cases_for_layoutlm: int = 200
    label_ocr_benchmark_min_field_f1: float = 0.85

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    def validate_production_secrets(self) -> None:
        if self.environment != "production":
            return
        if self.jwt_secret.startswith("dev-only") or len(self.jwt_secret) < 32:
            raise RuntimeError("NUTRILENS_JWT_SECRET must be a strong production secret.")
        if self.admin_key == "dev-admin-key":
            raise RuntimeError("NUTRILENS_ADMIN_KEY must be changed in production.")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="NUTRILENS_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
