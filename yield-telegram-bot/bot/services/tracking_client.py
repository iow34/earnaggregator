import asyncio
import time
import httpx
from typing import Optional, Dict, Any
from bot.config import settings
from bot.utils.logger import logger


class TrackingClient:
    def __init__(self, base_url: Optional[str] = None):
        try:
            self.base_url = base_url or settings.data_service_url
            self.timeout = getattr(settings, "REQUEST_TIMEOUT", 30.0) or 30.0
        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації TrackingClient: {e}")

            self.base_url = "http://localhost:8000"
            self.timeout = 30.0

        self._tracking_enabled = True
        self._consecutive_failures = 0
        self._last_failure_time = None

    async def register_user(
        self,
        telegram_id: int,
        payload: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(telegram_id, int) or telegram_id <= 0:
            logger.error(f"❌ Неправильний telegram_id для реєстрації: {telegram_id}")
            return None

        if not getattr(self, "_tracking_enabled", True):
            logger.debug(f"📊 Tracking вимкнений, пропускаємо реєстрацію user {telegram_id}")
            return None

        try:
            async with httpx.AsyncClient(
                headers={"X-Service-API-Key": settings.SERVICE_API_KEY}, timeout=self.timeout
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tracking/user/register",
                    json={
                        "telegram_id": telegram_id,
                        "payload": payload,
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                )

                if response.status_code == 200:
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
        import time

        current_time = time.time()

        self._consecutive_failures += 1
        self._last_failure_time = current_time

        if self._consecutive_failures >= 5:
            logger.error(
                f"❌ Tracking API недоступний ({self._consecutive_failures} помилок), вимикаємо tracking"
            )
            self._tracking_enabled = False

            self._schedule_auto_recovery()

    def _schedule_auto_recovery(self):
        import asyncio
        import time

        async def recover_tracking():
            await asyncio.sleep(300)
            logger.info("🔄 Автоматичне відновлення tracking після 5 хвилин")
            self._tracking_enabled = True
            self._consecutive_failures = 0
            self._last_failure_time = None

        asyncio.create_task(recover_tracking())

    async def get_user_info(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(
                headers={"X-Service-API-Key": settings.SERVICE_API_KEY}, timeout=self.timeout
            ) as client:
                response = await client.get(f"{self.base_url}/api/v1/tracking/user/{telegram_id}")

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
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
        return self._tracking_enabled

    async def check_api_availability(self) -> bool:
        try:
            async with httpx.AsyncClient(
                headers={"X-Service-API-Key": settings.SERVICE_API_KEY}, timeout=5.0
            ) as client:
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
        self._tracking_enabled = True
        self._consecutive_failures = 0
        self._last_failure_time = None


tracking_client = TrackingClient()
