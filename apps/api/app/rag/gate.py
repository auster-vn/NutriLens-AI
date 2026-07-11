from dataclasses import asdict, dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import RagRelease
from app.rag.evaluation import evaluate_cases


@dataclass(frozen=True)
class EvaluationThresholds:
    route_accuracy: float = 1.0
    abstain_accuracy: float = 1.0
    source_recall_at_3: float = 0.8
    mean_reciprocal_rank: float = 0.7
    required_fact_coverage: float = 0.9
    retrieval_latency_p95_ms: float = 250.0


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    release_id: str
    evaluation_run_id: str
    thresholds: dict[str, float]
    metrics: dict
    failures: list[dict[str, float | str]]

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_THRESHOLDS = EvaluationThresholds()


async def evaluate_release_gate(
    session: AsyncSession,
    release_id: str,
    cases: list[dict],
    *,
    dataset_name: str,
    dataset_hash: str,
    thresholds: EvaluationThresholds = DEFAULT_THRESHOLDS,
) -> GateDecision:
    release = await session.get(RagRelease, release_id)
    if release is None:
        raise ValueError("Knowledge release not found.")
    evaluation = await evaluate_cases(
        session,
        cases,
        dataset_name=dataset_name,
        dataset_hash=dataset_hash,
        release_id=release_id,
    )
    expected = asdict(thresholds)
    failures: list[dict[str, float | str]] = []
    for metric, threshold in expected.items():
        actual = float(evaluation.metrics_json.get(metric, 0.0))
        operator = "<=" if metric.endswith("_ms") else ">="
        failed = actual > threshold if operator == "<=" else actual < threshold
        if failed:
            failures.append(
                {"metric": metric, "actual": actual, "operator": operator, "threshold": threshold}
            )
    decision = GateDecision(
        passed=not failures,
        release_id=release_id,
        evaluation_run_id=evaluation.id,
        thresholds=expected,
        metrics=evaluation.metrics_json,
        failures=failures,
    )
    metrics = dict(release.metrics_json or {})
    metrics["evaluation_gate"] = decision.as_dict()
    release.metrics_json = metrics
    await session.commit()
    return decision
