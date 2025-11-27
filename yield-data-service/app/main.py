"""
Головний файл Data Service.

Цей файл:
- Створює FastAPI додаток
- Реєструє API маршрути
- Запускає scheduler для автоматичного оновлення кешу
- Налаштовує підключення до бази даних
- Налаштовує логування

Запуск: uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from contextlib import asynccontextmanager

from prometheus_client import generate_latest, Counter, Gauge, Histogram

from app.utils.logger import logger
from app.db.database import startup_database, shutdown_database, get_database_health
from app.api.routes import router as api_router
from app.api.tracking_routes import router as tracking_router, redirect_router
from app.services.cache import cache_manager
from app.middleware.metrics import PrometheusHTTPMetricsMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.services.scheduler import start_scheduler_async, stop_scheduler, data_scheduler
from app.services.exchanges import exchange_registry
from app.config import settings
from app.__version__ import __version__

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events для FastAPI додатку.
    
    Керує життєвим циклом додатку:
    - Startup: ініціалізація БД, scheduler
    - Shutdown: закриття з'єднань
    """
    # Startup
    logger.info("🚀 Запуск EarnAggregator Data Service...")
    
    # Спробуємо ініціалізувати БД, але не блокуємо запуск якщо недоступна
    try:
        await startup_database()
        logger.info("✅ База даних підключена")
    except Exception as e:
        logger.warning(f"⚠️ Не вдалося підключитися до БД: {e}")
        logger.info("🔄 Сервіс запускається без БД, спробуємо пізніше")
    
    # Ініціалізуємо кеш
    cache_ready = await cache_manager.initialize()
    if cache_ready:
        logger.info("✅ Redis кеш підключено")
    else:
        logger.warning("⚠️ Redis недоступний, використовується fallback кеш")

    # Ініціалізуємо реєстр бірж
    await exchange_registry.initialize()
    logger.info("✅ Реєстр бірж ініціалізовано")
    
    # Запускаємо scheduler - РОЗДІЛ 3.3
    try:
        await start_scheduler_async()
        logger.info("✅ Scheduler запущено успішно")
    except Exception as e:
        logger.warning(f"⚠️ Помилка запуску scheduler: {e}")
        logger.info("🔄 Сервіс працює без scheduler")
    
    logger.info("✅ Сервіс готовий до роботи")
    
    yield
    
    # Shutdown
    logger.info("🛑 Зупинка EarnAggregator Data Service...")
    
    # Зупиняємо scheduler
    try:
        stop_scheduler()
        logger.info("✅ Scheduler зупинено")
    except Exception as e:
        logger.warning(f"⚠️ Помилка зупинки scheduler: {e}")
    
    await cache_manager.close()
    await shutdown_database()
    logger.info("✅ Сервіс зупинено")

# Створюємо FastAPI додаток
app = FastAPI(
    title="EarnAggregator Data Service",
    description="API для отримання даних про Earn продукти з криптобірж",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Налаштування CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшні обмежити конкретними доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP metrics middleware
app.add_middleware(PrometheusHTTPMetricsMiddleware)

# Rate limiting middleware для захисту redirect endpoint
app.add_middleware(
    RateLimiterMiddleware,
    redis_url=settings.redis_url,
    rate_limit=10,  # 10 requests
    time_window=60,  # per minute
    endpoints=['/ref']  # Тільки для redirect endpoint
)

# Prometheus метрики: повертаємо базові метрики процесу/інтерпретатора

# Реєструємо API роутери
app.include_router(api_router)
app.include_router(tracking_router)  # Tracking endpoints
app.include_router(redirect_router)  # Redirect server (без prefix)

@app.get("/")
async def root():
    """Кореневий endpoint для перевірки роботи сервісу."""
    return {
        "message": "EarnAggregator Data Service",
        "status": "running",
        "version": __version__
    }

@app.get("/health")
async def health_check():
    """Health check endpoint для Docker health checks."""
    # Перевіряємо стан бази даних
    db_health = await get_database_health()
    
    # Перевіряємо стан кешу
    cache_health = await cache_manager.health_check()
    
    # Визначаємо загальний статус
    overall_status = "healthy"
    if db_health["status"] != "healthy":
        overall_status = "unhealthy"
    elif cache_health["status"] == "unhealthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": "yield-data-service",
        "database": db_health,
        "cache": cache_health
    }

@app.get("/api/v1/status")
async def api_status():
    """Статус API endpoints."""
    return {
        "api_version": "v1",
        "status": "active",
        "endpoints": [
            "/api/v1/yield/{symbol}",
            "/api/v1/top", 
            "/api/v1/exchanges",
            "/api/v1/exchanges/list",
            "/api/v1/health",
            "/api/v1/recommendations/{user_id}",
            "/api/v1/stats",
            "/api/v1/cache/stats",
            "/api/v1/cache/health",
            "/api/v1/binance/test",
            "/api/v1/bybit/test"
        ]
    }

@app.get("/api/v1/health")
async def api_health_check():
    """Health check endpoint для API (РОЗДІЛ 3.1)."""
    # Перевіряємо стан бази даних
    db_health = await get_database_health()
    
    # Перевіряємо стан кешу
    cache_health = await cache_manager.health_check()
    
    # Визначаємо загальний статус
    overall_status = "healthy"
    if db_health["status"] != "healthy":
        overall_status = "unhealthy"
    elif cache_health["status"] == "unhealthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "service": "yield-data-service",
        "version": __version__,
        "api_version": "v1",
        "database": db_health,
        "cache": cache_health,
        "endpoints_available": [
            "/api/v1/yield/{symbol}",
            "/api/v1/top",
            "/api/v1/exchanges",
            "/api/v1/exchanges/list",
            "/api/v1/stats"
        ]
    }

@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus метрики (native формат). Використовується Prometheus для scraping.
    """
    try:
        return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"❌ Помилка генерації Prometheus метрик: {e}")
        return Response(content=f"# Error generating metrics: {str(e)}\n", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    logger.info("Запуск EarnAggregator Data Service...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
