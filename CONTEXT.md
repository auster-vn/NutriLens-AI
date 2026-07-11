# NutriLens Domain Context

## Identity

A registered NutriLens account. Identity owns authentication, role, and session lifecycle. Passwords are stored only as Argon2 hashes; browser sessions use signed, expiring JWT cookies.

## Personal Nutrition Data

User-owned profile preferences, scan history, pantry items, meal plans, and favorites. Every read and mutation must be scoped by Identity.

## Product Intelligence

Normalized Open Food Facts data plus deterministic scoring, comparison, cache freshness, and personalized warnings. Product facts are shared; scan history is Personal Nutrition Data.

## Knowledge Corpus

Approved static guidance and approved admin documents used for ranked retrieval, citations, and abstention. The corpus never treats product facts as nutrition guidance.

## Knowledge Chunk

An immutable, retrieval-sized snapshot derived from one approved document during a Data Pipeline Run. It carries source lineage, content hash, lexical statistics, and an embedding vector.

## Knowledge Release

A versioned manifest of Knowledge Chunks. Only one release is published at a time; prior releases remain immutable so retrieval can be audited or rolled back.

## Data Pipeline Run

One observable ingestion execution with input, output, rejection, timing, configuration, and error metrics. A successful run may create a draft Knowledge Release.

## Evaluation Run

A reproducible benchmark execution against a named dataset and Knowledge Release. It records aggregate retrieval/route/abstention metrics plus per-case evidence.

## Retrieval Experiment

An immutable retrieval specification and execution trace tied to a Knowledge Release. It records the candidate adapter, embedding model, rank-fusion configuration, candidate count, and ranked evidence.

## Data Artifact

An immutable exported snapshot of Knowledge Release lineage, Knowledge Chunks, or Evaluation Runs. Artifacts use bronze, silver, and gold paths so storage can move from local files to object storage without changing producers.

## Nutrition Insight

An aggregate derived from Personal Nutrition Data, such as average scan score, risk distribution, expiring pantry count, or recurring warnings.

## Private Answer Audit

Privacy-safe chat telemetry. It stores a one-way question hash and answer metrics, never the raw question.
