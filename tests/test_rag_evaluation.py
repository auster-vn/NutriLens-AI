import json
from pathlib import Path

from app.rag.service import answer_question, search_knowledge

EVALUATION_DIR = Path("tests/evaluation")


def _read_jsonl(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (EVALUATION_DIR / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_rag_evaluation_cases_return_expected_sources():
    for case in _read_jsonl("nutrition_rag_questions.jsonl"):
        results = search_knowledge(case["question"])
        sources = {result.source for result in results}
        for expected in case.get("expected_sources", []):
            assert expected in sources


def test_abstain_cases_abstain():
    for case in _read_jsonl("abstain_cases.jsonl"):
        response = answer_question(case["question"])
        assert response.abstained is case["should_abstain"]


def test_mixed_cases_classified_as_mixed_with_barcode():
    for case in _read_jsonl("mixed_product_rag_questions.jsonl"):
        response = answer_question(case["question"], barcode="12345678")
        assert response.route == case["expected_route"]
