from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    grain: str
    meaning: str
    owner: str
    freshness: str


METRICS = (
    MetricDefinition(
        "citation_coverage", "day, route", "Share of RAG answers with at least one citation.", "rag", "5m"
    ),
    MetricDefinition("abstention_rate", "day, route", "Share of RAG answers that abstained.", "rag", "5m"),
    MetricDefinition("latency_mean_ms", "day, route", "Mean end-to-end RAG answer latency.", "rag", "5m"),
    MetricDefinition(
        "pipeline_success_rate", "day, pipeline", "Succeeded runs divided by completed runs.", "data", "15m"
    ),
    MetricDefinition(
        "product_completeness", "snapshot", "Mean normalized product completeness score.", "product", "1h"
    ),
)


def semantic_catalog() -> list[dict]:
    return [asdict(metric) for metric in METRICS]
