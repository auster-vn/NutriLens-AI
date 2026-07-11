# Data Platform

NutriLens has two data planes:

- Product Data: Open Food Facts normalization, cache freshness, stale fallback, and personalized scoring inputs.
- Knowledge Data: curated nutrition evidence, approved admin documents, immutable RAG releases, chunk lineage, embeddings, and evaluation evidence.

## Knowledge Lineage

```text
SourceDocument
  -> ChunkDraft
  -> RagChunk
  -> RagRelease
  -> RetrievalHit
  -> Citation
  -> RagEvaluationRun
```

Each `RagChunk` stores source filename, source title, optional source URL, source document ID, heading path, content hash, token count, metadata, embedding vector, and embedding model. This makes a citation explainable after the original admin document changes or disappears.

Ingestion uses `content_hash + embedding_model` as a content-addressed cache key. Unchanged chunks receive new release lineage while reusing vectors; run metrics report generated and reused embedding counts.

## Pipeline Runs

`data_pipeline_runs` captures operational history for ingestion:

- config JSON: chunking and embedding settings
- input count: candidate documents
- output count: generated chunks
- rejected count: invalid documents
- status and error message
- duration and release manifest

The pipeline commits the run before processing so failures are visible as data, not just logs. The parent orchestrator runs ingest, evaluation gate, and publish as explicit stages; gate failures leave the candidate in draft and mark the run `blocked`. An optional Prefect flow wraps the same framework-neutral core.

## Quality Report

```bash
npm run data:quality
```

The report includes:

- product cache count, completeness, stale ratio, and missing field rates
- knowledge release count, published release, chunk count, duplicate chunk hashes
- empty embeddings and embedding model distribution
- pipeline success/failure counts and latest run metadata

This gives interviewers a concrete observability story: data quality is queryable, versioned, and tied to release operations.

## Release Semantics

- Draft releases are immutable candidates.
- Publishing one release retires the previous published release.
- Rollback restores the latest retired release.
- Runtime answers use the published release when the stored embedding model matches the configured adapter.
- If a model mismatch is detected, runtime falls back to ephemeral retrieval and marks the strategy as `hybrid_ephemeral_model_mismatch`.

## Local And Production Modes

SQLite is supported for local development and tests. PostgreSQL migrations live in `infra/migrations` and define the production schema. PostgreSQL uses full-text candidate retrieval plus pgvector cosine search, then applies the same hybrid reranker as local mode. The compose database image includes pgvector and startup applies idempotent vector bootstrap statements.

## Analytics And Metrics

`GET /metrics` exposes Prometheus-compatible HTTP counters and latency summaries. Admin observability adds RAG abstention, citation coverage, evaluation, and pipeline reliability metrics. `npm run data:analytics` builds runtime marts; `analytics/` contains dbt-ready daily RAG and pipeline models for a warehouse deployment.

The semantic catalog defines each metric's meaning, grain, owner, and freshness before marts expose values.

## Data Artifacts

`python -m app.data.cli export-release <release-id> --output artifacts` exports immutable bronze, silver, and gold artifacts. Local filesystem and in-memory adapters share one storage seam; object storage can replace them when volume or retention requires it.
