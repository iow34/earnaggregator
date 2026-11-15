import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
import time
from datetime import datetime, UTC

from sqlalchemy.engine.url import make_url

from app.config import settings
from app.utils.logger import logger


class DatabaseManager:
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._connection_retries = 3
        self._retry_delay = 1.0
        self._max_retry_delay = 30.0

        self._db_url = self._normalize_database_url(settings.database_url)

    def _normalize_database_url(self, url: str) -> str:
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            logger.info("Database/cache connection configured")
        return url

    async def _create_engine(self, url: str) -> AsyncEngine:
        return create_async_engine(
            url,
            poolclass=NullPool,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            echo_pool=False,
            connect_args={
                "command_timeout": 30,
                "server_settings": {"application_name": "yield-data-service", "timezone": "UTC"},
            },
        )

    async def initialize(self) -> bool:
        try:
            logger.info("🔌 Ініціалізація підключення до PostgreSQL...")

            self.engine = await self._create_engine(self._db_url)
            self._setup_event_listeners()
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )

            success, error = await self._test_connection()
            if not success:
                if error and "nodename nor servname" in str(error):
                    logger.warning(
                        "⚠️ Не вдалося підключитися до 'postgres'. Пробуємо fallback на 127.0.0.1"
                    )
                    fallback_url = str(make_url(self._db_url).set(host="127.0.0.1"))

                    if self.engine:
                        await self.engine.dispose()
                        self.engine = None
                    self.engine = await self._create_engine(fallback_url)
                    self._setup_event_listeners()
                    self.session_factory = async_sessionmaker(
                        bind=self.engine,
                        class_=AsyncSession,
                        expire_on_commit=False,
                        autoflush=True,
                        autocommit=False,
                    )
                    success, error = await self._test_connection()
                    if success:
                        self._db_url = fallback_url
                        settings.database_url = fallback_url
                        logger.info(
                            "✅ Використовується fallback підключення до PostgreSQL через 127.0.0.1"
                        )
                    else:
                        logger.error("❌ Не вдалося підключитися до БД навіть через fallback")
                        return False
                else:
                    logger.error(f"❌ Помилка ініціалізації підключення до БД: {error}")
                    return False

            logger.info("✅ Підключення до PostgreSQL успішно ініціалізовано")
            return True

        except Exception as e:
            logger.error(f"❌ Критична помилка ініціалізації БД: {e}")
            return False

    def _setup_event_listeners(self):
        if not self.engine:
            return

        @event.listens_for(self.engine.sync_engine, "connect")
        def set_connection_info(dbapi_conn, connection_record):
            logger.debug("🔗 Нове з'єднання з PostgreSQL створено")

    async def _test_connection(self) -> tuple[bool, Optional[Exception]]:
        if not self.engine:
            return False, Exception("Engine не ініціалізовано")

        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("✅ Тест підключення до PostgreSQL пройшов успішно")
                return True, None
        except Exception as err:
            logger.error(f"❌ Тест підключення до PostgreSQL не пройшов: {err}")
            return False, err

    async def close(self):
        if self.engine:
            logger.info("🔌 Закриття з'єднань з PostgreSQL...")
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            logger.info("✅ З'єднання з PostgreSQL закрито")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            raise RuntimeError("Database не ініціалізовано. Викличте initialize() спочатку.")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> dict:
        if not self.engine:
            return {"status": "unhealthy", "connected": False, "error": "Engine не ініціалізовано"}

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    return {
                        "status": "healthy",
                        "connected": True,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "connected": False,
                        "error": "Неочікувана відповідь від БД",
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


db_manager = DatabaseManager()


async def startup_database() -> bool:
    return await db_manager.initialize()


async def shutdown_database():
    await db_manager.close()


async def get_database_health() -> dict:
    return await db_manager.health_check()


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.get_session() as session:
        yield session


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
