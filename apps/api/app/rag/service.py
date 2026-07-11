import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.products.scoring import DISCLAIMER
from app.rag.text import tokenize as analyze_tokens
from app.schemas.rag import ChatResponse, Citation

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "nutrition_knowledge"
NUTRITION_TERMS = {
    "đường",
    "sugar",
    "sodium",
    "muối",
    "salt",
    "protein",
    "fiber",
    "xơ",
    "fat",
    "béo",
    "allergen",
    "dị",
    "ứng",
    "gluten",
    "lactose",
    "vegan",
    "vegetarian",
    "nutri",
    "score",
    "phụ",
    "gia",
    "expiry",
    "hạn",
    "nutrition",
    "dinh",
    "dưỡng",
}


@dataclass(frozen=True)
class KnowledgeDocument:
    filename: str
    title: str
    metadata: dict
    body: str


@dataclass(frozen=True)
class RankedPassage:
    score: int
    document: KnowledgeDocument
    paragraph: str


def tokenize(text: str) -> set[str]:
    return set(analyze_tokens(text))


def parse_document(path: Path) -> KnowledgeDocument:
    text = path.read_text(encoding="utf-8")
    metadata: dict = {}
    body = text
    if text.startswith("```json"):
        _, raw_meta, rest = text.split("```", 2)
        metadata = json.loads(raw_meta.removeprefix("json").strip())
        body = rest.strip()
    title = next((line.removeprefix("#").strip() for line in body.splitlines() if line.startswith("#")), path.stem)
    return KnowledgeDocument(filename=path.name, title=title, metadata=metadata, body=body)


def load_documents() -> list[KnowledgeDocument]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return [parse_document(path) for path in sorted(KNOWLEDGE_DIR.glob("*.md"))]


def search_knowledge(
    question: str,
    limit: int = 5,
    additional_documents: list[KnowledgeDocument] | None = None,
) -> list[Citation]:
    passages = _rank_passages(question, additional_documents)
    return [_citation(passage.document, passage.paragraph) for passage in passages[:limit]]


def answer_question(
    question: str,
    barcode: str | None = None,
    additional_documents: list[KnowledgeDocument] | None = None,
) -> ChatResponse:
    passages = _rank_passages(question, additional_documents)
    query_tokens = tokenize(question)
    if not query_tokens & NUTRITION_TERMS:
        passages = []
    if passages and passages[0].score < 4:
        passages = []
    elif passages:
        relative_threshold = max(4, passages[0].score * 0.8)
        passages = [passage for passage in passages if passage.score >= relative_threshold]
    citations = [_citation(passage.document, passage.paragraph) for passage in passages[:3]]
    route = classify_route(question, barcode)
    if not citations:
        return ChatResponse(
            route=route,
            answer="Mình chưa có đủ nguồn đáng tin trong kho kiến thức để trả lời chắc chắn.",
            citations=[],
            abstained=True,
            disclaimer=DISCLAIMER,
        )
    product_prefix = ""
    if route in {"product", "mixed"}:
        product_prefix = (
            f"Với barcode {barcode}, các số liệu sản phẩm phải lấy từ cache/Open Food Facts. "
            if barcode
            else "Nếu câu hỏi liên quan sản phẩm cụ thể, cần barcode hoặc dữ liệu sản phẩm trước khi kết luận. "
        )
    answer_points = [_clean_answer_sentence(passage.paragraph) for passage in passages[:3]]
    answer = product_prefix + " ".join(point for point in answer_points if point)
    if route == "product" and not barcode:
        answer += " Hiện chưa có barcode nên mình không thể xác nhận thông tin riêng của sản phẩm."
    return ChatResponse(
        route=route,
        answer=answer,
        citations=citations,
        abstained=False,
        disclaimer=DISCLAIMER,
    )


def classify_route(question: str, barcode: str | None = None) -> str:
    lowered = question.lower()
    product_terms = {"sản phẩm này", "barcode", "allergen", "dị ứng", "dùng được", "phù hợp", "nutri-score"}
    concept_terms = {"là gì", "nghĩa là", "vì sao", "hướng dẫn", "khuyến nghị", "cao có sao"}
    if barcode:
        return "mixed"
    has_product = bool(barcode) or any(term in lowered for term in product_terms)
    has_concept = any(term in lowered for term in concept_terms)
    if has_product and has_concept:
        return "mixed"
    if has_product:
        return "product"
    return "rag"


def _rank_passages(
    question: str,
    additional_documents: list[KnowledgeDocument] | None = None,
) -> list[RankedPassage]:
    query_tokens = set(analyze_tokens(question, remove_stop_words=True, expand_aliases=True))
    best_by_document: dict[str, RankedPassage] = {}
    documents_by_filename = {document.filename: document for document in load_documents()}
    documents_by_filename.update({document.filename: document for document in additional_documents or []})
    for doc in documents_by_filename.values():
        domain_tokens = tokenize(" ".join(doc.metadata.get("domains", [])) + " " + doc.title)
        for paragraph in _paragraphs(doc.body):
            paragraph_tokens = set(analyze_tokens(paragraph, remove_stop_words=True))
            overlap = len(query_tokens & paragraph_tokens)
            domain_overlap = len(query_tokens & domain_tokens)
            score = overlap * 3 + domain_overlap
            if score:
                passage = RankedPassage(score=score, document=doc, paragraph=paragraph)
                current = best_by_document.get(doc.filename)
                if current is None or passage.score > current.score:
                    best_by_document[doc.filename] = passage
    ranked = list(best_by_document.values())
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
def _paragraphs(body: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"\n\s*\n", body)
        if part.strip() and not part.strip().startswith("#")
    ]


def _citation(doc: KnowledgeDocument, paragraph: str) -> Citation:
    return Citation(
        source=doc.filename,
        title=doc.title,
        source_url=doc.metadata.get("source_url"),
        snippet=paragraph[:420],
    )


def _clean_answer_sentence(paragraph: str) -> str:
    cleaned = re.sub(r"\s+", " ", paragraph).strip()
    if not cleaned.endswith((".", "!", "?")):
        cleaned += "."
    return cleaned


def validate_metadata(metadata: dict) -> list[str]:
    required = {
        "authority",
        "source_url",
        "jurisdiction",
        "risk_level",
        "effective_from",
        "expires_at",
        "reviewed_at",
        "evidence_level",
        "domains",
        "status",
    }
    return sorted(required - set(metadata))


def has_prompt_injection_risk(content: str) -> bool:
    lowered = content.lower()
    risky = ["ignore previous", "ignore all previous", "system prompt", "developer message"]
    return any(term in lowered for term in risky)
