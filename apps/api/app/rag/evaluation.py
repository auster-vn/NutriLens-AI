import json
from hashlib import sha256
from pathlib import Path
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import RagEvaluationRun, RagRelease
from app.rag.pipeline import active_release
from app.rag.runtime import answer_with_retrieval


def load_evaluation_cases(paths: list[Path]) -> tuple[list[dict], str]:
    cases: list[dict] = []
    material: list[str] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(json.loads(line))
                material.append(line.strip())
    return cases, sha256("\n".join(material).encode()).hexdigest()


async def evaluate_cases(
    session: AsyncSession,
    cases: list[dict],
    *,
    dataset_name: str,
    dataset_hash: str,
    release_id: str | None = None,
) -> RagEvaluationRun:
    release = await session.get(RagRelease, release_id) if release_id else await active_release(session)
    if release_id and release is None:
        raise ValueError("Knowledge release not found.")
    results: list[dict] = []
    for case in cases:
        barcode = case.get("barcode")
        if case.get("expected_route") == "mixed" and not barcode:
            barcode = "12345678"
        answer = await answer_with_retrieval(session, case["question"], barcode, release_id=release_id)
        sources = [citation.source for citation in answer.citations]
        expected_sources = case.get("expected_sources", [])
        expected_route = case.get("expected_route")
        expected_abstain = case.get("should_abstain")
        reciprocal_rank: float | None = None
        source_recall: float | None = None
        if expected_sources:
            first_rank = next(
                (rank for rank, source in enumerate(sources, start=1) if source in expected_sources),
                None,
            )
            reciprocal_rank = 1 / first_rank if first_rank else 0.0
            source_recall = len(set(sources) & set(expected_sources)) / len(expected_sources)
        required_facts = [str(fact).lower() for fact in case.get("required_facts", [])]
        answer_lower = answer.answer.lower()
        fact_coverage = (
            sum(fact in answer_lower for fact in required_facts) / len(required_facts)
            if required_facts
            else None
        )
        results.append(
            {
                "id": case.get("id"),
                "route_correct": expected_route is None or answer.route == expected_route,
                "abstain_correct": expected_abstain is None or answer.abstained is expected_abstain,
                "source_recall": source_recall,
                "reciprocal_rank": reciprocal_rank,
                "required_fact_coverage": round(fact_coverage, 4) if fact_coverage is not None else None,
                "sources": sources,
                "route": answer.route,
                "abstained": answer.abstained,
                "retrieval_ms": answer.retrieval_ms or 0.0,
                "retrieval_trace": answer.retrieval_trace,
                "slice": case.get("slice") or _infer_slice(case),
            }
        )
    latencies = sorted(float(result["retrieval_ms"]) for result in results)
    metrics = {
        "case_count": len(results),
        "route_accuracy": _average(results, "route_correct"),
        "abstain_accuracy": _average(results, "abstain_correct"),
        "source_recall_at_3": _average(results, "source_recall"),
        "mean_reciprocal_rank": _average(results, "reciprocal_rank"),
        "required_fact_coverage": _average(results, "required_fact_coverage"),
        "retrieval_latency_mean_ms": round(mean(latencies), 2) if latencies else 0.0,
        "retrieval_latency_p50_ms": round(median(latencies), 2) if latencies else 0.0,
        "retrieval_latency_p95_ms": round(_percentile(latencies, 0.95), 2) if latencies else 0.0,
        "retrieval_experiment": next(
            (result["retrieval_trace"].get("spec") for result in results if result.get("retrieval_trace")),
            None,
        ),
        "slices": _slice_metrics(results),
        "confidence_intervals": {
            "route_accuracy": _wilson_interval(sum(result["route_correct"] for result in results), len(results)),
            "abstain_accuracy": _wilson_interval(sum(result["abstain_correct"] for result in results), len(results)),
        },
    }
    previous = await session.scalar(
        select(RagEvaluationRun)
        .where(RagEvaluationRun.dataset_name == dataset_name, RagEvaluationRun.dataset_hash == dataset_hash)
        .order_by(RagEvaluationRun.created_at.desc())
        .limit(1)
    )
    metrics["trend"] = compare_evaluation_metrics(metrics, previous.metrics_json) if previous else None
    evaluation = RagEvaluationRun(
        release_id=release.id if release else None,
        dataset_name=dataset_name,
        dataset_hash=dataset_hash,
        metrics_json=metrics,
        case_results=results,
    )
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)
    return evaluation


def _average(rows: list[dict], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, round((len(values) - 1) * quantile)))
    return values[index]


def compare_evaluation_metrics(candidate: dict, baseline: dict) -> dict:
    higher_is_better = {
        "route_accuracy",
        "abstain_accuracy",
        "source_recall_at_3",
        "mean_reciprocal_rank",
        "required_fact_coverage",
    }
    lower_is_better = {"retrieval_latency_mean_ms", "retrieval_latency_p50_ms", "retrieval_latency_p95_ms"}
    deltas: dict[str, float] = {}
    regressions: list[dict[str, float | str]] = []
    for metric in sorted(higher_is_better | lower_is_better):
        candidate_value = float(candidate.get(metric, 0.0))
        baseline_value = float(baseline.get(metric, 0.0))
        delta = round(candidate_value - baseline_value, 4)
        deltas[metric] = delta
        regressed = delta < 0 if metric in higher_is_better else delta > 0
        if regressed:
            regressions.append(
                {"metric": metric, "baseline": baseline_value, "candidate": candidate_value, "delta": delta}
            )
    return {"deltas": deltas, "regressions": regressions, "regression_count": len(regressions)}


def _infer_slice(case: dict) -> str:
    if case.get("should_abstain"):
        return "abstention"
    if case.get("expected_route") in {"product", "mixed"}:
        return "product_grounding"
    sources = case.get("expected_sources") or []
    return sources[0].removesuffix(".md") if sources else "general"


def _slice_metrics(results: list[dict]) -> dict:
    slices: dict[str, list[dict]] = {}
    for result in results:
        slices.setdefault(result["slice"], []).append(result)
    return {
        name: {
            "case_count": len(rows),
            "route_accuracy": _average(rows, "route_correct"),
            "abstain_accuracy": _average(rows, "abstain_correct"),
            "source_recall_at_3": _average(rows, "source_recall"),
            "mean_reciprocal_rank": _average(rows, "reciprocal_rank"),
        }
        for name, rows in sorted(slices.items())
    }


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float]:
    if total == 0:
        return {"lower": 0.0, "upper": 0.0}
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return {"lower": round(max(0.0, center - margin), 4), "upper": round(min(1.0, center + margin), 4)}
