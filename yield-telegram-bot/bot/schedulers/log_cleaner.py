"""
Scheduler для очистки старих логів трекінгу.
"""
import asyncio
from datetime import datetime, timedelta, UTC
from sqlalchemy import delete
from bot.config import settings
from bot.utils.logger import logger
from bot.db.database import get_database_session
from bot.db.models import UserAction


class LogCleaner:
    """Очищення старих логів трекінгу."""

    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        """Запустити scheduler."""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info("🚀 Log cleaner запущений")

    async def stop(self):
        """Зупинити scheduler."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Log cleaner зупинений")

    async def _cleanup_loop(self):
        """Цикл очистки (раз на добу)."""
        while self.running:
            try:
                await self._cleanup_old_logs()
                # Чекати 24 години
                await asyncio.sleep(86400)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Помилка в log cleaner: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Повторити через годину

    async def _cleanup_old_logs(self):
        """Видалити логи старші за retention period."""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(
                days=settings.TRACKING_LOG_RETENTION_DAYS
            )

            async with get_database_session() as session:
                stmt = delete(UserAction).where(
                    UserAction.timestamp < cutoff_date
                )
                result = await session.execute(stmt)
                await session.commit()

                deleted_count = result.rowcount
                logger.info(
                    f"🧹 Видалено {deleted_count} старих записів трекінгу "
                    f"(старіше {settings.TRACKING_LOG_RETENTION_DAYS} днів)"
                )

        except Exception as e:
            logger.error(f"❌ Помилка очистки логів: {e}", exc_info=True)


# Глобальний екземпляр log cleaner
log_cleaner = LogCleaner()

