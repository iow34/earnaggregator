"""
Pytest fixtures для tracking тестів.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.models import Base
from app.config import settings


@pytest.fixture
async def db_session():
    """
    Створити тестову сесію БД.
    
    Використовує окрему тестову БД або in-memory database.
    """
    # Використовуємо тестову БД з .env.test або створюємо in-memory
    test_db_url = settings.database_url
    
    # Створюємо engine для тестів
    engine = create_async_engine(
        test_db_url,
        poolclass=NullPool,
        echo=False
    )
    
    # Створюємо всі таблиці
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Створюємо session factory
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Надаємо сесію для тесту
    async with session_factory() as session:
        yield session
        await session.rollback()  # Rollback після тесту
    
    # Очищаємо після тестів
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

