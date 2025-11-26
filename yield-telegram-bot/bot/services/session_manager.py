"""
Менеджер сесій для групування дій користувачів.
"""
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional
import redis.asyncio as redis
from bot.config import settings
from bot.utils.logger import logger


class SessionManager:
    """Управління сесіями користувачів."""

    SESSION_TTL = 1800  # 30 хвилин

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Ініціалізація Redis клієнта."""
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Перевірка з'єднання
            await self.redis.ping()
            logger.info("✅ SessionManager ініціалізовано")
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації SessionManager: {e}")
            raise

    async def get_or_create_session(self, user_id: int) -> str:
        """
        Отримати існуючу сесію або створити нову.

        Args:
            user_id: Telegram ID користувача

        Returns:
            UUID сесії
        """
        key = f"session:{user_id}"

        try:
            # Спроба отримати існуючу сесію
            session_id = await self.redis.get(key)

            if session_id:
                # Продовжити TTL сесії
                await self.redis.expire(key, self.SESSION_TTL)
                return session_id

            # Створити нову сесію
            new_session_id = str(uuid.uuid4())
            await self.redis.setex(key, self.SESSION_TTL, new_session_id)

            logger.info(f"🆕 Нова сесія створена: {new_session_id} для user {user_id}")
            return new_session_id

        except Exception as e:
            logger.error(f"❌ Помилка в get_or_create_session: {e}")
            # Fallback - генеруємо UUID без збереження в Redis
            return str(uuid.uuid4())

    async def close(self):
        """Закрити з'єднання з Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("🛑 SessionManager закрито")


# Глобальний екземпляр session manager
session_manager = SessionManager()

