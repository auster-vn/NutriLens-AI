from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from app.products.label_ocr.contracts import DocumentBlock, ExtractedField, OcrDocument, union_bbox

ADDITIVE_PATTERN = re.compile(r"\bE[ -]?(\d{3,4}[a-z]?)\b", re.I)
PERCENTAGE_PATTERN = re.compile(r"(?:\(|\b)(\d+(?:[.,]\d+)?)\s*%")
INGREDIENT_HEADER = re.compile(r"^(?:thành\s*phần|ingredients?)\s*[:\-]?\s*", re.I)

ONTOLOGY: dict[str, tuple[str, ...]] = {
    "milk": ("milk", "cow milk", "sua", "sua bo"),
    "whey_powder": ("whey", "whey powder", "bot whey"),
    "sugar": ("sugar", "sucrose", "duong"),
    "oats": ("oat", "oats", "yen mach"),
    "soy": ("soy", "soya", "dau nanh"),
    "wheat_flour": ("wheat flour", "flour", "bot mi", "bot lua mi"),
    "cocoa": ("cocoa", "cacao"),
    "peanut": ("peanut", "dau phong", "lac"),
    "egg": ("egg", "eggs", "trung"),
    "salt": ("salt", "muoi"),
    "water": ("water", "nuoc"),
}

ALLERGEN_ONTOLOGY: dict[str, tuple[str, ...]] = {
    "milk": ("milk", "sua", "whey", "casein"),
    "egg": ("egg", "trung"),
    "peanut": ("peanut", "dau phong", "lac"),
    "soy": ("soy", "soya", "dau nanh"),
    "gluten": ("wheat", "barley", "rye", "lua mi", "lua mach", "gluten"),
    "tree_nuts": ("almond", "cashew", "walnut", "hanh nhan", "hat dieu", "oc cho"),
    "fish": ("fish", "ca"),
    "shellfish": ("shrimp", "prawn", "crab", "tom", "cua", "giap xac"),
    "sesame": ("sesame", "me", "vung"),
}


@dataclass(frozen=True)
class IngredientEntity:
    raw_name: str
    canonical_id: str | None
    percentage: float | None
    children: list[IngredientEntity]
    confidence: float

    def as_dict(self) -> dict:
        return asdict(self)


def parse_ingredients(
    document: OcrDocument,
    blocks: list[DocumentBlock],
    provider_agreement: dict[int, float],
) -> tuple[ExtractedField | None, list[IngredientEntity], list[str], list[str]]:
    ingredient_blocks = [block for block in blocks if block.kind == "ingredients"]
    if not ingredient_blocks:
        return None, [], [], []
    text = " ".join(block.text for block in ingredient_blocks)
    text = INGREDIENT_HEADER.sub("", text).strip(" .;:")
    entities = parse_ingredient_list(text)
    word_indexes = [index for block in ingredient_blocks for index in block.word_indexes]
    mean_ocr = sum(document.words[index].confidence for index in word_indexes) / max(1, len(word_indexes))
    agreement = sum(provider_agreement.get(index, 1.0) for index in word_indexes) / max(1, len(word_indexes))
    parse_coverage = sum(entity.canonical_id is not None for entity in _flatten(entities)) / max(
        1, len(_flatten(entities))
    )
    confidence = round(mean_ocr * (0.7 + 0.3 * parse_coverage) * (0.8 + 0.2 * agreement), 3)
    additives = sorted({f"E{match.upper()}" for match in ADDITIVE_PATTERN.findall(text)})
    folded = _fold(text)
    allergens = sorted(
        canonical
        for canonical, aliases in ALLERGEN_ONTOLOGY.items()
        if any(_contains_term(folded, alias) for alias in aliases)
    )
    field = ExtractedField(
        key="ingredients_text",
        value=text,
        confidence=confidence,
        source_bbox=union_bbox([block.bbox for block in ingredient_blocks]),
        provider_agreement=round(agreement, 3),
        parser="nested-ingredient-v2",
        raw_value=text,
    )
    return field, entities, allergens, additives


def parse_ingredient_list(text: str) -> list[IngredientEntity]:
    return [_parse_entity(part) for part in _split_top_level(text) if part.strip()]


def _parse_entity(value: str) -> IngredientEntity:
    value = value.strip(" .;:")
    children: list[IngredientEntity] = []
    name = value
    opening = _first_top_level_opening(value)
    if opening is not None and value.endswith(")"):
        name = value[:opening].strip()
        children = parse_ingredient_list(value[opening + 1 : -1])
    percentage_match = PERCENTAGE_PATTERN.search(name)
    percentage = float(percentage_match.group(1).replace(",", ".")) if percentage_match else None
    name = PERCENTAGE_PATTERN.sub("", name).strip(" (),")
    canonical, match_score = canonicalize_ingredient(name)
    confidence = round(0.55 + 0.45 * match_score, 3) if canonical else 0.45
    return IngredientEntity(name, canonical, percentage, children, confidence)


def canonicalize_ingredient(value: str, threshold: float = 0.78) -> tuple[str | None, float]:
    folded = _fold(value)
    best_id, best_score = None, 0.0
    for canonical, aliases in ONTOLOGY.items():
        for alias in aliases:
            score = SequenceMatcher(None, folded, alias).ratio()
            if score > best_score:
                best_id, best_score = canonical, score
    return (best_id, round(best_score, 3)) if best_score >= threshold else (None, round(best_score, 3))


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    start, depth = 0, 0
    for index, character in enumerate(value):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif character in ",;" and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def _first_top_level_opening(value: str) -> int | None:
    for index, character in enumerate(value):
        if character == "(":
            return index
    return None


def _flatten(entities: list[IngredientEntity]) -> list[IngredientEntity]:
    return [entity for item in entities for entity in [item, *_flatten(item.children)]]


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return re.sub(
        r"[^a-z0-9]+", " ", "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    ).strip()


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None
