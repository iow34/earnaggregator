"""
Підключення до PostgreSQL бази даних.

Цей модуль забезпечує:
- Стабільне підключення до PostgreSQL
- Connection pool для ефективності
- Retry логіку при втраті з'єднання
- Dependency injection для FastAPI endpoints
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
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
    """
    Менеджер підключення до бази даних.
    
    Забезпечує стабільне підключення з retry логікою
    та connection pooling.
    """
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._connection_retries = 3
        self._retry_delay = 1.0
        self._max_retry_delay = 30.0
        self._db_url = settings.database_url
        
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
                "server_settings": {
                    "application_name": "yield-data-service",
                    "timezone": "UTC"
                }
            }
        )
    
    async def initialize(self) -> bool:
        """
        Ініціалізує підключення до бази даних.
        
        Returns:
            bool: Чи успішно ініціалізовано
        """
        try:
            logger.info("🔌 Ініціалізація підключення до PostgreSQL...")
            
            # Створюємо основний engine
            self.engine = await self._create_engine(self._db_url)
            self._setup_event_listeners()
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            success, error = await self._test_connection()
            if not success:
                if error and "nodename nor servname" in str(error):
                    logger.warning("⚠️ Не вдалося підключитися до 'postgres'. Пробуємо fallback на 127.0.0.1")
                    fallback_url = str(make_url(self._db_url).set(host="127.0.0.1"))
                    # Закриваємо попередній engine
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
                        autocommit=False
                    )
                    success, error = await self._test_connection()
                    if success:
                        self._db_url = fallback_url
                        settings.database_url = fallback_url
                        logger.info("✅ Використовується fallback підключення до PostgreSQL через 127.0.0.1")
                    else:
                        logger.error("❌ Не вдалося підключитися до БД навіть через fallback")
                        return False
                else:
                    logger.error(f"❌ Помилка ініціалізації підключення до БД: {error}")
                    return False
            
            logger.info("✅ Підключення до PostgreSQL успішно ініціалізовано")
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації підключення до БД: {e}")
            return False
    
    def _setup_event_listeners(self):
        """Налаштовує event listeners для моніторингу з'єднань."""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Налаштування при підключенні."""
            logger.debug("🔗 Нове з'єднання з PostgreSQL створено")
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Моніторинг checkout з'єднання."""
            logger.debug("📤 З'єднання взято з pool")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Моніторинг checkin з'єднання."""
            logger.debug("📥 З'єднання повернуто в pool")
    
    async def _test_connection(self) -> tuple[bool, Optional[Exception]]:
        """
        Тестує підключення до бази даних.
        
        Returns:
            tuple: (успіх, помилка)
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("✅ Тест підключення до PostgreSQL пройшов успішно")
                    return True, None
                else:
                    err = RuntimeError("Unexpected response from database during test")
                    logger.error(f"❌ Тест підключення до PostgreSQL не пройшов: {err}")
                    return False, err
        except Exception as e:
            logger.error(f"❌ Помилка тесту підключення: {e}")
            return False, e
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Отримує сесію бази даних з retry логікою.
        
        Yields:
            AsyncSession: Сесія бази даних
        """
        if not self.session_factory:
            raise RuntimeError("Database не ініціалізовано. Викличте initialize() спочатку.")
        
        session = None
        for attempt in range(self._connection_retries):
            try:
                session = self.session_factory()
                # Тестуємо з'єднання
                await session.execute(text("SELECT 1"))
                break
                
            except (DisconnectionError, OperationalError) as e:
                logger.warning(f"⚠️ Помилка з'єднання (спроба {attempt + 1}/{self._connection_retries}): {e}")
                
                if session:
                    await session.close()
                
                if attempt < self._connection_retries - 1:
                    delay = min(self._retry_delay * (2 ** attempt), self._max_retry_delay)
                    logger.info(f"🔄 Повторна спроба через {delay} секунд...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("❌ Не вдалося підключитися до БД після всіх спроб")
                    raise
        
        try:
            yield session
        finally:
            if session:
                await session.close()
    
    async def health_check(self) -> dict:
        """
        Перевіряє стан підключення до БД.
        
        Returns:
            dict: Стан підключення
        """
        try:
            # Перевіряємо чи БД ініціалізована
            if not self.session_factory or not self.engine:
                return {
                    "status": "unhealthy",
                    "error": "Database не ініціалізовано. Викличте initialize() спочатку.",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            
            start_time = time.time()
            
            async with self.get_session() as session:
                # Простий запит для перевірки
                result = await session.execute(text("SELECT NOW()"))
                db_time = result.fetchone()[0]
                
                response_time = time.time() - start_time
                
                # Перевіряємо pool статистику
                pool = self.engine.pool
                try:
                    pool_status = {
                        "size": getattr(pool, 'size', lambda: 0)(),
                        "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
                        "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
                        "overflow": getattr(pool, 'overflow', lambda: 0)(),
                        "invalid": getattr(pool, 'invalid', lambda: 0)(),
                        "pool_type": pool.__class__.__name__
                    }
                except Exception as pool_error:
                    # NullPool може не мати всіх методів
                    pool_status = {
                        "pool_type": pool.__class__.__name__,
                        "note": f"Pool stats not available: {pool_error}"
                    }
                
                return {
                    "status": "healthy",
                    "database_time": db_time.isoformat(),
                    "response_time_ms": round(response_time * 1000, 2),
                    "pool_status": pool_status,
                    "timestamp": datetime.now(UTC).isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Health check не пройшов: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
    
    async def close(self):
        """Закриває всі з'єднання з БД."""
        if self.engine:
            logger.info("🔌 Закриття з'єднань з PostgreSQL...")
            await self.engine.dispose()
            logger.info("✅ З'єднання з PostgreSQL закрито")


# Глобальний екземпляр менеджера БД
db_manager = DatabaseManager()


# =============================================================================
# DEPENDENCY INJECTION FOR FASTAPI
# =============================================================================

@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI endpoints.
    
    Надає сесію бази даних з автоматичним управлінням життєвим циклом.
    
    Yields:
        AsyncSession: Сесія бази даних
    """
    # Перевіряємо чи БД ініціалізована; якщо ні — намагаємось ініціалізувати ліниво
    if not db_manager.session_factory or not db_manager.engine:
        logger.warning("⚠️ Database не ініціалізовано в get_database_session — виконуємо lazy init")
        ok = await init_database()
        if ok:
            try:
                await create_tables()
            except Exception as e:
                logger.warning(f"⚠️ Створення таблиць пропущено або вже створені: {e}")
        else:
            logger.error("❌ Неможливо ініціалізувати Database у get_database_session")
            raise RuntimeError("Database не ініціалізовано. Перевірте підключення до БД.")
    
    async with db_manager.get_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"❌ Помилка в database session: {e}")
            if session:
                await session.rollback()
            raise
        finally:
            # Session автоматично закривається в get_session()
            pass


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для транзакцій.
    
    Автоматично комітить або робить rollback.
    
    Yields:
        AsyncSession: Сесія в транзакції
    """
    if not db_manager.session_factory or not db_manager.engine:
        logger.warning("⚠️ Database не ініціалізовано в get_db_transaction — виконуємо lazy init")
        ok = await init_database()
        if ok:
            try:
                await create_tables()
            except Exception as e:
                logger.warning(f"⚠️ Створення таблиць пропущено або вже створені: {e}")
        else:
            logger.error("❌ Неможливо ініціалізувати Database у get_db_transaction")
            raise RuntimeError("Database не ініціалізовано. Перевірте підключення до БД.")
    
    async with db_manager.get_session() as session:
        try:
            yield session
            await session.commit()
            logger.debug("✅ Транзакція успішно закомічена")
        except Exception as e:
            logger.error(f"❌ Помилка в транзакції: {e}")
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для read-only операцій.
    
    Оптимізований для читання даних.
    
    Yields:
        AsyncSession: Read-only сесія
    """
    if not db_manager.session_factory or not db_manager.engine:
        logger.warning("⚠️ Database не ініціалізовано в get_db_readonly — виконуємо lazy init")
        ok = await init_database()
        if ok:
            try:
                await create_tables()
            except Exception as e:
                logger.warning(f"⚠️ Створення таблиць пропущено або вже створені: {e}")
        else:
            logger.error("❌ Неможливо ініціалізувати Database у get_db_readonly")
            raise RuntimeError("Database не ініціалізовано. Перевірте підключення до БД.")
    
    async with db_manager.get_session() as session:
        # Встановлюємо read-only режим
        await session.execute(text("SET TRANSACTION READ ONLY"))
        try:
            yield session
        finally:
            # Read-only транзакції не потребують commit
            pass


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def init_database() -> bool:
    """
    Ініціалізує підключення до бази даних.
    
    Returns:
        bool: Чи успішно ініціалізовано
    """
    return await db_manager.initialize()


async def close_database():
    """Закриває підключення до бази даних."""
    await db_manager.close()


async def close_engine(engine: Optional[AsyncEngine] = None):
    if engine:
        await engine.dispose()


async def get_database_health() -> dict:
    """
    Отримує стан підключення до БД.
    
    Returns:
        dict: Стан підключення
    """
    try:
        return await db_manager.health_check()
    except Exception as e:
        logger.error(f"❌ Помилка перевірки стану БД: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat()
        }


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

async def create_tables():
    """
    Створює таблиці в базі даних.
    
    Використовується для ініціалізації БД.
    """
    try:
        from app.db.models import Base
        
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Таблиці в базі даних створено/оновлено")
        
    except Exception as e:
        # Перевіряємо чи помилка пов'язана з існуючими об'єктами
        if "already exists" in str(e) or "DuplicateTableError" in str(e):
            logger.info("ℹ️ Таблиці/індекси вже існують, продовжуємо")
        else:
            logger.error(f"❌ Помилка створення таблиць: {e}")
            raise


async def drop_tables():
    """
    Видаляє всі таблиці з бази даних.
    
    ⚠️ УВАГА: Використовуйте тільки для тестування!
    """
    try:
        from app.db.models import Base
        
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("⚠️ Всі таблиці з бази даних видалено")
        
    except Exception as e:
        logger.error(f"❌ Помилка видалення таблиць: {e}")
        raise


# =============================================================================
# DATABASE MIGRATION HELPERS
# =============================================================================

async def get_database_version() -> Optional[str]:
    """
    Отримує версію бази даних.
    
    Returns:
        Optional[str]: Версія БД або None
    """
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            return version
    except Exception as e:
        logger.error(f"❌ Помилка отримання версії БД: {e}")
        return None


async def get_database_size() -> Optional[int]:
    """
    Отримує розмір бази даних в байтах.
    
    Returns:
        Optional[int]: Розмір БД або None
    """
    try:
        async with db_manager.get_session() as session:
            result = await session.execute(text("""
                SELECT pg_database_size(current_database())
            """))
            size_bytes = result.fetchone()[0]
            return size_bytes
    except Exception as e:
        logger.error(f"❌ Помилка отримання розміру БД: {e}")
        return None


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

async def startup_database():
    """Запускається при старті додатку."""
    logger.info("🚀 Ініціалізація бази даних при старті...")
    
    success = await init_database()
    if not success:
        raise RuntimeError("Не вдалося ініціалізувати підключення до БД")
    
    # Створюємо таблиці якщо потрібно
    try:
        await create_tables()
        logger.info("✅ Таблиці перевірено/створено")
    except Exception as e:
        logger.warning(f"⚠️ Не вдалося створити таблиці (можливо вже існують): {e}")
    
    logger.info("✅ База даних готова до роботи")


async def shutdown_database():
    """Запускається при зупинці додатку."""
    logger.info("🛑 Закриття підключення до БД...")
    await close_database()
    logger.info("✅ Підключення до БД закрито")
