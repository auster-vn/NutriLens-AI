from pathlib import Path

from app.rag.evaluation import load_evaluation_cases

REPO_ROOT = Path(__file__).resolve().parents[4]
EVALUATION_DIR = REPO_ROOT / "tests" / "evaluation"
CORE_BENCHMARK_FILES = (
    "nutrition_rag_questions.jsonl",
    "mixed_product_rag_questions.jsonl",
    "abstain_cases.jsonl",
    "rag_benchmark_v2.jsonl",
)


def load_core_benchmark() -> tuple[list[dict], str]:
    return load_evaluation_cases([EVALUATION_DIR / filename for filename in CORE_BENCHMARK_FILES])
