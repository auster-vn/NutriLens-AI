import re
from collections.abc import Mapping
from secrets import compare_digest

from app.auth.security import get_optional_user
from app.core.config import get_settings
from app.core.models import User
from app.products.barcodes import BarcodeParseError, normalize_product_code
from fastapi import Depends, Header, HTTPException, status

SENSITIVE_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
]


def validate_barcode(barcode: str, source_format: str | None = None) -> str:
    try:
        return normalize_product_code(barcode, source_format).gtin
    except BarcodeParseError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "BARCODE_UNSUPPORTED",
                "message": str(exc),
            },
        ) from exc


def redact_sensitive_text(value: str) -> str:
    redacted = value
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


def require_admin(
    x_admin_key: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
) -> None:
    expected = get_settings().admin_key
    valid_key = bool(x_admin_key) and compare_digest(x_admin_key, expected)
    if valid_key or (user is not None and user.role == "admin"):
        return
    if user is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required.")


def audit_safe_payload(payload: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            safe[key] = redact_sensitive_text(value)[:500]
        elif isinstance(value, int | float | bool) or value is None:
            safe[key] = value
        else:
            safe[key] = "[structured]"
    return safe
