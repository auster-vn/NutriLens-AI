from __future__ import annotations

import re

from app.products.label_ocr.contracts import DocumentBlock, ExtractedField, OcrDocument, union_bbox

VALUE_PATTERN = re.compile(r"^<?\s*(\d+(?:[.,]\d+)?)\s*(kcal|kj|mg|g)?\s*%?$", re.I)
KEY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("saturated-fat_100g", re.compile(r"saturated|saturates|bão\s*hòa", re.I)),
    ("carbohydrates_100g", re.compile(r"carbohydrate|cacbohydrat|bột\s*đường", re.I)),
    ("sugars_100g", re.compile(r"sugars?|đường", re.I)),
    ("proteins_100g", re.compile(r"proteins?|chất\s*đạm|\bđạm\b", re.I)),
    ("fiber_100g", re.compile(r"fib(?:er|re)|chất\s*xơ", re.I)),
    ("sodium_100g", re.compile(r"sodium|natri", re.I)),
    ("salt_100g", re.compile(r"salt|muối", re.I)),
    ("fat_100g", re.compile(r"(?:total\s*)?fat|chất\s*béo", re.I)),
    ("energy-kcal_100g", re.compile(r"energy|năng\s*lượng", re.I)),
]


def parse_nutrition_table(
    document: OcrDocument,
    blocks: list[DocumentBlock],
    provider_agreement: dict[int, float],
) -> tuple[dict[str, float], dict[str, ExtractedField]]:
    nutrition_blocks = [block for block in blocks if block.kind == "nutrition"]
    target_column_x = _infer_100g_column(document, nutrition_blocks)
    fields: dict[str, ExtractedField] = {}
    values: dict[str, float] = {}
    for block in nutrition_blocks:
        key = next((key for key, pattern in KEY_PATTERNS if pattern.search(block.text)), None)
        if not key or key in values:
            continue
        ordered_indexes = sorted(block.word_indexes, key=lambda item: document.words[item].bbox[0])
        candidates = []
        for position, index in enumerate(ordered_indexes):
            word = document.words[index]
            match = VALUE_PATTERN.match(word.text.strip())
            if match:
                adjacent_unit = None
                if position + 1 < len(ordered_indexes):
                    next_word = document.words[ordered_indexes[position + 1]].text.casefold().strip()
                    if next_word in {"g", "mg", "kcal", "kj"}:
                        adjacent_unit = next_word
                candidates.append((index, word, match, adjacent_unit))
        if not candidates:
            combined = re.search(r"<?\s*(\d+(?:[.,]\d+)?)\s*(kcal|kj|mg|g)\b", block.text, re.I)
            if not combined:
                continue
            raw_number, unit = combined.group(1), combined.group(2)
            source_indexes = block.word_indexes
            ocr_confidence = block.confidence
            agreement = sum(provider_agreement.get(index, 1.0) for index in source_indexes) / max(
                1, len(source_indexes)
            )
        else:
            if target_column_x is None:
                index, word, match, adjacent_unit = max(candidates, key=lambda item: item[1].bbox[0])
            else:
                index, word, match, adjacent_unit = min(
                    candidates,
                    key=lambda item: abs((item[1].bbox[0] + item[1].bbox[2]) / 2 - target_column_x),
                )
            raw_number, unit = match.group(1), match.group(2) or adjacent_unit or "g"
            source_indexes = [index]
            ocr_confidence = word.confidence
            agreement = provider_agreement.get(index, 1.0)
        value = float(raw_number.replace(",", "."))
        unit = unit.lower()
        if key == "energy-kcal_100g" and unit == "kj":
            value = round(value / 4.184, 1)
        elif unit == "mg":
            value = round(value / 1000, 4)
        value = round(value, 4)
        values[key] = value
        fields[key] = ExtractedField(
            key=key,
            value=value,
            confidence=round(ocr_confidence * (0.82 + 0.18 * agreement), 3),
            source_bbox=union_bbox([document.words[index].bbox for index in source_indexes]),
            provider_agreement=round(agreement, 3),
            parser="bbox-nutrition-v2",
            raw_value=f"{raw_number} {unit}",
        )
    return values, fields


def _infer_100g_column(document: OcrDocument, blocks: list[DocumentBlock]) -> float | None:
    for block in blocks:
        if not re.search(r"(?:100\s*(?:g|ml)|per\s*100)", block.text, re.I):
            continue
        ordered = sorted(block.word_indexes, key=lambda index: document.words[index].bbox[0])
        for position, index in enumerate(ordered):
            word = document.words[index]
            if word.text.strip().casefold() == "100":
                return (word.bbox[0] + word.bbox[2]) / 2
            match = re.search(r"100\s*(?:g|ml)", word.text, re.I)
            if match:
                return (word.bbox[0] + word.bbox[2]) / 2
            if position + 1 < len(ordered) and word.text.casefold() == "per":
                next_word = document.words[ordered[position + 1]]
                if next_word.text.strip() == "100":
                    return (next_word.bbox[0] + next_word.bbox[2]) / 2
    return None


def validate_nutriments(values: dict[str, float]) -> list[str]:
    issues: list[str] = []
    for key, value in values.items():
        if value < 0 or (key != "energy-kcal_100g" and value > 100):
            issues.append(f"Giá trị {key} nằm ngoài phạm vi hợp lý.")
    if values.get("sugars_100g", 0) > values.get("carbohydrates_100g", 100):
        issues.append("Đường lớn hơn tổng carbohydrate.")
    if values.get("saturated-fat_100g", 0) > values.get("fat_100g", 100):
        issues.append("Chất béo bão hòa lớn hơn tổng chất béo.")
    macros = sum(
        values.get(key, 0) * factor
        for key, factor in (("proteins_100g", 4), ("carbohydrates_100g", 4), ("fat_100g", 9))
    )
    energy = values.get("energy-kcal_100g")
    if energy and macros and abs(energy - macros) / max(energy, 1) > 0.35:
        issues.append("Calories không khớp với tổng năng lượng ước tính từ macro.")
    return issues
