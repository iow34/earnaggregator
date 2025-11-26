"""
Prometheus метрики та утиліти для інструментування.

Цей модуль збирає основні лічильники/гістограми для:
- Агрегації даних (кількість запитів, латентність)
- Зовнішніх API викликів (Binance/Bybit)
- Кешу (HIT/MISS)
- Fallback до БД
"""

from time import perf_counter
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import Counter, Histogram


# Агрегація
AGGREGATION_REQUESTS = Counter(
    "ea_aggregation_requests_total",
    "Total aggregation requests",
    labelnames=["strategy"],
)

AGGREGATION_LATENCY_SECONDS = Histogram(
    "ea_aggregation_latency_seconds",
    "Aggregation latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)


# Зовнішні API
EXTERNAL_API_CALLS = Counter(
    "ea_external_api_calls_total",
    "External API calls",
    labelnames=["exchange", "status"],  # status: success|error
)


# Кеш
CACHE_HITS = Counter(
    "ea_cache_hits_total",
    "Cache hits",
    labelnames=["source"],  # source: redis|fallback
)

CACHE_MISSES = Counter(
    "ea_cache_misses_total",
    "Cache misses",
    labelnames=["source"],
)


# Fallback до БД
DB_FALLBACKS = Counter(
    "ea_db_fallbacks_total",
    "DB fallback operations",
    labelnames=["reason"],
)


@contextmanager
def observe_latency(histogram: Histogram) -> Iterator[None]:
    """Контекст-менеджер для виміру латентності та запису в Histogram."""
    start = perf_counter()
    try:
        yield
    finally:
        duration = perf_counter() - start
        histogram.observe(duration)


