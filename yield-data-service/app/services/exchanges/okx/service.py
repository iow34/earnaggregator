"""
Сервіс для інтеграції з OKX Financial Product API.

Об'єднує логіку отримання даних з OKX API, нормалізації,
кешування та збереження в базу даних.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
import time

from ..base_service import BaseExchangeService
from .api import OKXAPI
from app.utils.logger import logger
from app.services.cache import cache_manager, get_exchange_cache_key
from app.utils.metrics import EXTERNAL_API_CALLS, observe_latency, AGGREGATION_LATENCY_SECONDS
from app.config import settings


class OKXService(BaseExchangeService):
    """
    Сервіс для роботи з OKX Financial Product API.

    Агрегує логіку отримання даних, нормалізації,
    збереження в БД та кешування для OKX.
    """

    def __init__(self):
        """Ініціалізує OKX сервіс."""
        super().__init__("okx", OKXAPI)
        self.cache_ttl = 3600  # 1 година для OKX продуктів

    async def initialize(self):
        """Ініціалізує OKX API клієнт з перевіркою конфігурації."""
        try:
            # Перевіряємо наявність всіх 3 параметрів OKX
            api_key = getattr(settings, 'okx_api_key', '')
            api_secret = getattr(settings, 'okx_api_secret', '')
            api_passphrase = getattr(settings, 'okx_api_passphrase', '')

            if not api_key or not api_secret or not api_passphrase:
                logger.warning("⚠️ OKX API ключі не повністю налаштовані")
                logger.warning(f"   API Key: {'✅' if api_key else '❌'}")
                logger.warning(f"   API Secret: {'✅' if api_secret else '❌'}")
                logger.warning(f"   API Passphrase: {'✅' if api_passphrase else '❌'}")

                # Створюємо клієнт з порожніми ключами - працюватиме в обмеженому режимі
                self.api_client = OKXAPI(api_key or "", api_secret or "", api_passphrase or "")
                self.is_configured = False
            else:
                # Створюємо повноцінний клієнт
                self.api_client = OKXAPI(api_key, api_secret, api_passphrase)
                self.is_configured = True
                logger.info("✅ OKX API клієнт ініціалізовано успішно")

        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації OKX сервісу: {e}")
            self.is_configured = False
            self.api_client = OKXAPI("", "", "")

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестує підключення до OKX API.

        Returns:
            Dict з результатами тестування
        """
        start_time = datetime.now(UTC)

        try:
            logger.info("🧪 Тестування підключення до OKX API...")

            if not self.is_configured:
                return {
                    "status": "error",
                    "message": "OKX API ключі не налаштовані (потрібні API Key, Secret та Passphrase)",
                    "configured": False,
                    "timestamp": datetime.now(UTC).isoformat()
                }

            # Тестуємо отримання невеликої кількості Simple Earn продуктів (не вимагають аутентифікації)
            simple_earn_products = await self.api_client.get_simple_earn_flexible_products()

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            # Підраховуємо продукти по типам
            simple_earn_count = len(simple_earn_products)

            return {
                "status": "success",
                "message": "Підключення до OKX API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "simple_earn_count": simple_earn_count,
                "onchain_count": 0,  # On-chain вимагають аутентифікації
                "total_products": simple_earn_count,
                "configured": True,
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            response_time = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"❌ Помилка підключення до OKX API: {e}")

            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "inactive",
                "configured": self.is_configured,
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти безпосередньо з OKX API.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            List нормалізованих продуктів
        """
        if not self.api_client:
            logger.error("❌ OKX API клієнт не ініціалізовано")
            return []

        try:
            start_time = time.perf_counter()

            if symbol:
                logger.info(f"🔄 OKX: отримання продуктів для {symbol}")
                products = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                logger.info("🔄 OKX: отримання всіх продуктів")
                products = await self.api_client.get_earn_products()

            # Метрики
            duration = time.perf_counter() - start_time
            AGGREGATION_LATENCY_SECONDS.observe(duration)

            if products:
                EXTERNAL_API_CALLS.labels(exchange="okx", status="success").inc()
                logger.info(f"✅ OKX: отримано {len(products)} продуктів за {duration:.3f}s")
            else:
                EXTERNAL_API_CALLS.labels(exchange="okx", status="error").inc()
                logger.warning("⚠️ OKX: не отримано продуктів з API")

            return products

        except Exception as e:
            EXTERNAL_API_CALLS.labels(exchange="okx", status="error").inc()
            logger.error(f"❌ Помилка отримання продуктів з OKX API: {e}")
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти OKX з кешуванням.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            List нормалізованих продуктів
        """
        cache_key = get_exchange_cache_key("okx", symbol)

        # Перевіряємо кеш
        cached_data = await cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 OKX продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        # Якщо в кеші немає - отримуємо з API
        logger.info(f"💾 Запит до OKX API для {symbol or 'всіх'} продуктів")
        try:
            products = await self.get_products_from_api(symbol)

            # Нормалізуємо дані
            normalized_products = await self._normalize_products(products)

            # Зберігаємо в кеш
            cache_data = {
                "products": normalized_products,
                "count": len(normalized_products),
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol,
                "source": "okx_api"
            }
            await cache_manager.set_cached_data(cache_key, cache_data, self.cache_ttl)

            logger.info(f"✅ Отримано {len(normalized_products)} продуктів з OKX API")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з OKX: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Нормалізує дані продуктів OKX до єдиного формату.

        Args:
            raw_products: Сирі дані з OKX API

        Returns:
            List нормалізованих продуктів
        """
        logger.info(f"🔄 OKX: нормалізую {len(raw_products)} сирих продуктів")
        normalized = []

        for product in raw_products:
            try:
                # Визначаємо тип продукту
                product_type = product.get("product_type", "")

                # Нормалізуємо APY (залишаємо як є, оскільки вже нормалізовано в API)
                apy_value = float(product.get("apy", 0))

                # Для On-chain продуктів - medium ризик, для Simple Earn - low
                risk_level = "Medium" if product_type == "OnChain" else "Low"

                # Конвертуємо can_early_redeem в правильний формат
                can_early_redeem = product.get("can_early_redeem", False)

                normalized_product = {
                    "id": product.get("id", ""),
                    "symbol": product.get("symbol", "").upper(),
                    "name": product.get("name", f"OKX {product.get('symbol', '')} Earn"),
                    "provider": "OKX",
                    "apy": apy_value,
                    "is_cefi": True,
                    "min_amount": float(product.get("min_amount", 0)),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": int(product.get("lock_period_days", 0)),
                    "max_apy": apy_value,  # OKX не має діапазону APY
                    "risk_level": risk_level,
                    "is_active": bool(product.get("is_active", True)),
                    "website_url": product.get("website_url", "https://www.okx.com/earn"),
                    "description": product.get("description", ""),
                    "raw_data": product,
                    "last_checked": datetime.now(UTC),
                    "is_flexible": product.get("lock_period_days", 0) == 0,
                    "can_early_redeem": can_early_redeem,
                    "protocol": product.get("protocol"),  # Для On-chain
                    "product_type": product_type,
                }

                # Валідація обов'язкових полів
                if normalized_product["id"] and normalized_product["symbol"]:
                    normalized.append(normalized_product)
                else:
                    logger.warning(f"⚠️ Пропускаємо OKX продукт через відсутність обов'язкових полів: {product}")

            except Exception as e:
                logger.error(f"❌ Помилка нормалізації OKX продукту {product.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"✅ OKX: нормалізовано {len(normalized)} продуктів")
        return normalized

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Повертає статус здоров'я OKX сервісу.

        Returns:
            Dict з інформацією про стан сервісу
        """
        try:
            # Тест підключення
            connection_test = await self.test_connection()

            # Статистика кешу
            cache_stats = await cache_manager.get_cache_stats()

            # Інформація про конфігурацію
            config_status = {
                "api_key": bool(getattr(settings, 'okx_api_key', '')),
                "api_secret": bool(getattr(settings, 'okx_api_secret', '')),
                "api_passphrase": bool(getattr(settings, 'okx_api_passphrase', '')),
                "base_url": getattr(settings, 'okx_base_url', 'https://www.okx.com')
            }

            health_data = {
                "service": "okx",
                "configured": self.is_configured,
                "connection": connection_test,
                "config_status": config_status,
                "cache_stats": cache_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }

            # Визначаємо загальний статус
            if not self.is_configured:
                health_data["status"] = "unhealthy"
                health_data["message"] = "API ключі не налаштовані"
            elif connection_test.get("status") == "success":
                health_data["status"] = "healthy"
                health_data["message"] = "Сервіс працює нормально"
            else:
                health_data["status"] = "degraded"
                health_data["message"] = "Проблеми з API підключенням"

            return health_data

        except Exception as e:
            logger.error(f"❌ Помилка перевірки здоров'я OKX сервісу: {e}")
            return {
                "service": "okx",
                "status": "error",
                "message": f"Помилка перевірки: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat()
            }

