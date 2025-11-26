"""
Сервіс для інтеграції з Binance API.

Цей сервіс об'єднує логіку отримання даних з Binance API,
нормалізації, кешування та збереження в базу даних.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from ..base_service import BaseExchangeService
from .api import BinanceAPI
from app.utils.logger import logger


class BinanceService(BaseExchangeService):
    """
    Сервіс для роботи з Binance API.

    Агрегує логіку отримання даних, нормалізації,
    збереження в БД та кешування для Binance.
    """

    def __init__(self):
        """Ініціалізує Binance сервіс."""
        super().__init__("binance", BinanceAPI)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестує підключення до Binance API.

        Returns:
            Dict з результатами тестування
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "API ключі Binance не налаштовані",
                "timestamp": datetime.now(UTC).isoformat()
            }

        try:
            logger.info("🧪 Тестування підключення до Binance API...")
            start_time = datetime.now(UTC)

            # Тестуємо отримання Flexible products (менше даних)
            products = await self.api_client.get_flexible_savings_products(size=1)

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до Binance API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "products_found": len(products),
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до Binance API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти Binance з кешуванням.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            List нормалізованих продуктів
        """
        cache_key = f"exchange:binance:{symbol or 'all'}"

        # Перевіряємо кеш
        cached_data = await self.cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Binance продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        # Якщо в кеші немає - отримуємо з API
        logger.info(f"💾 Запит до Binance API для {symbol or 'всіх'} продуктів")
        try:
            if symbol:
                products = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                products = await self.api_client.get_earn_products()

            # Нормалізуємо дані
            normalized_products = await self._normalize_products(products)

            # Зберігаємо в кеш
            cache_data = {
                "products": normalized_products,
                "count": len(normalized_products),
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol
            }
            await self.cache_manager.set_cached_data(cache_key, cache_data, self.cache_ttl)

            logger.info(f"✅ Отримано {len(normalized_products)} продуктів з Binance API")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з Binance: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Нормалізує дані продуктів до єдиного формату.

        Args:
            raw_products: Сирі дані з Binance API

        Returns:
            List нормалізованих продуктів
        """
        logger.info(f"🔄 Binance: нормалізую {len(raw_products)} сирих продуктів")
        normalized = []

        for product in raw_products:
            try:
                # Додаткове нормалізування для Binance специфіки
                apy_value = float(product.get("apy", 0))
                max_apy_value = float(product.get("max_apy", product.get("apy", 0)))
                corrected_max_apy = max(apy_value, max_apy_value)

                if max_apy_value < apy_value:
                    logger.warning(f"⚠️ Binance API повернув некоректні дані: apy={apy_value}, max_apy={max_apy_value}, виправлено на {corrected_max_apy}")

                normalized_product = {
                    "id": product.get("id", ""),
                    "symbol": product.get("symbol", "").upper(),
                    "name": product.get("name", f"Binance {product.get('symbol', '')} Earn"),
                    "provider": "Binance",
                    "apy": apy_value,
                    "is_cefi": True,
                    "min_amount": float(product.get("min_amount", 0)),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": int(product.get("lock_period_days", 0)),
                    "max_apy": corrected_max_apy,
                    "risk_level": self._determine_risk_level(product),
                    "is_active": bool(product.get("is_active", True)),
                    "website_url": product.get("website_url", "https://www.binance.com/en/earn"),
                    "description": product.get("description", ""),
                    "raw_data": product,
                    "last_checked": datetime.now(UTC),
                    "is_flexible": product.get("lock_period_days", 0) == 0,
                }

                # Валідація обов'язкових полів
                if normalized_product["id"] and normalized_product["symbol"]:
                    normalized.append(normalized_product)
                else:
                    logger.warning(f"⚠️ Пропускаємо продукт через відсутність обов'язкових полів: {product}")

            except Exception as e:
                logger.error(f"❌ Помилка нормалізації продукту {product.get('id', 'unknown')}: {e}")
                continue

        return normalized

    def _determine_risk_level(self, product: Dict[str, Any]) -> str:
        """
        Визначає рівень ризику на основі характеристик продукту.

        Args:
            product: Дані продукту

        Returns:
            str: Рівень ризику (Low, Medium, High)
        """
        # Binance - зазвичай низький ризик для Simple Earn
        lock_period = product.get("lock_period_days", 0)

        if lock_period == 0:  # Flexible
            return "Low"
        elif lock_period <= 30:  # Короткий lock
            return "Medium"
        else:  # Довгий lock
            return "High"
