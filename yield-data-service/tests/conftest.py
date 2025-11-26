"""
Pytest конфігурація та fixtures для тестування.

Цей файл містить:
- Налаштування pytest fixtures
- Створення тестової бази даних
- Налаштування тестового підключення до PostgreSQL
- Очищення БД після тестів
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from datetime import datetime, UTC

from app.db.database import DatabaseManager
from app.db.models import Base
from app.config import Settings


# Тестові налаштування
TEST_DATABASE_URL = "postgresql+asyncpg://yield_user:yield_secure_password_2024@localhost:5432/yield_db_test"

class TestSettings(Settings):
    """Тестові налаштування."""
    database_url: str = TEST_DATABASE_URL
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = None
    redis_db: int = 1  # Використовуємо іншу БД Redis для тестів
    log_level: str = "DEBUG"


@pytest.fixture(scope="session")
def event_loop():
    """Створює event loop для всіх тестів."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database_manager():
    """
    Fixture для тестового менеджера бази даних.
    
    Створює тестову БД та очищає її після тестів.
    """
    # Створюємо тестовий менеджер
    manager = DatabaseManager()
    manager.engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Відключаємо SQL логування для тестів
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    # Створюємо session_factory для глобального db_manager
    manager.session_factory = async_sessionmaker(
        bind=manager.engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False
    )
    
    # Створюємо таблиці
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield manager
    
    # Очищаємо після тестів
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await manager.close()


@pytest.fixture
async def test_db_session(test_database_manager) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture для тестової сесії бази даних.
    
    Надає чисту сесію для кожного тесту.
    """
    session_factory = async_sessionmaker(
        bind=test_database_manager.engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with session_factory() as session:
        # Починаємо транзакцію
        await session.begin()
        try:
            yield session
        finally:
            # Rollback після кожного тесту
            await session.rollback()
            await session.close()


@pytest.fixture
async def clean_database(test_db_session):
    """
    Fixture для очищення бази даних перед тестом.
    
    Видаляє всі дані з таблиць.
    """
    # Очищаємо всі таблиці
    tables = ["exchange_data", "cache_metadata", "user_analytics", "system_metrics", "api_logs", "yield_products"]
    
    for table in tables:
        try:
            await test_db_session.execute(text(f"DELETE FROM {table}"))
        except Exception:
            # Таблиця може не існувати
            pass
    
    await test_db_session.commit()
    yield
    # Очищення після тесту відбувається автоматично через rollback


@pytest.fixture
def test_settings():
    """Fixture для тестових налаштувань."""
    return TestSettings()


@pytest.fixture
def sample_yield_product_data():
    """Fixture з тестовими даними для Yield продукту."""
    return {
        "id": "test_binance_btc_1234567890",
        "symbol": "BTC",
        "name": "Bitcoin Flexible Savings",
        "provider": "Binance",
        "apy": 5.25,
        "is_cefi": True,
        "min_amount": 0.001,
        "max_amount": 100.0,
        "lock_period_days": 0,
        "max_apy": 6.0,
        "risk_level": "Medium",
        "is_active": True,
        "website_url": "https://www.binance.com/en/earn",
        "description": "Bitcoin Flexible Savings Product",
        "raw_data": {
            "productId": "BTC_FLEXIBLE",
            "annualPercentageRate": 0.0525
        }
    }


@pytest.fixture
def sample_exchange_data():
    """Fixture з тестовими даними для Exchange data."""
    return {
        "product_id": "test_binance_btc_1234567890",
        "exchange": "Binance",
        "raw_data": {
            "productId": "BTC_FLEXIBLE",
            "annualPercentageRate": 0.0525,
            "minPurchaseAmount": 0.001,
            "canPurchase": True
        },
        "api_endpoint": "/sapi/v1/simple-earn/flexible/list",
        "response_status": 200,
        "response_time_ms": 150
    }


@pytest.fixture
def sample_cache_metadata():
    """Fixture з тестовими даними для Cache metadata."""
    return {
        "cache_key": "yield:BTC",
        "cache_type": "yield",
        "expires_at": datetime.now(UTC).replace(microsecond=0),
        "data_size_bytes": 1024,
        "hit_count": 5,
        "miss_count": 2
    }


@pytest.fixture
def multiple_yield_products():
    """Fixture з кількома тестовими продуктами."""
    return [
        {
            "id": "test_binance_btc_1",
            "symbol": "BTC",
            "name": "Bitcoin Flexible Savings",
            "provider": "Binance",
            "apy": 5.25,
            "is_cefi": True,
            "min_amount": 0.001,
            "lock_period_days": 0,
            "is_active": True
        },
        {
            "id": "test_binance_eth_2",
            "symbol": "ETH",
            "name": "Ethereum Locked Savings",
            "provider": "Binance",
            "apy": 8.50,
            "is_cefi": True,
            "min_amount": 0.01,
            "lock_period_days": 90,
            "is_active": True
        },
        {
            "id": "test_bybit_btc_3",
            "symbol": "BTC",
            "name": "Bitcoin Easy Earn",
            "provider": "Bybit",
            "apy": 4.75,
            "is_cefi": True,
            "min_amount": 0.001,
            "lock_period_days": 0,
            "is_active": True
        },
        {
            "id": "test_bybit_eth_4",
            "symbol": "ETH",
            "name": "Ethereum OnChain Staking",
            "provider": "Bybit",
            "apy": 6.20,
            "is_cefi": False,
            "min_amount": 0.1,
            "lock_period_days": 0,
            "is_active": True
        }
    ]


# Утилітарні функції для тестів

async def create_test_product(session: AsyncSession, product_data: dict):
    """Створює тестовий продукт в БД."""
    from app.db.models import YieldProductDB
    
    db_product = YieldProductDB(**product_data)
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    return db_product


async def create_test_exchange_data(session: AsyncSession, exchange_data: dict):
    """Створює тестові exchange data в БД."""
    from app.db.models import ExchangeDataDB
    
    db_exchange = ExchangeDataDB(**exchange_data)
    session.add(db_exchange)
    await session.commit()
    await session.refresh(db_exchange)
    return db_exchange


async def create_test_cache_metadata(session: AsyncSession, cache_data: dict):
    """Створює тестові cache metadata в БД."""
    from app.db.models import CacheMetadataDB
    
    db_cache = CacheMetadataDB(**cache_data)
    session.add(db_cache)
    await session.commit()
    await session.refresh(db_cache)
    return db_cache


# Маркери для тестів
pytestmark = pytest.mark.asyncio
