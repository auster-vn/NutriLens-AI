# NutriLens AI

NutriLens is an end-to-end nutrition intelligence platform. It turns public food-label data into personalized product scores, pantry workflows, meal plans, cited nutrition answers, and longitudinal user insights.

The project is built as a production-minded portfolio system rather than a UI-only demo: it has real identity, user-level data isolation, deterministic domain logic, external data resilience, privacy-safe RAG telemetry, browser E2E coverage, containers, and CI.

## Product workflow

```text
Register or enter demo
  -> scan a barcode
  -> normalize and cache Open Food Facts data
  -> score against the user's nutrition profile
  -> save history, pantry items, or favorites
  -> aggregate dashboard insights
  -> ask cited questions against the approved knowledge corpus
```

## Highlights

- HttpOnly JWT sessions with Argon2 password hashing and role-aware admin access.
- Strict ownership of profiles, scan history, pantry items, favorites, and meal plans.
- Resilient Open Food Facts adapter with TTL cache and stale fallback during upstream outages.
- Deterministic scoring for sugar, sodium, saturated fat, protein, fiber, calories, allergies, diets, additives, and Nutri-Score.
- Knowledge corpus combining curated Markdown and approved admin documents, with immutable releases, chunk lineage, hybrid BM25/vector retrieval, reciprocal-rank fusion, citations, relevance thresholds, and abstention.
- Data platform operations for RAG ingestion, publish/rollback, quality reporting, evaluation datasets, and retrieval score debugging.
- Private answer audit storing only a one-way question hash and operational metrics.
- Personal dashboard with aggregate metrics, risk distribution, warning patterns, and recent activity.
- Responsive Next.js workspace, camera barcode scanning, comparisons, charts, pantry expiry states, favorites, meal planning, and admin document management.
- FastAPI readiness checks, request IDs, latency headers, rate limits, CORS and security headers.
- PostgreSQL production compose, SQLite local mode, reproducible dependency pins, GitHub Actions, and Playwright Chromium tests.

## Architecture

```text
Next.js 16 workspace
  |  credentialed JSON requests
  v
FastAPI application
  |- Identity and session lifecycle
  |- Product intelligence and Open Food Facts adapter
  |- Personal nutrition data
  |- Nutrition insight aggregation
  |- Knowledge corpus and private answer audit
  `- Admin knowledge operations
  |
  +-> SQLite (local/tests)
  `-> PostgreSQL (compose/production)
```

Domain language lives in [`CONTEXT.md`](CONTEXT.md). Deeper implementation decisions are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DATA_PLATFORM.md`](docs/DATA_PLATFORM.md), [`docs/RAG_RUNBOOK.md`](docs/RAG_RUNBOOK.md), [`docs/RAG_EVALUATION.md`](docs/RAG_EVALUATION.md), and [`docs/SECURITY.md`](docs/SECURITY.md).

## Run locally

Requirements: Python 3.13+, Node.js 22+, npm.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
npm ci
npm run dev:api
```

In a second terminal:

```bash
npm run dev:web
```

Open `http://localhost:3000`. Use **Open portfolio demo** for a zero-setup account, or register a new account. The backend is available at `http://localhost:8000`; OpenAPI documentation is at `http://localhost:8000/docs`.

## Run the production stack

```bash
docker compose up --build
```

This starts PostgreSQL, the FastAPI image, and the production Next.js image with health-based startup ordering. Values in `docker-compose.yml` are local-only; deployment secrets must be supplied through the target platform.

## Quality gates

```bash
npm run data:ingest
npm run data:evaluate
npm run data:quality
npm run data:pipeline
npm run data:analytics
npm run validate
npm run test:e2e
docker compose config
```

Current coverage includes deterministic scoring, diet constraints, cache fallback, RAG release lineage, hybrid retrieval, evaluation metrics, cookie authentication, cross-user data isolation, dashboard aggregation, and a browser-level portfolio workflow.

The RAG/Data path also includes a non-bypassable Knowledge Release control plane, reproducible Retrieval Experiment traces, content-addressed embedding reuse, sliced evaluation governance, a semantic metric catalog, and immutable lakehouse-ready artifact export.

## Repository map

```text
apps/api        FastAPI domain modules, persistence, auth, data platform, and RAG
apps/web        Next.js workspace and Playwright browser tests
infra           PostgreSQL and pgvector schema migrations
analytics       dbt-ready product, RAG, and pipeline marts
tests           Backend integration and RAG evaluation suites
docs            Architecture, security, operations, and portfolio walkthrough
.github          CI pipeline
```

## Safety and limitations

NutriLens provides general nutrition and product-label assistance. It does not diagnose conditions or replace qualified medical advice. Product facts depend on Open Food Facts completeness; every score exposes missing data and every knowledge answer must cite approved evidence or abstain.
