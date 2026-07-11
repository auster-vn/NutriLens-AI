# RAG Evaluation

RAG quality is measured with executable JSONL datasets under `tests/evaluation/`. The evaluator exercises the same runtime path as chat, then stores the metrics and per-case evidence.

## Dataset Shape

```json
{
  "id": "protein-basics",
  "question": "Protein tren nhan dinh duong co y nghia gi?",
  "expected_route": "rag",
  "expected_sources": ["protein_basics.md"],
  "required_facts": ["protein", "muscle"],
  "should_abstain": false
}
```

Mixed product/RAG cases can include a `barcode`. If omitted, the evaluator supplies a placeholder barcode so route classification stays realistic.

## Metrics

- `route_accuracy`: route classifier correctness.
- `abstain_accuracy`: whether weak or unsafe questions abstain.
- `source_recall_at_3`: expected sources present in citations.
- `mean_reciprocal_rank`: first expected source ranking quality.
- `required_fact_coverage`: required facts found in generated answer text.
- `retrieval_latency_*_ms`: runtime latency distribution.

Metrics average only cases where the field applies. For example, source recall excludes cases without expected sources.

## Run

```bash
npm run data:ingest
npm run data:evaluate
```

Evaluation writes `rag_evaluation_runs` with the release ID, dataset hash, aggregate metrics, and per-case sources/routes/latency. Candidate drafts are evaluated before publish. The release gate requires perfect routing and abstention, minimum retrieval/fact metrics, and bounded p95 latency; its full decision is persisted in release metrics. Evaluation comparison reports per-metric deltas and regressions against a baseline run.

Each case belongs to an explicit or inferred slice. Evaluation Runs persist per-slice quality, Wilson confidence intervals, Retrieval Experiment traces, and trend deltas against the previous run with the same dataset hash.
