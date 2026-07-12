import pytest
from app.products.barcodes import (
    BarcodeParseError,
    expand_upc_e,
    has_valid_gtin_checksum,
    normalize_product_code,
)


@pytest.mark.parametrize(
    ("raw", "format_name", "expected", "kind"),
    [
        ("96385074", "EAN_8", "96385074", "linear"),
        ("036000291452", "UPC_A", "036000291452", "linear"),
        ("4006381333931", "EAN_13", "4006381333931", "linear"),
        ("10012345000017", "ITF", "10012345000017", "linear"),
        ("04252614", "UPC_E", "042100005264", "linear"),
        ("(01)09506000134352", "CODE_128", "09506000134352", "gs1_ai_01"),
        ("]d20109506000134352\x1d17271231", "DATA_MATRIX", "09506000134352", "gs1_ai_01"),
        (
            "https://id.gs1.org/01/09506000134352/10/ABC123",
            "QR_CODE",
            "09506000134352",
            "gs1_digital_link",
        ),
        ("https://example.com/lookup?gtin=4006381333931", "QR_CODE", "4006381333931", "gs1_digital_link"),
        ("4006 3813-3393 1", None, "4006381333931", "linear"),
    ],
)
def test_normalize_product_code_supports_retail_and_gs1_formats(raw, format_name, expected, kind):
    result = normalize_product_code(raw, format_name)

    assert result.gtin == expected
    assert result.source_kind == kind


@pytest.mark.parametrize("gtin", ["96385074", "036000291452", "4006381333931", "10012345000017"])
def test_known_gtins_have_valid_check_digits(gtin):
    assert has_valid_gtin_checksum(gtin)


def test_upc_e_expands_without_losing_leading_zero():
    assert expand_upc_e("04252614") == "042100005264"


@pytest.mark.parametrize("value", ["", "ABC-123", "https://example.com/promo", "1234567890"])
def test_non_product_codes_are_rejected(value):
    with pytest.raises(BarcodeParseError):
        normalize_product_code(value, "QR_CODE")
