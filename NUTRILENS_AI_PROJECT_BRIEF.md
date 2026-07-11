# NutriLens AI — Project Brief for Codex

## 1. Project concept

NutriLens AI is a practical AI-assisted nutrition and smart shopping platform.

Users scan a food product barcode, view nutrition information, receive personalized warnings, compare products, manage a pantry, generate simple meal/shopping plans, and ask a grounded nutrition assistant questions. The assistant uses RAG over curated nutrition documents and product data from Open Food Facts.

This project is intentionally different from a weather/GIS project, but it reuses strong engineering ideas:

- grounded RAG with citations;
- admin knowledge management;
- privacy-safe audit logs;
- product/tool data separated from explanatory knowledge;
- free-tier deployability;
- clear evaluation and security gates.

## 2. Primary user problems

Users often cannot quickly answer:

- Is this product high in sugar, sodium, saturated fat, or additives?
- Is this product safe for my allergies or dietary preference?
- Which of two products is healthier for my goal?
- What should I buy within a small budget?
- What meals can I make from products I already have?
- Can I trust the “healthy” marketing claim on a label?

NutriLens AI helps users make better food choices using barcode data, nutrition rules, and cited explanations.

## 3. Target users

- General consumers
- Students living on a budget
- People trying to reduce sugar/sodium
- People tracking protein/calories
- Vegetarians/vegans
- People with allergies
- Families managing pantry and expiry dates

Important: the app must not diagnose medical conditions or replace a doctor.

## 4. Core value proposition

```text
Scan food → understand nutrition → get personalized guidance → compare alternatives → plan smarter shopping.
```

## 5. Data source

Use Open Food Facts as the primary public product data source.

Official API docs:

```text
https://openfoodfacts.github.io/openfoodfacts-server/api/
```

Open Food Facts can provide:

- product name;
- brand;
- barcode;
- categories;
- ingredients;
- allergens;
- additives;
- nutrition facts;
- Nutri-Score if available;
- product image.

Cache product responses locally in the database to reduce API calls and improve performance.

## 6. Recommended tech stack

### Frontend

- Next.js 16 App Router
- TypeScript
- PWA support
- Camera barcode scanner:
  - Browser `BarcodeDetector` when available;
  - fallback: `@zxing/browser` or similar.
- Recharts or ECharts for nutrition dashboards
- CSS modules, Tailwind, or inline design system

### Backend

- FastAPI
- Python 3.12+ or 3.13+
- SQLAlchemy async
- Pydantic v2
- HTTPX for external APIs
- Redis/Upstash for cache/rate limiting if needed

### Database

- Supabase Postgres
- pgvector for RAG embeddings
- PostgreSQL full-text search for lexical retrieval
- Supabase Auth if user accounts are included
- Row Level Security for user-specific data

### AI/RAG

- Local-first RAG:
  - markdown corpus;
  - metadata validation;
  - chunking;
  - PostgreSQL FTS;
  - pgvector;
  - reciprocal rank fusion;
  - cited answers;
  - abstain if evidence is insufficient.
- Optional LLM:
  - Vercel AI SDK or backend LLM provider;
  - only for chat/meal-plan enhancement;
  - must have budget/rate limits.

## 7. High-level architecture

```text
User Web/PWA
  ├── Barcode Scanner
  ├── Product Detail
  ├── Nutrition Score
  ├── Product Compare
  ├── Pantry Tracker
  ├── Meal Planner
  └── Nutrition Chat Assistant
        │
        ▼
FastAPI Backend
  ├── Product Service
  ├── Open Food Facts Client
  ├── Nutrition Normalizer
  ├── Nutrition Scoring Engine
  ├── Recommendation Engine
  ├── RAG Service
  ├── User Profile Service
  └── Admin Service
        │
        ▼
Supabase/Postgres
  ├── product_cache
  ├── scan_history
  ├── user_profiles
  ├── pantry_items
  ├── meal_plans
  ├── rag_documents
  ├── rag_chunks
  ├── rag_claims
  ├── rag_releases
  ├── rag_answer_audit
  └── admin_operation_audit
```

## 8. Main modules

### 8.1 Barcode scanner

Required behavior:

1. User opens `/scan`.
2. Browser camera starts.
3. App detects barcode.
4. App calls backend:

```text
POST /api/products/scan
```

5. Backend checks local cache.
6. If product is missing, backend calls Open Food Facts.
7. Backend normalizes nutrition data.
8. Backend stores product in `product_cache`.
9. Frontend navigates to `/product/[barcode]`.

### 8.2 Product detail

Show:

