# RAG Runbook

NutriLens treats nutrition knowledge as versioned data, not loose prompt context. Curated Markdown and approved admin documents are validated, chunked, embedded, released, evaluated, and rolled back through one pipeline.

## Retrieval Path

```text
Question
  -> route classifier
  -> active Knowledge Release
  -> BM25 lexical score
  -> embedding cosine score
  -> reciprocal-rank fusion
  -> citation assembly
  -> abstention when evidence is weak
```

The default embedding adapter is deterministic feature hashing so local tests and demos are reproducible. Production experiments can switch to a neural adapter:

```bash
pip install -r apps/api/requirements-ml.txt
export NUTRILENS_RAG_EMBEDDING_PROVIDER=sentence_transformers
export NUTRILENS_RAG_SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Ingest And Publish

```bash
npm run data:ingest
```

This command:

- loads static Markdown plus approved database documents
- validates metadata and prompt-injection risk
- creates heading-aware chunks with content hashes
- writes embeddings and lineage to `rag_chunks`
- creates a draft `rag_releases` row
- publishes the release and retires the previous published release
- records a `data_pipeline_runs` row

To create a draft without publishing:

```bash
PYTHONPATH=apps/api python -m app.data.cli ingest-rag --version portfolio-candidate-001
```

## Inspect Retrieval

```bash
npm run data:search -- "Toi di ung sua thi can canh giac gi?"
```

The output includes source, fused score, lexical score, semantic score, and heading lineage. Use this before editing chunk sizes or relevance thresholds.

## Evaluate

```bash
npm run data:evaluate
```

The evaluator reads JSONL cases from `tests/evaluation/`, runs real retrieval and answer assembly, then stores a `rag_evaluation_runs` row with:

- route accuracy
- abstain accuracy
- source recall at 3
- mean reciprocal rank
- required fact coverage
- retrieval latency mean, p50, and p95

## Rollback

```bash
PYTHONPATH=apps/api python -m app.data.cli list-releases
curl -X POST http://localhost:8000/api/admin/rag/rollback -H "X-Admin-Key: dev-admin-key"
```

Rollback retires the current release and republishes the most recent retired release. Chunks are immutable snapshots, so deleting an admin document does not break already-published citation lineage.

## Admin Workflow

1. Upload or approve a Knowledge Document in Admin.
2. Run ingest from the Data Ops tab.
3. Publish the draft release.
4. Run evaluation.
5. Inspect data quality, release metrics, pipeline runs, and evaluation evidence.
