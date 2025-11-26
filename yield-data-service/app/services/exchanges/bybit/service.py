"""
Сервіс для інтеграції з Bybit API.

Цей сервіс об'єднує логіку отримання даних з Bybit API,
нормалізації, кешування та збереження в базу даних.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from ..base_service import BaseExchangeService
from .api import BybitAPI
from app.utils.logger import logger


class BybitService(BaseExchangeService):
    """
    Сервіс для роботи з Bybit API.

    Агрегує логіку отримання даних, нормалізації,
    збереження в БД та кешування для Bybit.
    """

    def __init__(self):
        """Ініціалізує Bybit сервіс."""
        super().__init__("bybit", BybitAPI)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестує підключення до Bybit API.

        Returns:
            Dict з результатами тестування
        """
        if not self.api_client:
            # Створюємо тимчасовий клієнт для тестування (публічні endpoints)
            self.api_client = BybitAPI("", "")

        try:
            logger.info("🧪 Тестування підключення до Bybit API...")
            start_time = datetime.now(UTC)

            # Тестуємо отримання FlexibleSaving products (менше даних)
            products = await self.api_client.get_flexible_saving_products()

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до Bybit API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "products_found": len(products),
                "public_api": True,  # Bybit Earn API публічний
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до Bybit API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "public_api": True,
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти Bybit з кешуванням.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            List нормалізованих продуктів
        """
        cache_key = f"exchange:bybit:{symbol or 'all'}"

        # Перевіряємо кеш
        cached_data = await self.cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Bybit продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        # Якщо в кеші немає - отримуємо з API
        logger.info(f"💾 Запит до Bybit API для {symbol or 'всіх'} продуктів")

        if not self.api_client:
            self.api_client = BybitAPI("", "")

        try:
            if symbol:
                logger.info(f"🟡 Викликаємо get_earn_products_by_asset({symbol})")
                products = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                logger.info(f"🟡 Викликаємо get_earn_products() для всіх продуктів")
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

            logger.info(f"✅ Отримано {len(normalized_products)} продуктів з Bybit API")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з Bybit: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Нормалізує дані продуктів до єдиного формату.

        Args:
            raw_products: Сирі дані з Bybit API

        Returns:
            List нормалізованих продуктів
        """
        normalized = []

        for product in raw_products:
            try:
                # Додаткове нормалізування для Bybit специфіки
                normalized_product = {
                    "id": product.get("id", ""),
                    "symbol": product.get("symbol", "").upper(),
                    "name": product.get("name", f"Bybit {product.get('symbol', '')} Earn"),
                    "provider": "Bybit",
                    "apy": float(product.get("apy", 0)),
                    "is_cefi": self._determine_cefi_status(product),
                    "min_amount": float(product.get("min_amount", 0)),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": int(product.get("lock_period_days", 0)),
                    "max_apy": max(float(product.get("apy", 0)), float(product.get("max_apy", product.get("apy", 0)))),
                    "risk_level": self._determine_risk_level(product),
                    "is_active": bool(product.get("is_active", True)),
                    "website_url": product.get("website_url", "https://www.bybit.com/earn"),
                    "description": product.get("description", ""),
                    "raw_data": product,
                    "last_checked": datetime.now(UTC),
                    "product_category": product.get("category", "Unknown"),
                    "product_type": product.get("product_type", "Flexible"),
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

    def _determine_cefi_status(self, product: Dict[str, Any]) -> bool:
        """
        Визначає чи продукт CeFi чи DeFi на основі категорії.

        Args:
            product: Дані продукту

        Returns:
            bool: True для CeFi, False для DeFi
        """
        category = product.get("category", "").lower()

        # FlexibleSaving - це CeFi (керується Bybit)
        if category == "flexiblesaving":
            return True

        # OnChain - це DeFi (он-чейн стейкінг)
        if category == "onchain":
            return False

        # За замовчуванням вважаємо CeFi для Bybit
        return True

    def _determine_risk_level(self, product: Dict[str, Any]) -> str:
        """
        Визначає рівень ризику на основі характеристик продукту.

        Args:
            product: Дані продукту

        Returns:
            str: Рівень ризику (Low, Medium, High)
        """
        category = product.get("category", "").lower()
        lock_period = product.get("lock_period_days", 0)

        # OnChain продукти зазвичай ризиковіші
        if category == "onchain":
            if lock_period <= 7:  # Короткий
                return "Medium"
            else:  # Довгий
                return "High"

        # FlexibleSaving продукти
        if category == "flexiblesaving":
            if lock_period == 0:  # Flexible
                return "Low"
            elif lock_period <= 30:  # Короткий lock
                return "Medium"
            else:  # Довгий lock
                return "High"

        # За замовчуванням
        return "Medium"
