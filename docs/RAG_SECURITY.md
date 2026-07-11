# RAG Security

- Product values must come from Open Food Facts or cached product records, not generated text.
- Health explanations must cite approved knowledge documents.
- If retrieval returns no relevant document, the assistant abstains.
- Uploaded documents require metadata validation.
- Uploaded content is scanned for obvious prompt-injection phrases.
- Published Knowledge Releases are immutable; runtime answers cite chunk snapshots instead of mutable admin documents.
- Runtime refuses to silently use stale embedding vectors with a different configured model; it falls back to ephemeral retrieval and exposes the strategy.
- Evaluation datasets include abstention cases so weak evidence is tested, not just happy-path retrieval.
- Admin operations are audited without raw sensitive payloads.
- Raw prompts should not be logged in production.
- Rendered markdown must be sanitized before rich rendering is enabled.
