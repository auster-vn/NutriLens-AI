from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from pathlib import Path

from app.core.config import get_settings
from app.core.models import LabelOcrEvaluationRun, ProductLabelExtraction
from app.products.label_extraction import parse_label_text
from app.products.label_ocr.preprocessing import preprocess_image
from app.products.label_ocr.providers import PaddleOcrProvider, TesseractProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_DATASET = Path(__file__).resolve().parents[5] / "data" / "benchmarks" / "label_ocr_v1.json"


def load_benchmark(path: Path = DEFAULT_DATASET) -> tuple[dict, str]:
    raw = path.read_bytes()
    dataset = json.loads(raw)
    digest = sha256(raw)
    for case in sorted(dataset.get("cases", []), key=lambda item: item["id"]):
        image_path = case.get("image_path")
        if image_path:
            digest.update((path.parent / image_path).read_bytes())
    return dataset, digest.hexdigest()


async def evaluate_label_pipeline(session: AsyncSession, path: Path = DEFAULT_DATASET) -> LabelOcrEvaluationRun:
    dataset, dataset_hash = load_benchmark(path)
    case_results = []
    for case in dataset["cases"]:
        result = _evaluate_case(case)
        result["runtime_ocr"] = await _evaluate_runtime_providers(case, path.parent)
        case_results.append(result)
    confirmed = list(
        (
            await session.execute(select(ProductLabelExtraction).where(ProductLabelExtraction.status == "confirmed"))
        ).scalars()
    )
    case_results.extend(_evaluate_confirmed_extraction(extraction) for extraction in confirmed)
    metrics = _aggregate(case_results)
    metrics["runtime_provider_cer"] = _aggregate_runtime_cer(case_results)
    settings = get_settings()
    readiness = {
        "layoutlm_or_ner_ready": len(case_results) >= settings.label_ocr_benchmark_min_cases_for_layoutlm
        and metrics["field_f1"] >= settings.label_ocr_benchmark_min_field_f1,
        "labeled_case_count": len(case_results),
        "required_case_count": settings.label_ocr_benchmark_min_cases_for_layoutlm,
        "field_f1": metrics["field_f1"],
        "required_field_f1": settings.label_ocr_benchmark_min_field_f1,
        "recommendation": "Collect and review more real package labels before training LayoutLMv3/NER.",
    }
    run = LabelOcrEvaluationRun(
        dataset_name=dataset["name"],
        dataset_hash=dataset_hash,
        providers=["tesseract", "paddleocr", "ensemble"],
        metrics_json=metrics,
        case_results=case_results,
        readiness_json=readiness,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


def _evaluate_case(case: dict) -> dict:
    provider_cer = {
        provider: _cer(case["ground_truth_text"], hypothesis)
        for provider, hypothesis in case.get("ocr_text_by_provider", {}).items()
    }
    best_provider = min(provider_cer, key=provider_cer.get) if provider_cer else "ground_truth"
    text = case.get("ocr_text_by_provider", {}).get(best_provider, case["ground_truth_text"])
    parsed = parse_label_text(_restore_lines(text))
    expected = case["expected"]
    expected_fields = set(expected.get("nutriments", {}))
    actual_fields = set(parsed.nutriments)
    true_fields = expected_fields & actual_fields
    precision = len(true_fields) / max(1, len(actual_fields))
    recall = len(true_fields) / max(1, len(expected_fields))
    field_f1 = 2 * precision * recall / max(1e-9, precision + recall)
    numeric_matches = [
        abs(parsed.nutriments[key] - expected["nutriments"][key]) <= max(0.01, abs(expected["nutriments"][key]) * 0.02)
        for key in true_fields
    ]
    expected_allergens = set(expected.get("allergens", []))
    allergen_recall = (
        len(expected_allergens & set(parsed.allergens)) / len(expected_allergens) if expected_allergens else None
    )
    return {
        "id": case["id"],
        "language": case["language"],
        "difficulty": case["difficulty"],
        "provider_cer": provider_cer,
        "best_provider": best_provider,
        "field_precision": round(precision, 4),
        "field_recall": round(recall, 4),
        "field_f1": round(field_f1, 4),
        "numeric_accuracy": round(sum(numeric_matches) / max(1, len(numeric_matches)), 4),
        "allergen_recall": round(allergen_recall, 4) if allergen_recall is not None else None,
        "expected_fields": sorted(expected_fields),
        "actual_fields": sorted(actual_fields),
    }


def _evaluate_confirmed_extraction(extraction: ProductLabelExtraction) -> dict:
    predicted = extraction.extracted_json or {}
    confirmed = predicted.get("confirmed") or {}
    expected_nutriments = confirmed.get("nutriments") or {}
    actual_nutriments = predicted.get("nutriments") or {}
    expected_fields, actual_fields = set(expected_nutriments), set(actual_nutriments)
    true_fields = expected_fields & actual_fields
    precision = len(true_fields) / max(1, len(actual_fields))
    recall = len(true_fields) / max(1, len(expected_fields))
    field_f1 = 2 * precision * recall / max(1e-9, precision + recall)
    numeric_matches = [
        abs(float(actual_nutriments[key]) - float(expected_nutriments[key]))
        <= max(0.01, abs(float(expected_nutriments[key])) * 0.02)
        for key in true_fields
        if _is_number(actual_nutriments[key]) and _is_number(expected_nutriments[key])
    ]
    expected_allergens = set(confirmed.get("allergens") or [])
    allergen_recall = (
        len(expected_allergens & set(predicted.get("allergens") or [])) / len(expected_allergens)
        if expected_allergens
        else None
    )
    return {
        "id": f"confirmed-{extraction.id}",
        "language": "unknown",
        "difficulty": "production_correction",
        "provider_cer": {},
        "runtime_ocr": {},
        "best_provider": extraction.ocr_provider,
        "field_precision": round(precision, 4),
        "field_recall": round(recall, 4),
        "field_f1": round(field_f1, 4),
        "numeric_accuracy": round(sum(numeric_matches) / max(1, len(numeric_matches)), 4),
        "allergen_recall": round(allergen_recall, 4) if allergen_recall is not None else None,
        "expected_fields": sorted(expected_fields),
        "actual_fields": sorted(actual_fields),
    }


def _aggregate(cases: list[dict]) -> dict:
    providers = sorted({provider for case in cases for provider in case["provider_cer"]})
    provider_cer = {
        provider: round(
            sum(case["provider_cer"][provider] for case in cases if provider in case["provider_cer"])
            / max(1, sum(provider in case["provider_cer"] for case in cases)),
            4,
        )
        for provider in providers
    }

    def mean(key: str) -> float:
        values = [case[key] for case in cases if case[key] is not None]
        return round(sum(values) / max(1, len(values)), 4)

    return {
        "case_count": len(cases),
        "provider_cer": provider_cer,
        "field_precision": mean("field_precision"),
        "field_recall": mean("field_recall"),
        "field_f1": mean("field_f1"),
        "numeric_accuracy": mean("numeric_accuracy"),
        "allergen_recall": mean("allergen_recall"),
    }


async def _evaluate_runtime_providers(case: dict, dataset_directory: Path) -> dict:
    image_path = case.get("image_path")
    if not image_path:
        return {}
    image_bytes = (dataset_directory / image_path).read_bytes()
    preprocessed = preprocess_image(image_bytes)
    image = preprocessed.variants["enhanced"]
    results = {}
    for provider in (TesseractProvider(), PaddleOcrProvider()):
        if not provider.available():
            results[provider.name] = {"status": "unavailable"}
            continue
        try:
            document = await asyncio.wait_for(
                asyncio.to_thread(provider.recognize, image, "enhanced"),
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001
            results[provider.name] = {"status": "failed", "error": str(exc)}
        else:
            results[provider.name] = {
                "status": "succeeded",
                "cer": _cer(case["ground_truth_text"], document.text),
                "confidence": document.confidence,
                "word_count": len(document.words),
            }
    return results


def _aggregate_runtime_cer(cases: list[dict]) -> dict:
    providers = {
        provider
        for case in cases
        for provider, result in case.get("runtime_ocr", {}).items()
        if result.get("status") == "succeeded"
    }
    return {
        provider: round(
            sum(
                case["runtime_ocr"][provider]["cer"]
                for case in cases
                if case.get("runtime_ocr", {}).get(provider, {}).get("status") == "succeeded"
            )
            / sum(case.get("runtime_ocr", {}).get(provider, {}).get("status") == "succeeded" for case in cases),
            4,
        )
        for provider in sorted(providers)
    }


def _cer(reference: str, hypothesis: str) -> float:
    reference, hypothesis = reference.casefold(), hypothesis.casefold()
    previous = list(range(len(hypothesis) + 1))
    for row, ref_char in enumerate(reference, start=1):
        current = [row]
        for column, hyp_char in enumerate(hypothesis, start=1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (ref_char != hyp_char)))
        previous = current
    return round(previous[-1] / max(1, len(reference)), 4)


def _restore_lines(text: str) -> str:
    headings = (
        "Thành phần",
        "THÀNH PHẦN",
        "Ingredients",
        "DINH DƯỠNG",
        "Dinh dưỡng",
        "Nutrition",
        "Energy",
        "Năng lượng",
        "Protein",
        "Chất đạm",
        "Fat",
        "Chất béo",
        "Carbohydrate",
        "Sugars",
        "Đường",
        "Sodium",
        "Natri",
    )
    restored = text
    for heading in headings:
        restored = restored.replace(f" {heading}", f"\n{heading}")
    return restored


def _is_number(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
