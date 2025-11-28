"""
Конфігурація бази даних для Telegram бота.

Використовує SQLAlchemy 2.0 async з asyncpg драйвером.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy import text

from bot.config import settings
from bot.db.models import Base
from bot.utils.logger import logger


class DatabaseManager:
    """Менеджер бази даних для бота."""

    def __init__(self, db_url: Optional[str] = None):
        # Railway надає DATABASE_URL в форматі postgresql://, але потрібен postgresql+asyncpg://
        raw_url = db_url or settings.DATABASE_URL
        self._db_url = self._normalize_database_url(raw_url)
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def _normalize_database_url(self, url: str) -> str:
        """
        Нормалізує DATABASE_URL для підтримки Railway формату.
        
        Railway надає: postgresql://user:pass@host:port/db
        Потрібно: postgresql+asyncpg://user:pass@host:port/db
        """
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            logger.debug(f"🔄 Нормалізовано DATABASE_URL для asyncpg: {url[:50]}...")
        return url

    async def initialize(self) -> bool:
        """Ініціалізація з'єднання з БД."""
        try:
            logger.info(f"Підключення до БД: {self._db_url.replace('postgresql+asyncpg://', 'postgresql://')}")

            self.engine = create_async_engine(
                self._db_url,
                echo=False,  # Вимкнути SQL логи в продакшні
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )

            # Тест підключення
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Створюємо фабрику сесій
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )

            logger.info("✅ БД успішно ініціалізована")
            return True

        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації БД: {e}")
            await self.close_engine()
            return False

    async def close_engine(self) -> None:
        """Закриття з'єднання з БД."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Отримати сесію БД."""
        if not self.session_factory:
            raise RuntimeError("Database не ініціалізована")

        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Помилка в сесії БД: {e}")
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """Отримати сесію з транзакцією."""
        async with self.get_session() as session:
            async with session.begin():
                yield session

    async def health_check(self) -> dict:
        """Перевірка здоров'я БД."""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "version": version,
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Глобальний менеджер БД
db_manager = DatabaseManager()


async def init_database() -> bool:
    """Ініціалізація БД для бота."""
    return await db_manager.initialize()


async def shutdown_database() -> None:
    """Закриття БД."""
    await db_manager.close_engine()


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI-like ін'єкції сесії."""
    async with db_manager.get_session() as session:
        yield session


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для транзакцій."""
    async with db_manager.get_transaction() as session:
        yield session


async def get_database_health() -> dict:
    """Отримати статус здоров'я БД."""
    return await db_manager.health_check()


async def create_tables() -> None:
    """
    Створити всі таблиці якщо вони не існують.
    
    ВАЖЛИВО: НЕ видаляє існуючі таблиці для збереження даних користувачів!
    Для міграцій схеми використовуйте Alembic або ручні ALTER TABLE.
    """
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            # Створюємо таблиці тільки якщо їх немає (IF NOT EXISTS)
            # Base.metadata.create_all створює таблиці тільки якщо вони не існують
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблиці перевірені/створені успішно")


async def recreate_tables_dev_only() -> None:
    """
    ТІЛЬКИ ДЛЯ РОЗРОБКИ: Видалити та створити таблиці заново.
    
    ⚠️ УВАГА: Видаляє всі дані! Використовуйте тільки в development mode!
    Ніколи не викликайте цю функцію в production!
    """
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            # Видаляємо таблиці в порядку залежностей (foreign keys)
            await conn.execute(text("DROP TABLE IF EXISTS user_actions CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS referral_clicks CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS user_queries CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS telegram_users CASCADE"))
            logger.warning("🗑️ [DEV ONLY] Таблиці видалені")
            
            # Створюємо таблиці заново
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ [DEV ONLY] Таблиці створені заново")


async def check_tables_exist() -> dict:
    """
    Перевірити які таблиці існують у БД.
    
    Returns:
        dict: Інформація про існуючі таблиці
    """
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            return {
                "exists": len(tables) > 0,
                "tables": tables,
                "count": len(tables)
            }
    return {"exists": False, "tables": [], "count": 0}
