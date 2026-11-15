import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy import text

from bot.config import settings
from bot.db.models import Base
from bot.utils.logger import logger


class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None):

        raw_url = db_url or settings.DATABASE_URL
        self._db_url = self._normalize_database_url(raw_url)
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def _normalize_database_url(self, url: str) -> str:
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            logger.info("Database/cache connection configured")
        return url

    async def initialize(self) -> bool:
        try:
            logger.info("Database/cache connection configured")

            self.engine = create_async_engine(
                self._db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )

            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

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
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
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
        async with self.get_session() as session:
            async with session.begin():
                yield session

    async def health_check(self) -> dict:
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


db_manager = DatabaseManager()


async def init_database() -> bool:
    return await db_manager.initialize()


async def shutdown_database() -> None:
    await db_manager.close_engine()


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.get_session() as session:
        yield session


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.get_transaction() as session:
        yield session


async def get_database_health() -> dict:
    return await db_manager.health_check()


async def create_tables() -> None:
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблиці перевірені/створені успішно")


async def recreate_tables_dev_only() -> None:
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS user_actions CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS referral_clicks CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS user_queries CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS telegram_users CASCADE"))
            logger.warning("🗑️ [DEV ONLY] Таблиці видалені")

            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ [DEV ONLY] Таблиці створені заново")


async def check_tables_exist() -> dict:
    if db_manager.engine:
        async with db_manager.engine.begin() as conn:
            result = await conn.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            return {"exists": len(tables) > 0, "tables": tables, "count": len(tables)}
    return {"exists": False, "tables": [], "count": 0}
