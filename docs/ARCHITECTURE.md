# Architecture

## Design goals

NutriLens separates shared product facts from user-owned decisions and explanatory knowledge. This keeps external data caching efficient without weakening privacy or mixing product records into the knowledge corpus.

## Domain modules

### Identity

Owns registration, login, logout, demo sessions, password hashing, JWT creation, cookie policy, and current-user resolution. Its interface returns an active `User`; callers never decode tokens themselves.

### Product Intelligence

Owns Open Food Facts normalization, cache freshness, stale fallback, deterministic scoring, comparisons, and scan recording. Shared product facts are cached once; personalized scan events belong to one Identity.

### Personal Nutrition Data

Profile, pantry, favorites, meal plans, and scan history are filtered by `user_id` in every query. Item lookup uses both resource ID and owner ID so another user's identifiers cannot disclose or mutate data.

### Nutrition Insight

The dashboard derives counts, average score, risk distribution, warning frequency, and activity from Personal Nutrition Data. The browser receives aggregates and recent records, not database implementation details.

### Knowledge Corpus

Static Markdown and approved database documents become versioned Knowledge Releases. Ingestion validates metadata, rejects obvious prompt-injection content, creates heading-aware chunks, stores content hashes, persists embeddings, and records pipeline metrics. Runtime retrieval uses the published release with BM25 lexical scoring, embedding cosine scoring, reciprocal-rank fusion, citation lineage, relevance thresholds, and abstention.

All state changes pass through `KnowledgeReleaseControl`; activation is internal and always follows a persisted Evaluation Run gate. Retrieval executes a versioned Retrieval Experiment whose trace captures adapters, embedding model, rank-fusion parameters, candidate count, and release lineage.

### RAG Evaluation

Evaluation cases are JSONL datasets that exercise the same runtime path as chat. The evaluator records route accuracy, abstain accuracy, source recall, mean reciprocal rank, required fact coverage, and retrieval latency against the active Knowledge Release.

### Data Operations

Admin and CLI operations expose ingest, publish, rollback, quality reports, pipeline runs, release inventory, and evaluation history. The data operations interface is deliberately operational: it shows evidence, status, and metrics rather than hiding the platform behind a demo-only workflow.

### Private Answer Audit

Chat requests create operational telemetry with user ID when available, SHA-256 question hash, route, abstention, citation count, and latency. Raw question text is deliberately excluded.

## Persistence

SQLAlchemy async models support SQLite for local development and PostgreSQL through `asyncpg` for production. `Base.metadata.create_all` bootstraps local environments; ordered SQL files in `infra/migrations` define the production schema.

RAG releases are immutable snapshots. Chunks retain source lineage, heading paths, content hashes, metadata, embedding model, and vector values. `DataPipelineRun` and `RagEvaluationRun` make ingestion and quality checks queryable.

## Request lifecycle

1. Middleware assigns or propagates a request ID and starts latency measurement.
2. Rate limiting classifies sensitive routes.
3. CORS and authentication resolve the caller.
4. Route handlers call domain modules and owner-scoped persistence.
5. Security, request ID, and timing headers are attached to every response, including rate-limit responses.

## Failure strategy

- Invalid user input returns `422`.
- Missing owned resources return `404` without revealing another owner's data.
- Missing authentication returns `401`.
- Open Food Facts absence returns `404`; upstream failure returns stale cache or `502`.
- Knowledge retrieval abstains when evidence is weak.
