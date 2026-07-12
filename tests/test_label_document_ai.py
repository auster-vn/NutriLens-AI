import io
import sys
from types import SimpleNamespace

import pytest
from app.core.models import Base
from app.products.label_extraction import extract_label, parse_document
from app.products.label_ocr.benchmark import evaluate_label_pipeline, load_benchmark
from app.products.label_ocr.contracts import OcrDocument, OcrWord
from app.products.label_ocr.ingredients import canonicalize_ingredient, parse_ingredient_list
from app.products.label_ocr.preprocessing import preprocess_image
from app.products.label_ocr.providers import PaddleOcrProvider, reconcile_documents
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _document(words: list[OcrWord], provider: str = "tesseract") -> OcrDocument:
    return OcrDocument("", words, 0.9, provider, 900, 500)


def test_bbox_nutrition_parser_pairs_value_with_adjacent_unit():
    words = [
        OcrWord("Nutrition", 0.95, (10, 10, 100, 30), "tesseract", 1, 1),
        OcrWord("Sodium", 0.94, (10, 60, 90, 82), "tesseract", 1, 2),
        OcrWord("75", 0.91, (400, 60, 430, 82), "tesseract", 1, 2),
        OcrWord("mg", 0.93, (438, 60, 470, 82), "tesseract", 1, 2),
    ]

    result = parse_document(_document(words))

    assert result.nutriments["sodium_100g"] == 0.075
    assert result.fields["sodium_100g"]["source_bbox"] == (400, 60, 430, 82)
    assert result.fields["sodium_100g"]["parser"] == "bbox-nutrition-v2"


def test_bbox_nutrition_parser_selects_per_100g_column_over_serving_and_dv():
    words = [
        OcrWord("Nutrition", 0.95, (10, 10, 100, 30), "tesseract", 1, 1),
        OcrWord("Serving", 0.95, (260, 40, 330, 60), "tesseract", 1, 2),
        OcrWord("100", 0.95, (470, 40, 510, 60), "tesseract", 1, 2),
        OcrWord("g", 0.95, (515, 40, 530, 60), "tesseract", 1, 2),
        OcrWord("%DV", 0.95, (700, 40, 750, 60), "tesseract", 1, 2),
        OcrWord("Protein", 0.94, (10, 90, 90, 112), "tesseract", 1, 3),
        OcrWord("3", 0.92, (280, 90, 300, 112), "tesseract", 1, 3),
        OcrWord("g", 0.92, (305, 90, 320, 112), "tesseract", 1, 3),
        OcrWord("8", 0.93, (480, 90, 500, 112), "tesseract", 1, 3),
        OcrWord("g", 0.93, (505, 90, 520, 112), "tesseract", 1, 3),
        OcrWord("16%", 0.9, (700, 90, 740, 112), "tesseract", 1, 3),
    ]

    result = parse_document(_document(words))

    assert result.nutriments["proteins_100g"] == 8
    assert result.fields["proteins_100g"]["source_bbox"] == (480, 90, 500, 112)


def test_nested_ingredient_parser_preserves_children_and_percentages():
    entities = parse_ingredient_list("chocolate (đường, cacao, sữa 12%), bột mì")

    assert entities[0].raw_name == "chocolate"
    assert [child.canonical_id for child in entities[0].children] == ["sugar", "cocoa", "milk"]
    assert entities[0].children[2].percentage == 12
    assert entities[1].canonical_id == "wheat_flour"


def test_ingredient_ontology_tolerates_small_ocr_errors():
    canonical, score = canonicalize_ingredient("bot whev")

    assert canonical == "whey_powder"
    assert score >= 0.78


def test_ocr_ensemble_records_cross_provider_agreement():
    left = _document([OcrWord("Protein", 0.8, (10, 10, 90, 30), "tesseract", 1, 1)])
    right = _document([OcrWord("Protein", 0.95, (12, 10, 92, 30), "paddleocr", 1, 1)], "paddleocr")

    ensemble, agreement = reconcile_documents([left, right])

    assert ensemble.provider == "ensemble"
    assert ensemble.words[0].provider == "ensemble"
    assert agreement[0] == 1
    assert ensemble.words[0].confidence == pytest.approx(0.95)


