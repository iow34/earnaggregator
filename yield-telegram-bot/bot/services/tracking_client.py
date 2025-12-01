"""
Клієнт для взаємодії з Data Service tracking API.

Надає методи для:
- Реєстрації користувачів через deep link
- Отримання tracking інформації
- Генерації реферальних посилань
"""

import httpx
from typing import Optional, Dict, Any
from bot.config import settings
from bot.utils.logger import logger


class TrackingClient:
    """Клієнт для tracking API."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Ініціалізація клієнта.
        
        Args:
            base_url: URL Data Service (за замовчуванням з settings)
        """
        self.base_url = base_url or settings.data_service_url
        self.timeout = settings.REQUEST_TIMEOUT
        self._tracking_enabled = True  # Початково ввімкнений
        self._consecutive_failures = 0
    
    async def register_user(
        self,
        telegram_id: int,
        payload: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Зареєструвати користувача через deep link.
        
        Args:
            telegram_id: Telegram ID користувача
            payload: Deep link payload
            username: Telegram username
            first_name: Ім'я
            last_name: Прізвище
            
        Returns:
            Дані користувача (uuid, source) або None при помилці
        """
        # Якщо tracking вимкнений, просто повертаємо None
        if not getattr(self, '_tracking_enabled', True):
            logger.debug(f"📊 Tracking вимкнений, пропускаємо реєстрацію user {telegram_id}")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tracking/user/register",
                    json={
                        "telegram_id": telegram_id,
                        "payload": payload,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        f"✅ Користувач зареєстровано: {telegram_id}, "
                        f"uuid={data.get('user_uuid')}, source={data.get('acquisition_source')}"
                    )
                    return data
                else:
                    logger.warning(
                        f"⚠️ Помилка реєстрації користувача {telegram_id}: "
                        f"status={response.status_code}"
                    )
                    self._consecutive_failures += 1

                    # Якщо багато послідовних помилок, вимикаємо tracking
                    if self._consecutive_failures >= 3:
                        logger.error(f"❌ Tracking API недоступний ({self._consecutive_failures} помилок), вимикаємо tracking")
                        self._tracking_enabled = False

                    return None
                    
        except Exception as e:
            logger.warning(f"⚠️ Помилка з'єднання з tracking API: {e}")
            self._consecutive_failures += 1

            # Якщо багато послідовних помилок, вимикаємо tracking
            if self._consecutive_failures >= 3:
                logger.error(f"❌ Tracking API недоступний ({self._consecutive_failures} помилок), вимикаємо tracking")
                self._tracking_enabled = False

            return None
    
    async def get_user_info(
        self,
        telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Отримати tracking інформацію користувача.
        
        Args:
            telegram_id: Telegram ID користувача
            
        Returns:
            Дані користувача або None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/tracking/user/{telegram_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # Користувач не знайдений - це нормально
                    return None
                else:
                    logger.error(
                        f"❌ Помилка отримання користувача {telegram_id}: "
                        f"status={response.status_code}"
                    )
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Помилка виклику tracking API (get_user): {e}")
            return None

    def is_tracking_enabled(self) -> bool:
        """Перевірити чи tracking увімкнений."""
        return self._tracking_enabled

    def reset_tracking_status(self):
        """Скинути статус tracking (для тестування)."""
        self._tracking_enabled = True
        self._consecutive_failures = 0


# Глобальний екземпляр
tracking_client = TrackingClient()

