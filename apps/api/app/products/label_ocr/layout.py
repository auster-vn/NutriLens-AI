from __future__ import annotations

import re
from collections import defaultdict

from app.products.label_ocr.contracts import DocumentBlock, OcrDocument, union_bbox

BLOCK_PATTERNS = {
    "ingredients": re.compile(r"thành\s*phần|ingredients?", re.I),
    "nutrition": re.compile(r"dinh\s*dưỡng|nutrition|energy|năng\s*lượng|protein|chất\s*béo", re.I),
    "allergen": re.compile(r"dị\s*ứng|allergen|contains|may\s*contain|có\s*thể\s*chứa", re.I),
    "identity": re.compile(r"product|sản\s*phẩm|brand|thương\s*hiệu", re.I),
}


def classify_blocks(document: OcrDocument) -> list[DocumentBlock]:
    grouped: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, word in enumerate(document.words):
        grouped[(word.block_id, word.line_id)].append(index)
    lines: list[tuple[list[int], str]] = []
    for indexes in grouped.values():
        indexes.sort(key=lambda index: document.words[index].bbox[0])
        lines.append((indexes, " ".join(document.words[index].text for index in indexes)))
    lines.sort(key=lambda item: min(document.words[index].bbox[1] for index in item[0]))
    blocks: list[DocumentBlock] = []
    active_kind = "other"
    for indexes, text in lines:
        detected = next((kind for kind, pattern in BLOCK_PATTERNS.items() if pattern.search(text)), None)
        if detected:
            active_kind = detected
        words = [document.words[index] for index in indexes]
        blocks.append(
            DocumentBlock(
                kind=active_kind,  # type: ignore[arg-type]
                text=text,
                bbox=union_bbox([word.bbox for word in words]),
                confidence=round(sum(word.confidence for word in words) / len(words), 3),
                word_indexes=indexes,
            )
        )
    return blocks