def test_paddle_adapter_preserves_word_bbox_and_confidence(monkeypatch: pytest.MonkeyPatch):
    class FakePaddleEngine:
        def __init__(self, **_: object) -> None:
            pass

        def predict(self, _: object):
            return [
                {
                    "rec_texts": ["Protein", "8", "g"],
                    "rec_scores": [0.98, 0.96, 0.95],
                    "rec_boxes": [[10, 20, 110, 48], [420, 20, 445, 48], [452, 20, 470, 48]],
                }
            ]

    monkeypatch.setitem(sys.modules, "paddleocr", SimpleNamespace(PaddleOCR=FakePaddleEngine))
    provider = PaddleOcrProvider()

    document = provider.recognize(Image.new("RGB", (600, 200), "white"), "enhanced")

    assert document.provider == "paddleocr"
    assert document.words[0].text == "Protein"
    assert document.words[0].bbox == (10, 20, 110, 48)
    assert document.words[0].confidence == pytest.approx(0.98)


def test_preprocessing_produces_quality_and_transform_metadata():
    image = Image.new("RGB", (900, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 120), "Ingredients: oats, milk", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = preprocess_image(buffer.getvalue())

    assert set(result.variants) == {"enhanced", "adaptive"}
    assert result.metadata.original_width == 900
    assert result.metadata.output_width > 0
    assert 0 <= result.metadata.quality_score <= 1
    assert result.metadata.transforms


def test_preprocessing_corrects_perspective_and_skew():
    perspective = Image.new("RGB", (1000, 700), "white")
    draw = ImageDraw.Draw(perspective)
    draw.polygon([(150, 100), (850, 160), (800, 600), (100, 550)], fill="#eeeeee", outline="black", width=8)
    for row in range(8):
        draw.text((200, 180 + row * 40), "Ingredients milk sugar protein", fill="black")
    perspective_buffer = io.BytesIO()
    perspective.save(perspective_buffer, format="PNG")

    perspective_result = preprocess_image(perspective_buffer.getvalue())

    assert perspective_result.metadata.perspective_corrected is True
    assert "perspective_warp" in perspective_result.metadata.transforms

    base = Image.new("L", (900, 500), "white")
    draw = ImageDraw.Draw(base)
    for row in range(8):
        draw.text((80, 50 + row * 50), "Ingredients milk sugar protein nutrition 100 g", fill="black")
    skewed = base.rotate(7, expand=False, fillcolor="white").convert("RGB")
    skewed_buffer = io.BytesIO()
    skewed.save(skewed_buffer, format="PNG")

    skewed_result = preprocess_image(skewed_buffer.getvalue())

    assert skewed_result.metadata.skew_angle == pytest.approx(-7, abs=1)
    assert "deskew" in skewed_result.metadata.transforms


@pytest.mark.asyncio
async def test_quality_gate_rejects_unreadable_image_before_ocr():
    image = Image.new("RGB", (120, 120), "black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    with pytest.raises(ValueError, match="quality is too low"):
        await extract_label(buffer.getvalue())


@pytest.mark.asyncio
async def test_label_benchmark_is_versioned_and_blocks_premature_model_training(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.products.label_ocr.benchmark.TesseractProvider.available", lambda _: False)
    monkeypatch.setattr("app.products.label_ocr.benchmark.PaddleOcrProvider.available", lambda _: False)
    dataset, dataset_hash = load_benchmark()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        run = await evaluate_label_pipeline(session)

    assert run.dataset_name == dataset["name"]
    assert run.dataset_hash == dataset_hash
    assert run.metrics_json["case_count"] == len(dataset["cases"])
    assert "tesseract" in run.metrics_json["provider_cer"]
    assert run.readiness_json["layoutlm_or_ner_ready"] is False
    await engine.dispose()
