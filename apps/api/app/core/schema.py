import logging

from app.core.models import Base
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

SQLITE_COMPAT_MIGRATIONS = [
    "alter table product_cache add column raw_summary JSON",
    "alter table product_cache add column completeness_score FLOAT default 0",
    "alter table product_cache add column cached_at DATETIME default CURRENT_TIMESTAMP",
    "alter table rag_documents add column content_hash VARCHAR(64)",
    "alter table rag_documents add column version INTEGER default 1",
    "alter table rag_documents add column updated_at DATETIME default CURRENT_TIMESTAMP",
    "create index if not exists ix_scan_history_user_created on scan_history(user_id, created_at)",
    "create index if not exists ix_scan_history_barcode_created on scan_history(barcode, created_at)",
    "create index if not exists ix_pantry_items_user_expiry on pantry_items(user_id, expiry_date)",
    "create index if not exists ix_pantry_items_barcode on pantry_items(barcode)",
    "create index if not exists ix_meal_plans_user_created on meal_plans(user_id, created_at)",
    "create index if not exists ix_rag_documents_status on rag_documents(status)",
    "create index if not exists ix_data_pipeline_runs_pipeline_started on data_pipeline_runs(pipeline, started_at)",
    "create index if not exists ix_rag_releases_status_created on rag_releases(status, created_at)",
    "create index if not exists ix_rag_chunks_release_source on rag_chunks(release_id, source_filename)",
    "create index if not exists ix_rag_chunks_content_hash on rag_chunks(content_hash)",
    "create index if not exists ix_rag_evaluation_runs_release_created on rag_evaluation_runs(release_id, created_at)",
    "alter table user_profiles add column biological_sex VARCHAR(16)",
    "alter table user_profiles add column age INTEGER",
    "alter table user_profiles add column height_cm FLOAT",
    "alter table user_profiles add column weight_kg FLOAT",
    "alter table user_profiles add column activity_level VARCHAR(32)",
    "alter table user_profiles add column target_weight_loss_kg_week FLOAT",
    "alter table product_label_extractions add column words_json JSON default '[]'",
    "alter table product_label_extractions add column preprocessing_json JSON default '{}'",
    "alter table product_label_extractions add column provider_runs_json JSON default '[]'",
]

POSTGRES_VECTOR_BOOTSTRAP = [
    "alter table user_profiles add column if not exists biological_sex VARCHAR(16)",
    "alter table user_profiles add column if not exists age INTEGER",
    "alter table user_profiles add column if not exists height_cm DOUBLE PRECISION",
    "alter table user_profiles add column if not exists weight_kg DOUBLE PRECISION",
    "alter table user_profiles add column if not exists activity_level VARCHAR(32)",
    "alter table user_profiles add column if not exists target_weight_loss_kg_week DOUBLE PRECISION",
    "alter table product_label_extractions add column if not exists words_json JSONB not null default '[]'::jsonb",
    "alter table product_label_extractions add column if not exists "
    "preprocessing_json JSONB not null default '{}'::jsonb",
    "alter table product_label_extractions add column if not exists "
    "provider_runs_json JSONB not null default '[]'::jsonb",
    "create extension if not exists vector",
    "alter table rag_chunks add column if not exists embedding_vector vector(256)",
    """
    create or replace function sync_rag_chunk_embedding_vector()
    returns trigger language plpgsql as $$
    begin
      new.embedding_vector := case
        when new.embedding is null or jsonb_array_length(new.embedding::jsonb) = 0 then null
        else new.embedding::text::vector
      end;
      return new;
    end;
    $$
    """,
    "drop trigger if exists trg_rag_chunk_embedding_vector on rag_chunks",
    """
    create trigger trg_rag_chunk_embedding_vector before insert or update of embedding on rag_chunks
    for each row execute function sync_rag_chunk_embedding_vector()
    """,
    """
    update rag_chunks set embedding_vector = embedding::text::vector
    where jsonb_array_length(embedding::jsonb) = 256 and embedding_vector is null
    """,
    """
    create index if not exists ix_rag_chunks_embedding_hnsw
    on rag_chunks using hnsw (embedding_vector vector_cosine_ops)
    """,
    """
    create index if not exists ix_rag_chunks_content_fts
    on rag_chunks using gin (to_tsvector('simple', source_title || ' ' || content))
    """,
]


async def initialize_schema(engine: AsyncEngine, database_url: str) -> None:
    logger = logging.getLogger("nutrilens.schema")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if database_url.startswith("sqlite"):
            for statement in SQLITE_COMPAT_MIGRATIONS:
                try:
                    await connection.execute(text(statement))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Schema compatibility step skipped: %s - %s", statement[:60], exc)
        elif database_url.startswith("postgresql"):
            for statement in POSTGRES_VECTOR_BOOTSTRAP:
                await connection.execute(text(statement))
