"""
Сервіси для Data Service - РОЗДІЛ 3.2: Бізнес-логіка.

Модулі включають:
- aggregation_service: Сервіс агрегації даних з бірж
- exchanges: Реєстр та інтеграції з біржами (динамічне завантаження)
- cache: Робота з Redis кешем
- scheduler: Автоматичне оновлення кешу
- coingecko_service: Інтеграція з CoinGecko API для популярності монет
"""

from .aggregation_service import DataAggregationService, aggregation_service
from .exchanges import exchange_registry
from .cache import CacheManager, cache_manager
from .scheduler import (
    start_scheduler,
    start_scheduler_async,
    stop_scheduler,
    get_scheduler_status,
    get_scheduler_metrics,
    get_prometheus_metrics,
    data_scheduler
)

__all__ = [
    "DataAggregationService",
    "aggregation_service",
    "exchange_registry",
    "CacheManager",
    "cache_manager",
    "start_scheduler",
    "start_scheduler_async",
    "stop_scheduler",
    "get_scheduler_status",
    "get_scheduler_metrics",
    "get_prometheus_metrics",
    "data_scheduler"
]
