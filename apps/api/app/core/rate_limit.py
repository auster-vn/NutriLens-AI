from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status

Window = tuple[int, int]

LIMITS: dict[str, Window] = {
    "auth": (12, 60),
    "scan": (20, 60),
    "label_ocr": (4, 60),
    "chat": (10, 60),
    "admin_mutation": (30, 60),
}

_buckets: dict[str, deque[float]] = defaultdict(deque)


def classify_request(request: Request) -> str | None:
    path = request.url.path
    method = request.method.upper()
    if path.startswith("/api/auth/") and method == "POST":
        return "auth"
    if path == "/api/products/scan" and method == "POST":
        return "scan"
    if path == "/api/products/label-extractions" and method == "POST":
        return "label_ocr"
    if path == "/api/chat/stream" and method == "POST":
        return "chat"
    if path.startswith("/api/admin") and method in {"POST", "PUT", "PATCH", "DELETE"}:
        return "admin_mutation"
    return None


def enforce_rate_limit(request: Request) -> None:
    bucket_type = classify_request(request)
    if bucket_type is None:
        return
    limit, window_seconds = LIMITS[bucket_type]
    identity = request.headers.get("x-admin-key") if bucket_type == "admin_mutation" else None
    identity = identity or (request.client.host if request.client else "unknown")
    bucket_key = f"{bucket_type}:{identity}"
    now = monotonic()
    bucket = _buckets[bucket_key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {bucket_type}.",
        )
    bucket.append(now)
