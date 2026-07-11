from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
