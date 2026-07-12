import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

GTIN_LENGTHS = {8, 12, 13, 14}
SYMBOLOGY_PREFIX = re.compile(r"^\][A-Za-z][0-9]")
GS1_AI_01 = re.compile(r"(?:\(01\)|^01)(\d{14})(?:\x1d|$|[^0-9])")


class BarcodeParseError(ValueError):
    pass


@dataclass(frozen=True)
class ProductCode:
    gtin: str
    source_format: str | None
    checksum_valid: bool
    source_kind: str


def normalize_product_code(value: str, source_format: str | None = None) -> ProductCode:
    raw = unquote(value).strip()
    if not raw:
        raise BarcodeParseError("Barcode is empty.")

    format_name = source_format.strip().upper() if source_format else None
    raw = SYMBOLOGY_PREFIX.sub("", raw).strip()
    digital_link = _extract_digital_link_gtin(raw)
    if digital_link:
        return _identity(digital_link, format_name or "QR_CODE", "gs1_digital_link")

    ai_match = GS1_AI_01.search(raw)
    if ai_match:
        return _identity(ai_match.group(1), format_name, "gs1_ai_01")

    compact = re.sub(r"[\s-]", "", raw)
    if not compact.isdigit() or len(compact) not in GTIN_LENGTHS:
        raise BarcodeParseError("The code was decoded, but it does not contain a supported retail GTIN.")
    if format_name == "UPC_E":
        compact = expand_upc_e(compact)
    return _identity(compact, format_name, "linear")


def has_valid_gtin_checksum(gtin: str) -> bool:
    if not gtin.isdigit() or len(gtin) not in GTIN_LENGTHS:
        return False
    payload, expected = gtin[:-1], int(gtin[-1])
    total = 0
    for index, digit in enumerate(reversed(payload), start=1):
        total += int(digit) * (3 if index % 2 == 1 else 1)
    return (10 - total % 10) % 10 == expected


def expand_upc_e(value: str) -> str:
    if len(value) != 8 or not value.isdigit():
        raise BarcodeParseError("UPC-E must contain exactly 8 digits.")
    number_system, body, check_digit = value[0], value[1:7], value[7]
    if number_system not in {"0", "1"}:
        raise BarcodeParseError("UPC-E number system must be 0 or 1.")
    x1, x2, x3, x4, x5, x6 = body
    if x6 in "012":
        payload = number_system + x1 + x2 + x6 + "0000" + x3 + x4 + x5
    elif x6 == "3":
        payload = number_system + x1 + x2 + x3 + "00000" + x4 + x5
    elif x6 == "4":
        payload = number_system + x1 + x2 + x3 + x4 + "00000" + x5
    else:
        payload = number_system + x1 + x2 + x3 + x4 + x5 + "0000" + x6
    return payload + check_digit


def _extract_digital_link_gtin(value: str) -> str | None:
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    for index, segment in enumerate(segments[:-1]):
        if segment == "01" and segments[index + 1].isdigit() and len(segments[index + 1]) == 14:
            return segments[index + 1]
    query = parse_qs(parsed.query)
    for key in ("01", "gtin"):
        candidate = query.get(key, [None])[0]
        if candidate and candidate.isdigit() and len(candidate) in GTIN_LENGTHS:
            return candidate
    return None


def _identity(gtin: str, source_format: str | None, source_kind: str) -> ProductCode:
    if len(gtin) not in GTIN_LENGTHS:
        raise BarcodeParseError("GTIN must contain 8, 12, 13, or 14 digits.")
    return ProductCode(
        gtin=gtin,
        source_format=source_format,
        checksum_valid=has_valid_gtin_checksum(gtin),
        source_kind=source_kind,
    )
