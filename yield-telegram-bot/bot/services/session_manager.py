"""
Менеджер сесій для групування дій користувачів.
"""
import uuid
from typing import Optional
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError
from bot.config import settings
from bot.utils.logger import logger


class SessionManager:
    """Управління сесіями користувачів."""

    SESSION_TTL = 1800  # 30 хвилин

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Ініціалізація Redis клієнта."""
        if self.redis:
            logger.debug("SessionManager вже ініціалізований")
            return

        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Перевірка з'єднання
            await self.redis.ping()
            logger.info("✅ SessionManager ініціалізовано")
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації SessionManager: {e}")
            raise

    async def is_available(self) -> bool:
        """Перевірити чи SessionManager готовий до роботи."""
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def get_or_create_session(self, user_id: int) -> str:
        """
        Отримати існуючу сесію або створити нову.

        Args:
            user_id: Telegram ID користувача

        Returns:
            UUID сесії
        """
        # Валідація user_id
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"❌ Неправильний user_id для сесії: {user_id}")
            return str(uuid.uuid4())

        # Перевірка ініціалізації Redis
        if not self.redis:
            logger.warning("⚠️ SessionManager не ініціалізований, використовую fallback для user {user_id}")
            return str(uuid.uuid4())

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

        except RedisConnectionError as e:
            logger.warning(f"⚠️ Redis недоступний для user {user_id}: {e}")
            return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"❌ Неочікувана помилка в get_or_create_session для user {user_id}: {e}", exc_info=True)
            # Fallback - генеруємо UUID без збереження в Redis
            return str(uuid.uuid4())

    async def close(self):
        """Закрити з'єднання з Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("🛑 SessionManager закрито")


# Глобальний екземпляр session manager
session_manager = SessionManager()

