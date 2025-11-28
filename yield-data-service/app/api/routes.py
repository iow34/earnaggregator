"""
API маршрути (ендпоінти) - РОЗДІЛ 3.1: Створення API endpoints та бізнес-логіки.

Основні ендпоінти (РОЗДІЛ 3.1):
- GET /api/v1/yield/{symbol} - дані по конкретній монеті з валідацією
- GET /api/v1/top?limit=N - топ N пропозицій за APY
- GET /api/v1/exchanges?exchange=X - дані з конкретної біржі
- GET /api/v1/health - статус сервісу

Додаткові ендпоінти:
- GET /api/v1/exchanges/list - список доступних бірж
- GET /api/v1/recommendations/{user_id} - персоналізовані рекомендації
- GET /api/v1/stats - статистика БД
- GET /api/v1/cache/stats - статистика кешу

Всі ендпоінти використовують кеш для економії API кредитів та включають валідацію параметрів.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, UTC

from app.db.database import get_database_session, get_db_transaction
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD, CacheMetadataCRUD, PriorityProductCRUD, get_database_stats
from app.models.yield_product import YieldProduct, YieldProductFilter, YieldProductCreate
from app.models.response import (
    YieldResponse, TopByProviderResponse, ErrorResponse, create_success_response,
    create_error_response, HealthResponse, StatsResponse
)
from app.services.cache import cache_manager, get_yield_cache_key, get_top_cache_key
from app.services.exchanges import exchange_registry
from app.services.aggregation_service import aggregation_service, AggregationStrategy, DataSource
from app.services.coingecko_service import coingecko_service
from app.services.scheduler import (
    get_scheduler_status,
    get_scheduler_metrics,
    get_prometheus_metrics,
    trigger_cache_update,
    trigger_db_sync,
    trigger_health_check
)
from app.utils.logger import logger
from app.__version__ import __version__

# Створюємо роутер для основних API
router = APIRouter(prefix="/api/v1", tags=["yield"])

# Окремий роутер для Prometheus метрик (без префіксу)
metrics_router = APIRouter(tags=["metrics"])

# [CONTENT TRUNCATED - файл занадто великий для повного відображення]
# Використовую локальний файл для оновлення