from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.products.label_ocr.contracts import ExtractedField, OcrDocument, OcrWord, PreprocessingMetadata
from app.products.label_ocr.ingredients import parse_ingredients
from app.products.label_ocr.layout import classify_blocks
from app.products.label_ocr.nutrition import parse_nutrition_table, validate_nutriments
from app.products.label_ocr.preprocessing import LabelImageError, preprocess_image
from app.products.label_ocr.providers import (
    OcrProvider,
    OcrUnavailableError,
    PaddleOcrProvider,
    TesseractProvider,
    reconcile_documents,
)
from PIL import Image

EXTRACTOR_VERSION = "document-ai-v2"
__all__ = ["LabelImageError", "OcrUnavailableError"]


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    provider: str = "tesseract"
    words: list[OcrWord] = field(default_factory=list)
    provider_runs: list[dict] = field(default_factory=list)
    preprocessing: PreprocessingMetadata | None = None


@dataclass(frozen=True)
class LabelExtractionResult:
    ingredients_text: str | None
    allergens: list[str]
    additives: list[str]
    nutriments: dict[str, float]
    confidence: float
    validation_issues: list[str]
    ingredient_entities: list[dict] = field(default_factory=list)
    fields: dict[str, dict] = field(default_factory=dict)
    blocks: list[dict] = field(default_factory=list)


async def extract_label(image_bytes: bytes) -> tuple[OcrResult, LabelExtractionResult]:
    preprocessed = preprocess_image(image_bytes)
    settings = get_settings()
    if preprocessed.metadata.quality_score < settings.label_ocr_quality_threshold:
        reasons = ", ".join(preprocessed.metadata.quality_issues)
        raise LabelImageError(f"Label image quality is too low ({reasons}).")
    providers = _configured_providers()
    documents: list[OcrDocument] = []
    runs: list[dict] = []
    for provider in providers:
        if not provider.available():
            runs.append({"provider": provider.name, "status": "unavailable"})
            continue
        candidates: list[OcrDocument] = []
        for variant, image in preprocessed.variants.items():
            try:
                document = await asyncio.to_thread(provider.recognize, image, variant)
            except (OcrUnavailableError, ValueError) as exc:
                runs.append({"provider": provider.name, "variant": variant, "status": "failed", "error": str(exc)})
            else:
                candidates.append(document)
                runs.append(
                    {
                        "provider": provider.name,
                        "variant": variant,
                        "status": "succeeded",
                        "confidence": document.confidence,
                        "word_count": len(document.words),
                    }
                )
        if candidates:
            documents.append(max(candidates, key=lambda item: (item.confidence, len(item.words))))
    if not documents:
        raise OcrUnavailableError("No OCR provider could read the label image.")
    document, provider_agreement = reconcile_documents(documents)
    parsed = parse_document(document, provider_agreement, preprocessed.metadata)
    return (
        OcrResult(
            text=document.text,
            confidence=document.confidence,
            provider=document.provider,
            words=document.words,
            provider_runs=runs,
            preprocessing=preprocessed.metadata,
        ),
        parsed,
    )


def parse_document(
    document: OcrDocument,
    provider_agreement: dict[int, float] | None = None,
    preprocessing: PreprocessingMetadata | None = None,
) -> LabelExtractionResult:
    provider_agreement = provider_agreement or {index: 1.0 for index in range(len(document.words))}
    blocks = classify_blocks(document)
    ingredient_field, entities, allergens, additives = parse_ingredients(document, blocks, provider_agreement)
    nutriments, nutrition_fields = parse_nutrition_table(document, blocks, provider_agreement)
    fields: dict[str, ExtractedField] = dict(nutrition_fields)
    if ingredient_field:
        fields[ingredient_field.key] = ingredient_field
    issues = validate_nutriments(nutriments)
    if preprocessing:
        issues.extend(_quality_messages(preprocessing))
    if ingredient_field is None:
        issues.append("Không xác định được vùng thành phần; cần kiểm tra ảnh hoặc nhập thủ công.")
    if not nutriments:
        issues.append("Không nhận diện được bảng dinh dưỡng trên mỗi 100 g/ml.")
    field_confidences = [item.confidence for item in fields.values()]
    extraction_confidence = (
        sum(field_confidences) / len(field_confidences) if field_confidences else document.confidence * 0.5
    )
    if preprocessing:
        extraction_confidence *= 0.75 + 0.25 * preprocessing.quality_score
    return LabelExtractionResult(
        ingredients_text=str(ingredient_field.value) if ingredient_field else None,
        allergens=allergens,
        additives=additives,
        nutriments=nutriments,
        confidence=round(max(0.0, min(1.0, extraction_confidence)), 3),
        validation_issues=list(dict.fromkeys(issues)),
        ingredient_entities=[entity.as_dict() for entity in entities],
        fields={key: value.as_dict() for key, value in fields.items()},
        blocks=[block.as_dict() for block in blocks],
    )


def parse_label_text(text: str, ocr_confidence: float = 1.0) -> LabelExtractionResult:
    document = _synthetic_document(text, ocr_confidence)
    return parse_document(document)


def prepare_image(image_bytes: bytes) -> Image.Image:
    """Backward-compatible access to the enhanced preprocessing variant."""
    return preprocess_image(image_bytes).variants["enhanced"]  # type: ignore[return-value]


def run_tesseract(image: Image.Image) -> OcrResult:
    document = TesseractProvider().recognize(image, "enhanced")
    return OcrResult(document.text, document.confidence, document.provider, document.words)


def _configured_providers() -> list[OcrProvider]:
    names = {name.strip() for name in get_settings().label_ocr_providers.split(",") if name.strip()}
    providers: list[OcrProvider] = []
    if "tesseract" in names:
        providers.append(TesseractProvider())
    if "paddleocr" in names:
        providers.append(PaddleOcrProvider())
    return providers


def _synthetic_document(text: str, confidence: float) -> OcrDocument:
    words: list[OcrWord] = []
    y = 0
    for line_id, line in enumerate(text.replace("\r", "\n").splitlines(), start=1):
        x = 0
        for token in re.findall(r"\S+", line):
            width = max(12, len(token) * 8)
            words.append(OcrWord(token, confidence, (x, y, x + width, y + 20), "synthetic", 1, line_id))
            x += width + 8
        y += 28
    return OcrDocument(text, words, confidence, "synthetic", 1000, max(28, y), "text")


def _quality_messages(metadata: PreprocessingMetadata) -> list[str]:
    translations = {
        "image_blurry": "Ảnh bị mờ; confidence OCR có thể thấp.",
        "image_too_dark": "Ảnh quá tối; nên chụp lại trong điều kiện đủ sáng.",
        "image_overexposed": "Ảnh bị cháy sáng.",
        "image_low_contrast": "Độ tương phản chữ và nền thấp.",
        "image_glare": "Ảnh có vùng phản sáng lớn.",
        "image_resolution_low": "Độ phân giải vùng nhãn thấp.",
        "opencv_unavailable": "Advanced image preprocessing is unavailable.",
    }
    return [translations.get(issue, issue) for issue in metadata.quality_issues]
