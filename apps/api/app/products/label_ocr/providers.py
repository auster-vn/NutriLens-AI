from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app.products.label_ocr.contracts import OcrDocument, OcrWord, bbox_iou
from PIL import Image


class OcrUnavailableError(RuntimeError):
    pass


class OcrProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def recognize(self, image: Image.Image, variant: str) -> OcrDocument: ...


class TesseractProvider:
    name = "tesseract"

    def available(self) -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
        except Exception:  # noqa: BLE001
            return False
        return True

    def recognize(self, image: Image.Image, variant: str) -> OcrDocument:
        try:
            import pytesseract
            from pytesseract import Output

            data = pytesseract.image_to_data(
                image,
                lang="vie+eng",
                config="--oem 1 --psm 6",
                output_type=Output.DICT,
                timeout=15,
            )
        except ImportError as exc:
            raise OcrUnavailableError("Tesseract Python adapter is not installed.") from exc
        except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError) as exc:
            raise OcrUnavailableError("Tesseract OCR engine or language data is unavailable.") from exc
        words: list[OcrWord] = []
        lines: dict[tuple[int, int, int], list[str]] = defaultdict(list)
        for index, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text).strip()
            if not text:
                continue
            confidence = _confidence(data.get("conf", [])[index])
            left, top = int(data["left"][index]), int(data["top"][index])
            width, height = int(data["width"][index]), int(data["height"][index])
            block_id = int(data["block_num"][index])
            line_id = int(data["line_num"][index])
            paragraph_id = int(data["par_num"][index])
            lines[(block_id, paragraph_id, line_id)].append(text)
            words.append(
                OcrWord(
                    text=text,
                    confidence=confidence,
                    bbox=(left, top, left + width, top + height),
                    provider=self.name,
                    block_id=block_id,
                    line_id=line_id,
                )
            )
        if not words:
            raise ValueError("No readable text was found in the label image.")
        return OcrDocument(
            text="\n".join(" ".join(line) for line in lines.values()),
            words=words,
            confidence=round(sum(word.confidence for word in words) / len(words), 3),
            provider=self.name,
            width=image.width,
            height=image.height,
            variant=variant,
        )


class PaddleOcrProvider:
    name = "paddleocr"

    def __init__(self) -> None:
        self._engine = None

    def available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
        except ImportError:
            return False
        return True

    def recognize(self, image: Image.Image, variant: str) -> OcrDocument:
        if not self.available():
            raise OcrUnavailableError("PaddleOCR adapter is not installed.")
        import numpy as np
        from paddleocr import PaddleOCR

        if self._engine is None:
            self._engine = PaddleOCR(lang="en", use_doc_orientation_classify=True, use_doc_unwarping=True)
        array = np.asarray(image.convert("RGB"))
        try:
            predictions = list(self._engine.predict(array))
            words = _paddle_v3_words(predictions)
        except AttributeError:
            words = _paddle_legacy_words(self._engine.ocr(array))
        if not words:
            raise ValueError("No readable text was found in the label image.")
        return OcrDocument(
            text=_words_to_text(words),
            words=words,
            confidence=round(sum(word.confidence for word in words) / len(words), 3),
            provider=self.name,
            width=image.width,
            height=image.height,
            variant=variant,
        )


def reconcile_documents(documents: list[OcrDocument]) -> tuple[OcrDocument, dict[int, float]]:
    if not documents:
        raise OcrUnavailableError("No OCR provider is available.")
    primary = max(documents, key=lambda item: (item.confidence, len(item.words)))
    words: list[OcrWord] = []
    agreement: dict[int, float] = {}
    for primary_word in primary.words:
        matches = [
            other
            for document in documents
            if document is not primary
            for other in document.words
            if bbox_iou(primary_word.bbox, other.bbox) >= 0.35
        ]
        text_matches = [word for word in matches if _normalize(word.text) == _normalize(primary_word.text)]
        provider_agreement = (1 + len(text_matches)) / len(documents)
        candidates = [primary_word, *text_matches]
        winner = max(candidates, key=lambda item: item.confidence)
        agreement[len(words)] = round(provider_agreement, 3)
        words.append(
            OcrWord(
                text=winner.text,
                confidence=round(winner.confidence * (0.75 + 0.25 * provider_agreement), 3),
                bbox=primary_word.bbox,
                provider="ensemble" if len(documents) > 1 else winner.provider,
                block_id=primary_word.block_id,
                line_id=primary_word.line_id,
            )
        )
    return (
        OcrDocument(
            text=_words_to_text(words),
            words=words,
            confidence=round(sum(word.confidence for word in words) / len(words), 3),
            provider="ensemble" if len(documents) > 1 else primary.provider,
            width=primary.width,
            height=primary.height,
            variant=primary.variant,
        ),
        agreement,
    )


def _paddle_v3_words(predictions: list) -> list[OcrWord]:
    words: list[OcrWord] = []
    for prediction in predictions:
        payload = getattr(prediction, "json", prediction)
        if callable(payload):
            payload = payload()
        if isinstance(payload, dict) and "res" in payload:
            payload = payload["res"]
        texts = payload.get("rec_texts", []) if isinstance(payload, dict) else []
        scores = payload.get("rec_scores", []) if isinstance(payload, dict) else []
        boxes = payload.get("rec_boxes", payload.get("dt_polys", [])) if isinstance(payload, dict) else []
        for index, text in enumerate(texts):
            box = boxes[index]
            coordinates = (
                list(box)
                if len(box) == 4 and not hasattr(box[0], "__len__")
                else [point for pair in box for point in pair]
            )
            xs, ys = coordinates[0::2], coordinates[1::2]
            words.append(
                OcrWord(
                    str(text),
                    float(scores[index]),
                    (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
                    "paddleocr",
                    line_id=index,
                )
            )
    return words


def _paddle_legacy_words(result: list) -> list[OcrWord]:
    words: list[OcrWord] = []
    rows = result[0] if result and isinstance(result[0], list) else result
    for index, row in enumerate(rows or []):
        polygon, recognition = row
        text, score = recognition
        xs, ys = [point[0] for point in polygon], [point[1] for point in polygon]
        words.append(
            OcrWord(
                str(text),
                float(score),
                (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
                "paddleocr",
                line_id=index,
            )
        )
    return words


def _words_to_text(words: list[OcrWord]) -> str:
    grouped: dict[tuple[int, int], list[OcrWord]] = defaultdict(list)
    for word in words:
        grouped[(word.block_id, word.line_id)].append(word)
    lines = []
    for line in grouped.values():
        lines.append(" ".join(word.text for word in sorted(line, key=lambda item: item.bbox[0])))
    return "\n".join(lines)


def _confidence(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, number / 100)), 3)


def _normalize(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())
