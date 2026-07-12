<div align="center">

<img src="apps/web/public/icon.svg" alt="NutriLens AI" width="88" height="88">

# NutriLens AI

**An end-to-end nutrition intelligence platform with barcode product analysis, grounded RAG, personalized meal planning, and production-grade data operations.**

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![Open Food Facts](https://img.shields.io/badge/Data-Open_Food_Facts-67B246?style=flat-square)](https://world.openfoodfacts.org/)

[**Live App**](https://nutrilens-rag.netlify.app) · [**API**](https://nutrilens-ai-zc6y.onrender.com) · [**Quick Start**](#quick-start) · [**Architecture**](#system-architecture) · [**Data Platform**](docs/DATA_PLATFORM.md)

</div>

---

## What is NutriLens?

Food labels contain useful information, but interpreting sugar, sodium, allergens, additives, serving sizes, and marketing claims is difficult in the moment of purchase.

NutriLens turns a barcode into a complete decision workflow:

```text
Scan a product
  -> normalize and cache public label data
  -> score it against the user's goals and allergies
  -> compare, save, or add it to the pantry
  -> generate a personalized meal and shopping plan
  -> ask nutrition questions with citations
```

This repository is designed as an **AI/Data Engineering portfolio project**, not a UI-only prototype. It includes immutable knowledge releases, hybrid retrieval, an evaluation gate, pgvector, pipeline lineage, observability, analytics marts, privacy-safe telemetry, and browser-level end-to-end testing.

## Product Capabilities

| Capability | What it does |
|---|---|
| **Barcode and label intelligence** | Scans retail/GS1 codes, falls back to document OCR for unknown products, and requires human confirmation before publishing extracted label data. |
| **Personalized scoring** | Evaluates sugar, sodium, saturated fat, protein, fiber, calories, allergens, diets, additives, and Nutri-Score with deterministic rules. |
| **Product comparison** | Compares two products by normalized nutrition dimensions and explains the recommendation. |
| **Grounded nutrition assistant** | Answers everyday food and label questions in Vietnamese with approved evidence, citations, and abstention when evidence is weak. |
| **Meal planning** | Builds varied multi-day plans from goals, diet, allergies, pantry inventory, budget, and calorie targets. |
| **TDEE guidance** | Estimates BMR/TDEE from body and activity inputs, applies deficit guardrails, and feeds the calorie target into meal planning. |
| **Pantry and favorites** | Tracks owned products, quantities, storage locations, expiry dates, and saved items per user. |
| **Personal dashboard** | Aggregates scan activity, average score, risk distribution, common warnings, and recent decisions. |
| **Mobile PWA** | Provides camera-first scanning, safe-area support, bottom navigation, touch-friendly controls, and installable shortcuts. |
| **Admin Control Plane** | Operates documents, releases, evaluation, rollback, data quality, pipelines, observability, and analytics separately from the user workspace. |

## AI and Data Engineering Highlights

### Hybrid RAG with release governance

```text
Curated Markdown + Approved Admin Documents
                    |
                    v
Metadata validation -> heading-aware chunking -> content hashing
                    |
                    v
Embedding reuse -> PostgreSQL FTS + pgvector candidates
                    |
                    v
BM25 + vector similarity -> Reciprocal Rank Fusion
                    |
                    v
Evidence threshold -> cited answer or explicit abstention
```

- Static and database-backed documents share one source contract.
- Every chunk retains document, heading, hash, embedding model, and release lineage.
- PostgreSQL uses full-text search and pgvector; SQLite provides a reproducible local adapter.
- Title and heading fields are boosted for stronger domain retrieval.
- Vietnamese aliases preserve short, meaningful terms such as `cá` and `xơ`.
- Feature-hash embeddings make local tests deterministic; sentence-transformers are available as an optional neural adapter.
- Raw user questions are not persisted in telemetry; audits store a SHA-256 hash and operational metrics.

### Non-bypassable evaluation gate

A draft Knowledge Release cannot become active until it passes the persisted evaluation gate. The benchmark covers nutrition concepts, product-grounded questions, everyday foods, mixed routes, and abstention cases.

| Metric | Default gate |
|---|---:|
| Route accuracy | `1.00` |
| Abstention accuracy | `1.00` |
| Source recall | `>= 0.80` |
| Mean reciprocal rank | `>= 0.70` |
| Required fact coverage | `>= 0.90` |
| Retrieval latency p95 | `<= 250 ms` |

Evaluation runs persist per-case results, slice metrics, Wilson confidence intervals, experiment configuration, latency, and comparisons against previous runs. A failed gate leaves the release in `draft` and marks the orchestration run as `blocked`.

### Data platform and analytics

NutriLens separates two data planes:

- **Product Data:** Open Food Facts ingestion, normalization, cache freshness, stale fallback, completeness, and personalized scoring inputs.
- **Knowledge Data:** evidence documents, immutable releases, chunks, embeddings, evaluation runs, and answer telemetry.

The platform includes:

- content-addressed embedding reuse with `content_hash + embedding_model`;
- ingest, evaluate, publish, rollback, export, and quality-report workflows;
- pipeline stage lineage and persisted failures;
- optional Prefect orchestration over framework-neutral core logic;
- Prometheus-compatible metrics at `/metrics`;
- runtime analytics marts and dbt-ready models in `analytics/`;
- bronze, silver, and gold release artifact export.

### Multimodal package-label extraction

When a GTIN is missing from Open Food Facts, NutriLens runs a provenance-first Document AI workflow:

```text
Package image -> quality gate -> perspective/deskew/CLAHE/adaptive threshold
              -> Tesseract + optional PaddleOCR -> bbox ensemble
              -> layout blocks -> ingredient and nutrition parsers
              -> field confidence + semantic validation -> human confirmation
```

- Word-level text, confidence, bounding boxes, provider, line, and block IDs are persisted with the extraction.
- Preprocessing metadata records blur, brightness, contrast, glare, skew, transformations, and quality score.
- Ingredient parsing supports nested groups, percentages, bilingual ontology matching, additives, and fuzzy OCR correction.
- Nutrition parsing associates values and units by row coordinates, normalizes `mg/g` and `kJ/kcal`, and validates macros.
- Confirmed user corrections become labeled evaluation examples instead of silently replacing model output.
- The admin OCR dashboard separates labeled-hypothesis CER from runtime-image CER and tracks field F1, numeric accuracy, allergen recall, and model readiness.
- LayoutLMv3/NER training remains gated until labeled-data and structured-field quality thresholds are met.

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  Next.js 16 PWA · TypeScript · Camera Scanner · Recharts           │
│  User Workspace + Mobile Navigation + Admin Control Plane          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ credentialed HTTP/JSON
                               v
┌─────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                             │
│  FastAPI · Async SQLAlchemy · Pydantic                             │
│                                                                     │
│  Identity        Product Intelligence       Personal Nutrition      │
│  JWT sessions    Open Food Facts adapter    Profile / TDEE          │
│  Argon2           Cache + stale fallback     Pantry / Meal Plans     │
│                                                                     │
│  RAG Runtime      Data Operations            Observability          │
│  Hybrid search    Release / Gate / Rollback  Metrics / Audit         │
└───────────────┬─────────────────────────┬───────────────────────────┘
                │                         │
                v                         v
┌────────────────────────────┐  ┌─────────────────────────────────────┐
│ PRODUCT DATA               │  │ KNOWLEDGE DATA                      │
│ Users · Product Cache      │  │ Documents · Releases · Chunks      │
│ Scans · Pantry · Favorites │  │ Embeddings · Evaluations · Runs    │
│ Meal Plans · Profiles      │  │ Answer Audit · Admin Audit         │
└───────────────┬────────────┘  └──────────────────┬──────────────────┘
                └──────────────────┬────────────────┘
                                   v
                   PostgreSQL 17 + pgvector
                   SQLite for local tests
```

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js 16, React, TypeScript | App Router workspace, responsive PWA, product and admin workflows |
| Visualization | Recharts | Nutrition, score, and dashboard charts |
| Barcode scanning | `@zxing/browser` | Camera-based barcode detection |
| API | FastAPI, Pydantic v2 | Async HTTP API, validation, middleware, OpenAPI |
| Persistence | SQLAlchemy async, asyncpg, aiosqlite | PostgreSQL production and SQLite local/test adapters |
| Authentication | JWT, HttpOnly cookies, Argon2 | Session lifecycle and password security |
| Retrieval | BM25, PostgreSQL FTS, pgvector, RRF | Hybrid candidate retrieval and ranking |
| Embeddings | Feature hashing, optional sentence-transformers | Reproducible local and neural retrieval experiments |
| Orchestration | Native pipeline core, optional Prefect | Ingest, evaluate, publish, and rollback workflows |
| Analytics | SQL marts, dbt project | Daily RAG and pipeline reporting |
| Observability | Prometheus exposition, persisted audits | Latency, answer quality, pipeline health, and traceability |
| Infrastructure | Docker Compose, Netlify, Render, Neon | Local stack and free-tier deployment |

## Quick Start

### Requirements

- Python 3.13+
- Node.js 22+
- npm
- Docker and Docker Compose v2 for the PostgreSQL stack

### Local development

```bash
git clone https://github.com/auster-vn/NutriLens-AI.git
cd NutriLens-AI

python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
npm ci
```

Create `.env` in the repository root:

```env
NUTRILENS_ENVIRONMENT=development
NUTRILENS_DATABASE_URL=sqlite+aiosqlite:///./nutrilens.db
NUTRILENS_OPEN_FOOD_FACTS_BASE_URL=https://world.openfoodfacts.org
NUTRILENS_JWT_SECRET=dev-only-change-this-secret-before-production
NUTRILENS_ADMIN_KEY=dev-admin-key
NUTRILENS_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NUTRILENS_RAG_EMBEDDING_PROVIDER=feature_hash
NUTRILENS_RAG_EMBEDDING_DIMENSIONS=256
NUTRILENS_RAG_RETRIEVAL_BACKEND=auto
NUTRILENS_LABEL_OCR_PROVIDERS=tesseract,paddleocr
NUTRILENS_LABEL_OCR_QUALITY_THRESHOLD=0.4
NUTRILENS_LABEL_OCR_BENCHMARK_MIN_CASES_FOR_LAYOUTLM=200
NUTRILENS_LABEL_OCR_BENCHMARK_MIN_FIELD_F1=0.85
```

Start the API:

```bash
npm run dev:api
```

Start the frontend in another terminal:

```bash
npm run dev:web
```

| Service | URL |
|---|---|
| Web application | http://localhost:3000 |
| FastAPI | http://localhost:8000 |
| OpenAPI documentation | http://localhost:8000/docs |
| Readiness | http://localhost:8000/health/ready |
| Prometheus metrics | http://localhost:8000/metrics |

Use the portfolio demo account from the application or register a local user.

### Full PostgreSQL stack

```bash
docker compose up --build
```

Docker Compose starts PostgreSQL with pgvector, FastAPI, and the production Next.js application with health-based startup ordering.

## RAG and Data Operations

Build and publish a Knowledge Release:

```bash
npm run data:ingest
```

Run the full release pipeline and supporting reports:

```bash
npm run data:pipeline
npm run data:evaluate
npm run data:quality
npm run data:analytics
```

Inspect retrieval for a question:

```bash
npm run data:search -- "Ăn trứng có tốt không?"
```

Export immutable release artifacts:

```bash
npm run data:export -- <release-id> --output artifacts
```

The same operations are available from the separate `/admin` Control Plane using `NUTRILENS_ADMIN_KEY`.

## Testing and Quality Gates

```bash
# Python lint and complete backend test suite
npm run lint:api
npm run test:api

# Frontend lint and production build
npm run lint:web
npm run build:web

# Combined validation
npm run validate

# Chromium browser workflow and mobile navigation tests
npm run test:e2e

# Infrastructure validation
docker compose config --quiet
```

Coverage includes authentication, cross-user isolation, product cache fallback, deterministic scoring, dietary constraints, TDEE guardrails, meal-plan diversity, RAG retrieval, evaluation metrics, release lineage, rollback, orchestration, analytics, and mobile browser navigation.

## Repository Structure

```text
NutriLens-AI/
├── apps/
│   ├── api/
│   │   ├── app/                 # FastAPI domains and platform services
│   │   │   ├── auth/            # Identity and session lifecycle
│   │   │   ├── products/        # Open Food Facts, cache, scoring, comparison
│   │   │   ├── profile/         # User preferences and TDEE calculation
│   │   │   ├── meal/            # Personalized meal-plan engine
│   │   │   ├── rag/             # Retrieval, evaluation, releases, experiments
│   │   │   ├── data/            # Orchestration, quality, artifact export
│   │   │   └── admin/           # Knowledge and Data Ops API
│   │   └── data/                # Curated nutrition knowledge corpus
│   └── web/
│       ├── app/                  # Next.js routes
│       ├── components/           # Product, chat, planning, admin, mobile UI
│       └── e2e/                  # Playwright desktop and mobile tests
├── analytics/                    # dbt-ready sources and marts
├── infra/migrations/             # PostgreSQL and pgvector migrations
├── tests/evaluation/             # Versioned RAG benchmark datasets
├── tests/                        # Backend unit and integration tests
├── docs/                         # Architecture, security, RAG, deployment
├── docker-compose.yml
└── Dockerfile                    # Render-compatible API image
```

## Deployment

The public deployment uses a free-tier split:

| Component | Platform |
|---|---|
| Next.js PWA | Netlify |
| FastAPI container | Render |
| PostgreSQL + pgvector | Neon |

Deployment configuration is stored in `netlify.toml` and the root `Dockerfile`. Production requires strong `NUTRILENS_JWT_SECRET` and `NUTRILENS_ADMIN_KEY` values, an HTTPS-only auth cookie, the Neon database URL, and a restricted Netlify CORS origin.

After deploying new knowledge documents, open `/admin` and run the release pipeline. The runtime intentionally continues using the previous published release until the candidate passes evaluation.

See [Deployment](docs/DEPLOYMENT.md), [RAG Runbook](docs/RAG_RUNBOOK.md), and [Security](docs/SECURITY.md) for operational details.

## Design Decisions

- **Deterministic scoring before generative AI:** product recommendations remain inspectable and reproducible.
- **Shared facts, private decisions:** product cache records are reusable; scans, profiles, pantry items, favorites, and meal plans are owner-scoped.
- **Stale cache over avoidable outage:** cached product data remains available when Open Food Facts is temporarily unavailable.
- **Citations or abstention:** weak evidence never becomes a confident nutrition answer.
- **Immutable releases:** every production answer can be traced back to a specific corpus and experiment configuration.
- **Hashed answer telemetry:** observability does not require retaining raw nutrition questions.
- **Adapter-based infrastructure:** SQLite/PostgreSQL and local/pgvector retrieval share stable domain contracts.

## Safety and Limitations

NutriLens provides general nutrition information and product-label assistance. It does not diagnose, treat, or replace advice from a qualified medical professional.

- Product accuracy depends on Open Food Facts completeness and community-contributed labels.
- Nutrition scores are deterministic guidance, not clinical recommendations.
- BMR, TDEE, calorie deficit, and meal-plan nutrition values are estimates and require real-world adjustment.
- Users with medical conditions, pregnancy, eating-disorder history, or specialized dietary needs should consult a qualified professional.
- The assistant abstains when the approved corpus does not provide sufficient evidence.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data Platform](docs/DATA_PLATFORM.md)
- [RAG Evaluation](docs/RAG_EVALUATION.md)
- [RAG Security](docs/RAG_SECURITY.md)
- [RAG Runbook](docs/RAG_RUNBOOK.md)
- [Product Data](docs/PRODUCT_DATA.md)
- [Portfolio Walkthrough](docs/PORTFOLIO_WALKTHROUGH.md)
- [Security](docs/SECURITY.md)

---

<div align="center">

Built as an AI/Data Engineering portfolio project focused on grounded intelligence, reproducible evaluation, and production-minded data systems.

</div>
