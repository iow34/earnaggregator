"""
Prometheus HTTP metrics middleware.

Реєструє базові метрики HTTP-рівня:
- http_requests_total{method, path, status}
- http_request_duration_seconds_bucket/sum/count{method, path, status}

Примітка: значення path береться як request.url.path (може спричинити високу кардинальність
для динамічних маршрутів). За потреби можна нормалізувати path (наприклад, замінювати
динамічні сегменти на плейсхолдери).
"""

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path", "status"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
    ),
)


class PrometheusHTTPMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            # У разі винятку реєструємо як 500 і повторно піднімаємо
            duration = time.perf_counter() - start
            labels = {
                "method": request.method,
                "path": request.url.path,
                "status": "500",
            }
            HTTP_REQUESTS_TOTAL.labels(**labels).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration)
            raise

        duration = time.perf_counter() - start
        labels = {
            "method": request.method,
            "path": request.url.path,
            "status": str(response.status_code),
        }
        HTTP_REQUESTS_TOTAL.labels(**labels).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration)
        return response