- product name;
- brand;
- image;
- barcode;
- categories;
- ingredients;
- allergens;
- additives;
- nutrition table per 100g/ml;
- Nutri-Score if available;
- app-generated nutrition score;
- warnings and good points;
- source badge: Open Food Facts.

### 8.3 Nutrition scoring engine

The scoring engine should be deterministic first, not LLM-based.

Input:

```json
{
  "nutriments": {},
  "allergens": [],
  "additives": [],
  "user_profile": {
    "goal": "low_sugar",
    "allergies": ["peanuts"],
    "diet": "vegetarian"
  }
}
```

Output:

```json
{
  "score": 72,
  "label": "Khá ổn",
  "risk_level": "medium",
  "warnings": [
    "Đường hơi cao",
    "Không phù hợp nếu cần hạn chế đường nghiêm ngặt"
  ],
  "good_points": [
    "Protein khá tốt",
    "Chất béo bão hòa thấp"
  ],
  "missing_data": [
    "fiber_100g"
  ]
}
```

Suggested rule dimensions:

- sugar per 100g;
- sodium/salt per 100g;
- saturated fat per 100g;
- protein per 100g;
- fiber per 100g;
- calories per 100g;
- allergens;
- additives count;
- Nutri-Score if available.

Do not present the score as medical advice.

### 8.4 Product comparison

Route:

```text
/compare
```

Backend:

```text
POST /api/products/compare
```

Compare:

- sugar;
- calories;
- protein;
- sodium/salt;
- saturated fat;
- fiber;
- allergens;
- additives;
- Nutri-Score;
- final recommendation by selected user goal.

Example output:

```text
If your priority is low sugar, choose Product B.
If your priority is higher protein, Product A is better.
Product A contains milk allergen.
```

### 8.5 User profile

Route:

```text
/profile
```

Fields:

- age group, optional;
- goal:
  - general;
  - low sugar;
  - low sodium;
  - high protein;
  - weight loss;
  - vegetarian;
  - vegan;
  - gluten-free;
  - lactose-free;
- allergies:
  - peanuts;
  - milk;
  - soy;
  - gluten;
  - eggs;
  - shellfish;
  - tree nuts;
- disliked ingredients;
- daily budget, optional.

Privacy:

- Do not store sensitive disease descriptions unless necessary.
- If stored, protect with RLS.
- Do not log raw profile data.

### 8.6 Pantry tracker

Route:

```text
/pantry
```

Features:

- add scanned product to pantry;
- set quantity;
- set expiry date;
- location: fridge/freezer/pantry;
- reminder for near-expiry items;
- suggest meals from pantry items.

Schema:

```sql
pantry_items (
  id uuid primary key,
  user_id uuid not null,
  barcode text not null,
  quantity numeric,
  unit text,
  expiry_date date,
  storage_location text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### 8.7 Meal planner

Route:

```text
/meal-planner
```

MVP should be rule-based:

Input:

- days;
- budget;
- goal;
- excluded ingredients;
- available pantry items.

Output:

- meal list;
- shopping list;
- estimated nutrition;
- warnings about missing data.

Optional LLM can later make the plan more natural, but deterministic rules should work first.

### 8.8 RAG nutrition assistant

Route:

```text
/chat
```

Example questions:

- “Nutri-Score B nghĩa là gì?”
- “Sodium cao có sao không?”
- “Sản phẩm này có phù hợp cho người hạn chế đường không?”
- “Chất béo bão hòa là gì?”
- “Phụ gia E330 là gì?”
- “Trẻ em có nên uống nước ngọt mỗi ngày không?”

Rules:

- Product facts come from product cache/Open Food Facts.
- Nutrition explanation comes from RAG.
- If product data is missing, say clearly.
- If evidence is insufficient, abstain.
- Do not diagnose.
- Always cite knowledge sources for health-related explanations.

## 9. RAG corpus plan

Create markdown documents under:

```text
apps/api/data/nutrition_knowledge/
```

Suggested documents:

```text
nutrition_label_reading.md
sugar_guidance.md
sodium_and_blood_pressure.md
saturated_fat.md
protein_basics.md
fiber_and_whole_grains.md
food_allergens.md
food_additives.md
nutriscore_explained.md
children_nutrition_basics.md
vegetarian_vegan_nutrition.md
diabetes_aware_eating.md
hypertension_friendly_eating.md
food_safety_storage.md
```

Each document should have metadata:

```json
{
  "authority": "WHO / FDA / EFSA / Open Food Facts / editorial synthesis",
  "source_url": "https://...",
  "jurisdiction": "global",
  "risk_level": "health",
  "effective_from": "2026-01-01",
  "expires_at": "2027-01-01",
  "reviewed_at": "2026-07-10",
  "evidence_level": "primary",
  "domains": ["nutrition", "health"],
  "status": "approved"
}
```

RAG pipeline:

```text
question
  → normalize text
  → classify route: product / rag / mixed
  → FTS retrieval
  → vector retrieval
  → reciprocal rank fusion
  → citation assembly
  → grounded answer
  → audit
