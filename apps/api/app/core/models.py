from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProductCache(Base):
    __tablename__ = "product_cache"

    barcode: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(255))
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    ingredients_text: Mapped[str | None] = mapped_column(Text)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    additives: Mapped[list[str]] = mapped_column(JSON, default=list)
    nutriments: Mapped[dict] = mapped_column(JSON, default=dict)
    nutriscore: Mapped[str | None] = mapped_column(String(8))
    ecoscore: Mapped[str | None] = mapped_column(String(8))
    image_url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), default="open_food_facts")
    raw_summary: Mapped[dict | None] = mapped_column(JSON)
    completeness_score: Mapped[float] = mapped_column(Float, default=0)
    cached_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ProductLabelExtraction(Base):
    __tablename__ = "product_label_extractions"
    __table_args__ = (
        Index("ix_product_label_extractions_barcode_created", "barcode", "created_at"),
        Index("ix_product_label_extractions_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    barcode: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="needs_review")
    image_sha256: Mapped[str] = mapped_column(String(64))
    image_mime: Mapped[str] = mapped_column(String(64))
    ocr_provider: Mapped[str] = mapped_column(String(64))
    extractor_version: Mapped[str] = mapped_column(String(32))
    raw_text: Mapped[str] = mapped_column(Text)
    words_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    preprocessing_json: Mapped[dict] = mapped_column(JSON, default=dict)
    provider_runs_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    extracted_json: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    validation_issues: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ScanHistory(Base):
    __tablename__ = "scan_history"
    __table_args__ = (
        Index("ix_scan_history_user_created", "user_id", "created_at"),
        Index("ix_scan_history_barcode_created", "barcode", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    barcode: Mapped[str] = mapped_column(ForeignKey("product_cache.barcode"))
    score: Mapped[int | None] = mapped_column(Integer)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (Index("ix_user_profiles_goal", "goal"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age_group: Mapped[str | None] = mapped_column(String(32))
    goal: Mapped[str] = mapped_column(String(32), default="general")
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    diet: Mapped[str | None] = mapped_column(String(32))
    disliked_ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    budget_daily: Mapped[float | None] = mapped_column(Float)
    biological_sex: Mapped[str | None] = mapped_column(String(16))
    age: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    activity_level: Mapped[str | None] = mapped_column(String(32))
    target_weight_loss_kg_week: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PantryItem(Base):
    __tablename__ = "pantry_items"
    __table_args__ = (
        Index("ix_pantry_items_user_expiry", "user_id", "expiry_date"),
        Index("ix_pantry_items_barcode", "barcode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    barcode: Mapped[str] = mapped_column(ForeignKey("product_cache.barcode"))
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    expiry_date: Mapped[date | None] = mapped_column(Date)
    storage_location: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MealPlan(Base):
    __tablename__ = "meal_plans"
    __table_args__ = (Index("ix_meal_plans_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    days: Mapped[int] = mapped_column(Integer)
    budget: Mapped[float | None] = mapped_column(Float)
    goal: Mapped[str | None] = mapped_column(String(32))
    plan: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RagDocument(Base):
    __tablename__ = "rag_documents"
    __table_args__ = (Index("ix_rag_documents_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AdminOperationAudit(Base):
    __tablename__ = "admin_operation_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    operation: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProductFavorite(Base):
    __tablename__ = "product_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "barcode", name="uq_product_favorites_user_barcode"),
        Index("ix_product_favorites_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    barcode: Mapped[str] = mapped_column(ForeignKey("product_cache.barcode"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RagAnswerAudit(Base):
    __tablename__ = "rag_answer_audit"
    __table_args__ = (Index("ix_rag_answer_audit_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    question_hash: Mapped[str] = mapped_column(String(64))
    route: Mapped[str] = mapped_column(String(32))
    abstained: Mapped[bool] = mapped_column(Boolean)
    citation_count: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DataPipelineRun(Base):
    __tablename__ = "data_pipeline_runs"
    __table_args__ = (Index("ix_data_pipeline_runs_pipeline_started", "pipeline", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pipeline: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="running")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    input_count: Mapped[int] = mapped_column(Integer, default=0)
    output_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class RagRelease(Base):
    __tablename__ = "rag_releases"
    __table_args__ = (
        Index("ix_rag_releases_status_created", "status", "created_at"),
        UniqueConstraint("version", name="uq_rag_releases_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    manifest_hash: Mapped[str] = mapped_column(String(64))
    pipeline_run_id: Mapped[str] = mapped_column(ForeignKey("data_pipeline_runs.id"))
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("release_id", "source_filename", "chunk_index", name="uq_rag_chunk_release_source_index"),
        Index("ix_rag_chunks_release_source", "release_id", "source_filename"),
        Index("ix_rag_chunks_content_hash", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    release_id: Mapped[str] = mapped_column(ForeignKey("rag_releases.id"))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("rag_documents.id", ondelete="SET NULL"))
    source_filename: Mapped[str] = mapped_column(String(255))
    source_title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float]] = mapped_column(JSON, default=list)
    embedding_model: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RagEvaluationRun(Base):
    __tablename__ = "rag_evaluation_runs"
    __table_args__ = (Index("ix_rag_evaluation_runs_release_created", "release_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    release_id: Mapped[str | None] = mapped_column(ForeignKey("rag_releases.id"))
    dataset_name: Mapped[str] = mapped_column(String(255))
    dataset_hash: Mapped[str] = mapped_column(String(64))
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    case_results: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LabelOcrEvaluationRun(Base):
    __tablename__ = "label_ocr_evaluation_runs"
    __table_args__ = (Index("ix_label_ocr_evaluation_runs_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_name: Mapped[str] = mapped_column(String(255))
    dataset_hash: Mapped[str] = mapped_column(String(64))
    providers: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    case_results: Mapped[list[dict]] = mapped_column(JSON, default=list)
    readiness_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
