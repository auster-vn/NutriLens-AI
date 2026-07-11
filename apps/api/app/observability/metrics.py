from collections import Counter
from threading import Lock


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: Counter[tuple[str, str, int]] = Counter()
        self._latency_sum: Counter[tuple[str, str]] = Counter()
        self._latency_count: Counter[tuple[str, str]] = Counter()

    def observe_http(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        route = _normalize_path(path)
        with self._lock:
            self._requests[(method, route, status_code)] += 1
            self._latency_sum[(method, route)] += duration_ms / 1000
            self._latency_count[(method, route)] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP nutrilens_http_requests_total Total HTTP requests.",
            "# TYPE nutrilens_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), value in sorted(self._requests.items()):
                labels = f'method="{method}",route="{route}",status="{status}"'
                lines.append(f"nutrilens_http_requests_total{{{labels}}} {value}")
            lines.extend(
                [
                    "# HELP nutrilens_http_request_duration_seconds HTTP request duration.",
                    "# TYPE nutrilens_http_request_duration_seconds summary",
                ]
            )
            for (method, route), value in sorted(self._latency_sum.items()):
                labels = f'method="{method}",route="{route}"'
                lines.append(f"nutrilens_http_request_duration_seconds_sum{{{labels}}} {value:.6f}")
                lines.append(
                    f"nutrilens_http_request_duration_seconds_count{{{labels}}} {self._latency_count[(method, route)]}"
                )
        return "\n".join(lines) + "\n"


def _normalize_path(path: str) -> str:
    parts = path.strip("/").split("/")
    normalized = ["{id}" if len(part) >= 32 and "-" in part else part for part in parts]
    return "/" + "/".join(normalized) if normalized != [""] else "/"


registry = MetricsRegistry()