```

## 10. Admin module

Routes:

```text
/admin/login
/admin
/admin/documents
/admin/evaluation
/admin/audit
```

Admin features:

- login with admin key or Supabase Auth role;
- upload/edit/delete nutrition documents;
- validate metadata;
- scan prompt injection;
- preview chunks;
- run retrieval test;
- publish RAG release;
- rollback release;
- view audit logs;
- view failed/low-confidence queries.

Security:

- Admin key should not be stored in localStorage.
- Prefer httpOnly cookie session or sessionStorage for simple demo.
- Backend must enforce auth.
- Frontend hiding is not security.
- Add rate limiting.
- Add audit logs.

## 11. API design

Public/user:

```text
GET  /health
GET  /version

POST /api/products/scan
GET  /api/products/{barcode}
POST /api/products/score
POST /api/products/compare

GET  /api/profile
PUT  /api/profile

GET  /api/pantry
POST /api/pantry
PUT  /api/pantry/{id}
DELETE /api/pantry/{id}

POST /api/meal-plan/generate
GET  /api/meal-plan/{id}

POST /api/chat/stream
POST /api/rag/search
```

Admin:

```text
GET  /api/admin/session
POST /api/admin/documents
GET  /api/admin/documents
GET  /api/admin/documents/{id}
DELETE /api/admin/documents/{id}
POST /api/admin/rag/publish
POST /api/admin/rag/rollback
GET  /api/admin/audit
GET  /api/admin/capacity
POST /api/admin/evaluate
```

## 12. Database schema draft

```sql
create table product_cache (
  barcode text primary key,
  name text,
  brand text,
  categories text[],
  ingredients_text text,
  allergens text[],
  additives text[],
  nutriments jsonb not null default '{}'::jsonb,
  nutriscore text,
  ecoscore text,
  image_url text,
  source text not null default 'open_food_facts',
  raw_payload jsonb,
  updated_at timestamptz not null default now()
);

