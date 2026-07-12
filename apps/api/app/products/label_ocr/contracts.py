from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

BBox = tuple[int, int, int, int]
BlockKind = Literal["ingredients", "nutrition", "allergen", "identity", "other"]


@dataclass(frozen=True)
class OcrWord:
    text: str
    confidence: float
    bbox: BBox
    provider: str
    block_id: int = 0
    line_id: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OcrDocument:
    text: str
    words: list[OcrWord]
    confidence: float
    provider: str
    width: int
    height: int
    variant: str = "enhanced"


@dataclass(frozen=True)
class DocumentBlock:
    kind: BlockKind
    text: str
    bbox: BBox
    confidence: float
    word_indexes: list[int]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExtractedField:
    key: str
    value: str | float | list | dict | None
    confidence: float
    source_bbox: BBox | None
    provider_agreement: float
    parser: str
    raw_value: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PreprocessingMetadata:
    original_width: int
    original_height: int
    output_width: int
    output_height: int
    blur_score: float
    brightness: float
    contrast: float
    glare_ratio: float
    skew_angle: float
    quality_score: float
    quality_issues: list[str] = field(default_factory=list)
    perspective_corrected: bool = False
    transforms: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PreprocessedImage:
    variants: dict[str, object]
    metadata: PreprocessingMetadata


def union_bbox(boxes: list[BBox]) -> BBox:
    if not boxes:
        return (0, 0, 0, 0)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def bbox_iou(left: BBox, right: BBox) -> float:
    x0, y0 = max(left[0], right[0]), max(left[1], right[1])
    x1, y1 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    left_area = max(0, left[2] - left[0]) * max(0, left[3] - left[1])
    right_area = max(0, right[2] - right[0]) * max(0, right[3] - right[1])
    denominator = left_area + right_area - intersection
    return intersection / denominator if denominator else 0.0
