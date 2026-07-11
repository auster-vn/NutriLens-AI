# Portfolio Walkthrough

## Five-minute product tour

1. Open the demo workspace and show the authenticated dashboard.
2. Open Profile and select a nutrition goal or allergy.
3. Scan or enter a barcode; explain cache freshness and personalized deterministic scoring.
4. Save the product to favorites and pantry, then show ownership and expiry status.
5. Compare two products and inspect raw nutrition dimensions beside the recommendation.
6. Ask a nutrition question and inspect citations and abstention behavior.
7. Open Admin Data Ops, run RAG ingest, publish a release, and inspect release metrics.
8. Run evaluation and explain route accuracy, source recall, fact coverage, and latency.
9. Upload an approved document in Admin, publish a new release, then ask a question grounded in that document.

## Engineering discussion points

- Why product facts are shared while user actions are isolated.
- Why stale cache is safer than failing every scan during an upstream outage.
- Why nutrition scoring is deterministic before introducing an LLM.
- Why Knowledge Corpus has two real adapters: Markdown and database documents.
- Why RAG embeddings have two adapters: deterministic feature hashing for reproducible tests and optional sentence-transformers for neural experiments.
- Why Knowledge Releases are immutable snapshots with chunk lineage.
- How reciprocal-rank fusion combines lexical and vector evidence.
- How evaluation datasets turn RAG quality into comparable metrics.
- How Data Ops exposes pipeline runs, rollback, and quality reporting.
- Why answer audit stores a hash instead of raw user text.
- How integration tests prove cross-user isolation.
- How Playwright proves the browser, cookie, backend, database, Data Ops, and RAG work together.

## Commands to demonstrate quality

```bash
npm run data:ingest
npm run data:evaluate
npm run data:quality
npm run validate
npm run test:e2e
docker compose config
```