create table scan_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  barcode text not null references product_cache(barcode),
  score integer,
  warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table user_profiles (
  user_id uuid primary key,
  goal text not null default 'general',
  allergies text[] not null default '{}',
  diet text,
  disliked_ingredients text[] not null default '{}',
  budget_daily numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table pantry_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  barcode text not null references product_cache(barcode),
  quantity numeric,
  unit text,
  expiry_date date,
  storage_location text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table meal_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  days integer not null,
  budget numeric,
  goal text,
  plan jsonb not null,
  created_at timestamptz not null default now()
);
```

RAG tables can mirror:

```text
rag_documents
rag_chunks
rag_claims
rag_releases
rag_answer_audit
admin_operation_audit
```

## 13. Security requirements

Required:

- No raw prompt logging.
- Redact email, phone, API keys.
- Row Level Security for user data.
- Admin endpoints require auth.
- Rate limit chat, scan, admin mutation.
- Validate barcode format.
- Validate external URLs.
- Do not render raw HTML from RAG output.
- Sanitize markdown.
- Prompt injection scan on uploaded documents.
- Audit admin operations without raw content.
- Add disclaimer for health-related advice.

Health disclaimer:

```text
NutriLens AI provides general nutrition information and product-label assistance.
It does not diagnose, treat, or replace advice from a qualified medical professional.
```

## 14. Evaluation plan

Create test files:

```text
tests/evaluation/product_questions.jsonl
tests/evaluation/nutrition_rag_questions.jsonl
tests/evaluation/mixed_product_rag_questions.jsonl
tests/evaluation/security_cases.jsonl
tests/evaluation/abstain_cases.jsonl
```

Metrics:

- route accuracy;
- retrieval recall@5;
- citation coverage;
- required fact coverage;
- unsupported claim rate;
- abstain correctness;
- latency;
- external API cache hit rate.

Example test case:

```json
{
  "id": "sugar_001",
  "question": "Đường cao trong sản phẩm nghĩa là gì?",
  "expected_route": "rag",
  "expected_sources": ["sugar_guidance.md"],
  "required_facts": ["đường", "hạn chế", "nhãn dinh dưỡng"],
  "should_abstain": false
}
```

## 15. Free-tier deployment plan

Recommended:

- Vercel: Next.js frontend
- Render: FastAPI backend
- Supabase: Postgres + Auth + pgvector
- Upstash: Redis
- Cron-job.org: keep-awake and periodic cache cleanup

Free-tier strategy:

- Cache Open Food Facts responses.
- Do not call LLM for every product scan.
- Keep RAG local-first.
- Limit uploaded document size.
- Limit OCR usage.
- Use scheduled cleanup for old scan history if unauthenticated.
- Keep embeddings small.

## 16. MVP roadmap

### Week 1 — Foundation

Deliverables:

- Next.js app
- FastAPI app
- Supabase schema
- Open Food Facts client
- product cache
- basic product page

Tasks:

- initialize repo;
- set env config;
- create database migrations;
- implement `/health`;
- implement `/api/products/{barcode}`;
- normalize Open Food Facts response.

### Week 2 — Scanner and scoring

Deliverables:

- barcode scanner page;
- scan history;
- scoring engine v1;
- product warnings;
- product comparison.

Tasks:

- implement camera scanner;
- implement fallback barcode input;
- implement score rules;
- create warning cards;
- implement compare endpoint and page.

### Week 3 — RAG assistant

Deliverables:

- nutrition corpus;
- ingest pipeline;
- hybrid retrieval;
- chat page;
- citation UI;
- abstain policy.

Tasks:

- create markdown documents;
- implement chunking;
- implement pgvector/FTS search;
- implement route planner;
- implement answer templates;
- add audit.

### Week 4 — Admin and polish

Deliverables:

- admin login;
- document manager;
- audit dashboard;
- meal planner v1;
- PWA polish;
- deploy.

Tasks:

- admin auth;
- document upload/edit/delete;
- evaluation endpoint;
- meal planner rule-based;
- mobile UX;
- production env setup.

## 17. Advanced roadmap

### V1

- Barcode scan
- Product detail
- Nutrition score
- Compare products
- RAG assistant
- Admin document manager

### V2

- Pantry tracker
- Meal planner
- Shopping list
- Expiry reminders

### V3

- OCR nutrition label when barcode data is missing
- User contribution/correction flow
- Product recommendation by similar category

### V4

- AI-enhanced meal planning
- Family profiles
- Receipt scanner
- Store price tracking
- Community verified products

## 18. Demo scenarios

### Demo 1 — Scan a soda

Show:

- barcode scan;
- high sugar warning;
- nutrition score;
- RAG explanation with citation.

### Demo 2 — Compare two yogurts

Show:

- sugar/protein/saturated fat comparison;
- recommendation by goal.

### Demo 3 — Allergy warning

Question:

```text
Tôi dị ứng sữa, sản phẩm này dùng được không?
```

Show:

- product allergen data;
- warning;
- “data missing” behavior if allergen data is unavailable.

### Demo 4 — Meal plan

Input:

```text
3 ngày, ngân sách 300k, ít đường, đủ protein
```

Show:

- shopping list;
- meal suggestions;
- nutrition estimate.

### Demo 5 — Admin adds new sodium guidance

Show:

- admin upload;
- RAG re-index;
- chatbot answer cites new source;
- audit log.

## 19. Acceptance criteria

MVP is done when:

- User can scan or enter a barcode.
- Product data is fetched and cached.
- Product detail page renders nutrition data.
- Nutrition scoring engine returns deterministic warnings.
- User can compare two products.
- RAG answers basic nutrition questions with citations.
- Mixed product + RAG question works.
- Admin can upload nutrition document.
- Admin audit exists.
- Build and deployment work on free-tier.
- Security checklist is documented.

## 20. Important implementation principles

- Product data and RAG knowledge must be separate.
- RAG must not invent product nutrition values.
- Product values come from Open Food Facts/cache.
- RAG explains concepts, thresholds, and guidance.
- If data is missing, say missing.
- Avoid external LLM dependency in MVP.
- Add LLM later as optional enhancement with quota limits.
- Optimize for mobile first.
- Keep UI simple but polished.

## 21. Suggested repo structure

```text
nutrilens-ai/
├── apps/
│   ├── web/
│   └── api/
├── infra/
│   ├── migrations/
│   └── docker/
├── docs/
│   ├── RAG_SECURITY.md
│   ├── RAG_RUNBOOK.md
│   ├── PRODUCT_DATA.md
│   └── DEPLOYMENT.md
├── tests/
│   └── evaluation/
└── README.md
```

## 22. Final product summary

NutriLens AI is:

```text
Barcode scanner
+ product nutrition intelligence
+ personal warnings
+ product comparison
+ pantry tracker
+ meal planner
+ grounded nutrition RAG
+ admin knowledge studio
```

It is practical, useful, demo-friendly, and technically strong without depending on expensive AI calls.
