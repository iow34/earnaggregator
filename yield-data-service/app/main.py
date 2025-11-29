"""
EarnAggregator Data Service - FastAPI Application

Головний модуль FastAPI додатку для агрегації даних про Yield продукти.
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
from app.api.migrations_routes import router as migrations_router
from app.services.cache import cache_manager
from app.middleware.metrics import PrometheusHTTPMetricsMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.services.scheduler import start_scheduler_async, stop_scheduler, data_scheduler
from app.services.exchanges import exchange_registry
from app.config import settings
from app.__version__ import __version__


# Безпечний імпорт версії
try:
    from app.__version__ import __version__
except (ImportError, AttributeError):
    __version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan контекст для FastAPI - управління життєвим циклом додатку.
    
    При старті:
    - Ініціалізує підключення до БД
    - Ініціалізує кеш
    - Запускає scheduler
    
    При завершенні:
    - Зупиняє scheduler
    - Закриває підключення до БД
    """
    # Startup
    try:
        logger.info("🚀 Запуск EarnAggregator Data Service...")
        logger.info(f"📦 Версія: {__version__}")
        
        # Ініціалізуємо БД
        db_success = await startup_database()
        if not db_success:
            logger.error("❌ Не вдалося ініціалізувати підключення до БД")
            # Не зупиняємо додаток, але логуємо помилку
        
        # Ініціалізуємо кеш
        try:
            await cache_manager.initialize()
            logger.info("✅ Redis кеш ініціалізовано")
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося ініціалізувати Redis кеш: {e}")
            logger.warning("⚠️ Продовжуємо роботу без кешу")
        
        # Ініціалізуємо реєстр бірж
        await exchange_registry.initialize()
        logger.info("✅ Реєстр бірж ініціалізовано")
        
        # Запускаємо scheduler
        try:
            await start_scheduler_async()
            logger.info("✅ Scheduler запущено")
        except Exception as e:
            logger.error(f"❌ Помилка запуску scheduler: {e}")
        
        logger.info("✅ EarnAggregator Data Service запущено успішно")
        
    except Exception as e:
        logger.error(f"❌ Критична помилка при старті: {e}")
        # Не зупиняємо додаток, але логуємо помилку
    
    yield
    
    # Shutdown
    try:
        logger.info("🛑 Зупинка EarnAggregator Data Service...")
        
        # Зупиняємо scheduler
        try:
            stop_scheduler()
            logger.info("✅ Scheduler зупинено")
        except Exception as e:
            logger.error(f"❌ Помилка зупинки scheduler: {e}")
        
        # Закриваємо підключення до БД
        try:
            await shutdown_database()
            logger.info("✅ Підключення до БД закрито")
        except Exception as e:
            logger.error(f"❌ Помилка закриття підключення до БД: {e}")
        
        # Закриваємо кеш
        try:
            await cache_manager.close()
            logger.info("✅ Redis кеш закрито")
        except Exception as e:
            logger.warning(f"⚠️ Помилка закриття Redis кешу: {e}")
        
        logger.info("✅ EarnAggregator Data Service зупинено")
        
    except Exception as e:
        logger.error(f"❌ Помилка при зупинці: {e}")


# Створюємо FastAPI додаток
app = FastAPI(
    title="EarnAggregator Data Service",
    description="API для агрегації даних про Yield продукти з криптовалютних бірж",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production обмежити до конкретних доменів
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware
app.add_middleware(PrometheusHTTPMetricsMiddleware)

# Rate limiter middleware (тільки якщо REDIS_URL налаштовано)
if settings.redis_url:
    app.add_middleware(RateLimiterMiddleware, redis_url=settings.redis_url)
else:
    logger.warning("⚠️ REDIS_URL не налаштовано, rate limiting вимкнено")


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint - інформація про API.
    """
    try:
        version = __version__
    except (NameError, AttributeError):
        version = "1.0.0"
    
    return {
        "name": "EarnAggregator Data Service",
        "version": version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# Health check endpoint
@app.get("/health")
async def health():
    """
    Health check endpoint для моніторингу.
    """
    db_health = await get_database_health()
    try:
        version = __version__
    except (NameError, AttributeError):
        version = "1.0.0"
    
    return {
        "status": "healthy" if db_health.get("connected") else "degraded",
        "version": version,
        "database": db_health
    }


# Підключаємо роутери
# Примітка: api_router вже має prefix="/api/v1" в routes.py, тому не додаємо prefix тут
app.include_router(api_router, tags=["api"])
app.include_router(tracking_router, prefix="/tracking", tags=["tracking"])
app.include_router(redirect_router, prefix="/ref", tags=["redirect"])
app.include_router(migrations_router, tags=["migrations"])


# API Health check endpoint (додатковий до основного /health)
@app.get("/api/v1/health")
async def api_health_check():
    """Health check endpoint для API (РОЗДІЛ 3.1)."""
    # Перевіряємо стан бази даних
    db_health = await get_database_health()
    
    # Перевіряємо стан кешу
    cache_health = await cache_manager.health_check()
    
    # Визначаємо загальний статус
    overall_status = "healthy"
    if db_health.get("status") != "healthy" or not db_health.get("connected"):
        overall_status = "unhealthy"
    elif cache_health.get("status") == "unhealthy":
        overall_status = "degraded"
    
    try:
        version = __version__
    except (NameError, AttributeError):
        version = "1.0.0"
    
    return {
        "status": overall_status,
        "service": "yield-data-service",
        "version": version,
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


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    try:
        return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"❌ Помилка генерації Prometheus метрик: {e}")
        return Response(content=f"# Error generating metrics: {str(e)}\n", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    logger.info("Запуск EarnAggregator Data Service...")
    
    # Railway надає PORT через змінну середовища
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("ENVIRONMENT", "production") != "production"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
