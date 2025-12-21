"""
Клієнт для взаємодії з Data Service tracking API.

Надає методи для:
- Реєстрації користувачів через deep link
- Отримання tracking інформації
- Генерації реферальних посилань
"""

import asyncio
import time
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
        try:
            self.base_url = base_url or settings.data_service_url
            self.timeout = getattr(settings, 'REQUEST_TIMEOUT', 30.0) or 30.0
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації TrackingClient: {e}")
            # Fallback URL для забезпечення роботи навіть при проблемах з конфігурацією
            self.base_url = "https://go-to-the-exchange.up.railway.app"
            self.timeout = 30.0

        self._tracking_enabled = True  # Початково ввімкнений
        self._consecutive_failures = 0
        self._last_failure_time = None  # Для auto-recovery
    
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
        # Валідація telegram_id
        if not isinstance(telegram_id, int) or telegram_id <= 0:
            logger.error(f"❌ Неправильний telegram_id для реєстрації: {telegram_id}")
            return None

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
                    # Успішна відповідь - скидаємо лічильник помилок
                    self._consecutive_failures = 0
                    data = response.json()
                    logger.info(
                        f"✅ Користувач зареєстровано: {telegram_id}, "
                        f"uuid={data.get('user_uuid')}, source={data.get('acquisition_source')}"
                    )
                    return data
                else:
                    logger.warning(
                        f"⚠️ Помилка реєстрації користувача {telegram_id}: "
                        f"status={response.status_code}, body={response.text[:200]}"
                    )
                    self._handle_api_error()

                    return None

        except httpx.ConnectError as e:
            logger.warning(f"⚠️ Неможливо підключитися до tracking API: {e}")
            # Не збільшуємо лічильник помилок для ConnectError - це може бути тимчасова проблема
            return None
        except httpx.TimeoutException as e:
            logger.warning(f"⚠️ Таймаут tracking API: {e}")
            self._handle_api_error()
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️ HTTP помилка tracking API: {e}")
            self._handle_api_error()
            return None
        except Exception as e:
            logger.warning(f"⚠️ Інша помилка tracking API: {e}")
            self._handle_api_error()
            return None

    def _handle_api_error(self):
        """Обробка помилок API з логікою auto-recovery."""
        import time
        current_time = time.time()

        self._consecutive_failures += 1
        self._last_failure_time = current_time

        # Збільшуємо поріг до 5 помилок замість 3
        if self._consecutive_failures >= 5:
            logger.error(f"❌ Tracking API недоступний ({self._consecutive_failures} помилок), вимикаємо tracking")
            self._tracking_enabled = False
            # Auto-recovery через 5 хвилин
            self._schedule_auto_recovery()

    def _schedule_auto_recovery(self):
        """Запланувати автоматичне відновлення tracking через 5 хвилин."""
        import asyncio
        import time

        async def recover_tracking():
            await asyncio.sleep(300)  # 5 хвилин
            logger.info("🔄 Автоматичне відновлення tracking після 5 хвилин")
            self._tracking_enabled = True
            self._consecutive_failures = 0
            self._last_failure_time = None

        # Запускаємо задачу відновлення
        asyncio.create_task(recover_tracking())

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

    async def check_api_availability(self) -> bool:
        """
        Перевірити чи API доступний.

        Returns:
            bool: True якщо API доступний
        """
        try:
            # Використовуємо короткий таймаут для швидкої перевірки
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    logger.debug("✅ Tracking API доступний")
                    return True
                else:
                    logger.warning(f"⚠️ Tracking API повернув статус {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"⚠️ Неможливо перевірити доступність tracking API: {e}")
            return False

    def reset_tracking_status(self):
        """Скинути статус tracking (для тестування)."""
        self._tracking_enabled = True
        self._consecutive_failures = 0
        self._last_failure_time = None


# Глобальний екземпляр
tracking_client = TrackingClient()

