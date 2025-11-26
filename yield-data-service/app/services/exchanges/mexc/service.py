"""
Сервіс для роботи з MEXC продуктами.

MEXC працює в API mode - дані отримуються автоматично через публічний API
та зберігаються в PostgreSQL з автоматичною синхронізацією.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from collections import defaultdict

from app.config import settings
from app.utils.logger import logger
from ..base_service import BaseExchangeService
from .api import MEXCAPI
from .models import CurrencyResult, FinancialProduct


class MEXCService(BaseExchangeService):
    """
    Сервіс для роботи з MEXC продуктами.

    MEXC працює в API mode:
    - Дані отримуються через публічний API MEXC
    - Продукти нормалізуються та зберігаються в PostgreSQL
    - Сервіс працює з кешуванням та автоматичною синхронізацією
    - Підтримує фільтрацію по мінімальному APR для кожного типу продукту
    """

    def __init__(self):
        """Ініціалізація MEXCService."""
        super().__init__(exchange_name="mexc", api_class=MEXCAPI)
        self.is_manual_mode = getattr(settings, 'mexc_manual_mode', False)

        # Для MEXC API ключі не потрібні, тому завжди ініціалізуємо клієнт
        if not self.api_client:
            self.api_client = self.api_class(self.api_key, self.api_secret)
            self.is_configured = True

        logger.info(f"✅ MEXCService ініціалізовано (manual_mode={self.is_manual_mode})")

    async def _normalize_products(self, raw_products: List[CurrencyResult]) -> List[Dict[str, Any]]:
        """
        Нормалізація продуктів з MEXC API до стандарту EarnAggregator.

        Згідно з техзавданням:
        - Фільтрує активні продукти (financialState=2, soldOut=false)
        - Для кожного currency обирає тільки один варіант з мінімальним APR для кожного типу
        - Нормалізує дані до стандартного формату

        Args:
            raw_products: Список CurrencyResult з API

        Returns:
            Список нормалізованих продуктів
        """
        normalized_products = []

        for currency_result in raw_products:
            # Групуємо продукти по типу (FLEXIBLE/FIXED) для вибору мінімального APR
            products_by_type = defaultdict(list)

            for product in currency_result.financialProductList:
                # Фільтруємо тільки активні продукти
                if not (product.financialState == 2 and not product.soldOut):
                    continue

                product_type = product.financialType
                products_by_type[product_type].append(product)

            # Для кожного типу обираємо продукт з мінімальним APR
            for product_type, products in products_by_type.items():
                if not products:
                    continue

                # Знаходимо продукт з мінімальним APR
                min_apr_product = min(products, key=self._get_product_apr)

                # Нормалізуємо продукт
                normalized_product = self._normalize_single_product(
                    min_apr_product,
                    currency_result.currency,
                    product_type
                )

                if normalized_product:
                    normalized_products.append(normalized_product)

        logger.info(f"[MEXCService] Нормалізовано {len(normalized_products)} продуктів")
        return normalized_products

    def _get_product_apr(self, product: FinancialProduct) -> float:
        """
        Отримує APR продукту для порівняння.

        Args:
            product: FinancialProduct

        Returns:
            APR як float
        """
        try:
            # Використовуємо showApr як основний APR (як у API класі)
            return float(product.showApr)

        except (ValueError, TypeError, AttributeError):
            return float('inf')

    def _normalize_single_product(
        self,
        product: FinancialProduct,
        currency: str,
        product_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Нормалізує один продукт до стандарту EarnAggregator.

        Args:
            product: FinancialProduct з API
            currency: Символ валюти
            product_type: Тип продукту (FLEXIBLE/FIXED)

        Returns:
            Нормалізований продукт або None при помилці
        """
        try:
            apr = self._get_product_apr(product)
            if apr == float('inf'):
                logger.warning(f"[MEXCService] Пропускаю продукт {product.financialId} через невалідний APR")
                return None

            # Визначаємо тип продукту
            if product_type == "FLEXIBLE":
                prod_type = "Flexible"
                lock_days = 0
                name = f"{currency} Flexible Savings"
                description = f"Flexible savings for {currency}"
            elif product_type == "FIXED":
                prod_type = "Locked"
                lock_days = product.fixedInvestPeriodCount or 30  # Default 30 days
                name = f"{currency} {lock_days} Days Fixed Savings"
                description = f"Fixed savings for {currency} ({lock_days} days)"
            else:
                logger.warning(f"[MEXCService] Невідомий тип продукту: {product_type}")
                return None

            # Визначаємо рівень ризику
            risk_level = "Low" if currency in ["USDT", "USDC"] else "Medium"

            # Створюємо нормалізований продукт
            normalized = {
                "id": f"mexc_{prod_type.lower()}_{product.financialId}",
                "symbol": currency,
                "name": name,
                "provider": "MEXC",
                "apy": apr,
                "max_apy": apr,  # Для MEXC max_apy = apy
                "is_cefi": True,  # MEXC - це CeFi біржа
                "min_amount": 0.001,  # Default minimum згідно техзавдання
                "max_amount": None,   # Не вказано в API
                "lock_period_days": lock_days,
                "product_type": prod_type,
                "is_active": True,
                "risk_level": risk_level,
                "description": description,
                "website_url": "https://www.mexc.com/staking",
                "raw_data": product.model_dump()
            }

            return normalized

        except Exception as e:
            logger.error(f"[MEXCService] Помилка нормалізації продукту {product.financialId}: {e}")
            return None

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти безпосередньо з MEXC API.

        Args:
            symbol: Символ токену для фільтрації (опціонально)

        Returns:
            Список нормалізованих продуктів
        """
        try:
            if not self.api_client:
                logger.error("[MEXCService] API клієнт не ініціалізований")
                return []

            logger.info(f"[MEXCService] Отримання продуктів з MEXC API для {symbol or 'всіх'}")

            if symbol:
                # Отримуємо продукти для конкретного активу
                products = await self.api_client.get_earn_products_by_asset(symbol)
                logger.info(f"[MEXCService] Отримано {len(products)} продуктів для {symbol}")
            else:
                # Отримуємо всі продукти та нормалізуємо
                logger.info("[MEXCService] Запит до MEXC API get_all_earn_products...")
                currencies = await self.api_client.get_all_earn_products()
                logger.info(f"[MEXCService] Отримано {len(currencies)} валют з API, нормалізую...")
                products = await self._normalize_products(currencies)
                logger.info(f"[MEXCService] Після нормалізації: {len(products)} продуктів")

            logger.info(f"[MEXCService] Отримано {len(products)} продуктів з API")
            return products

        except Exception as e:
            logger.error(f"[MEXCService] Помилка отримання продуктів з API: {e}", exc_info=True)
            return []

    async def sync_products_to_db(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Синхронізує продукти з MEXC API в базу даних.

        Для MEXC завжди отримуємо свіжі дані з API, ігноруючи кеш.
        """
        try:
            logger.info(f"🔄 Початок синхронізації {self.exchange_name} продуктів для {symbol or 'всіх'} з API")

            # Отримуємо свіжі продукти безпосередньо з API
            products = await self.get_products_from_api(symbol)

            if not products:
                return {
                    "status": "warning",
                    "message": "Продукти не знайдено в API",
                    "products_count": 0,
                    "sync_stats": {"created": 0, "updated": 0, "errors": 0}
                }

            # Зберігаємо в БД
            sync_stats = await self._save_products_to_db(products)

            return {
                "status": "success",
                "message": "Синхронізація завершена",
                "products_count": len(products),
                "sync_stats": sync_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Помилка синхронізації {self.exchange_name} продуктів: {e}")
            return {
                "status": "error",
                "message": f"Помилка синхронізації: {str(e)}",
                "products_count": 0,
                "sync_stats": {"created": 0, "updated": 0, "errors": 1},
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримання продуктів з кешу або БД.

        Спочатку перевіряє кеш, якщо даних немає - отримує з БД.
        В API mode дані в БД оновлюються автоматично через sync_products_to_db.

        Args:
            symbol: Символ токену для фільтрації (опціонально)

        Returns:
            Список продуктів з кешу/БД
        """
        if not symbol:
            logger.info("[MEXCService] Отримання всіх MEXC продуктів з БД")
        else:
            logger.info(f"[MEXCService] Отримання MEXC продуктів для {symbol} з БД")
        
        # Читаємо з БД
        from app.db.crud import YieldProductCRUD
        from app.models.yield_product import YieldProductFilter
        
        try:
            # Використовуємо filter_products з фільтром по provider
            filters = YieldProductFilter(provider="MEXC")
            db_products = await YieldProductCRUD.filter_products(filters=filters, limit=None)
            
            # Фільтрація по символу якщо потрібно
            if symbol:
                db_products = [p for p in db_products if p.symbol == symbol.upper()]
            
            # Конвертуємо ORM об'єкти в dict
            products = []
            for p in db_products:
                products.append({
                    "id": p.id,
                    "symbol": p.symbol,
                    "name": p.name,
                    "provider": p.provider,
                    "apy": p.apy,
                    "min_amount": p.min_amount or 0.0,
                    "max_amount": p.max_amount,
                    "lock_period_days": p.lock_period_days,
                    "product_type": getattr(p, 'product_type', 'Flexible' if p.lock_period_days == 0 else 'Locked'),
                    "is_active": p.is_active,
                    "risk_level": p.risk_level,
                    "description": p.description or "",
                    "website_url": p.website_url or "https://www.mexc.com/staking",
                    "raw_data": p.raw_data or {}
                })
            
            logger.info(f"✅ [MEXCService] Знайдено {len(products)} продуктів в БД")
            return products
            
        except Exception as e:
            logger.error(f"❌ [MEXCService] Помилка отримання продуктів з БД: {e}", exc_info=True)
            return []

    async def test_connection(self) -> Dict[str, Any]:
        """
        Перевірка доступності MEXC API та БД.

        Returns:
            Словник зі статусом перевірки
        """
        try:
            # Спочатку перевіряємо API
            api_status = "unknown"
            api_products = 0

            if self.api_client:
                try:
                    # Швидка перевірка API - отримуємо першу сторінку
                    response = await self.api_client.get_earn_products(page=1, page_size=10)
                    api_products = len(response.result)
                    api_status = "success"
                except Exception as e:
                    logger.warning(f"[MEXCService] API недоступний: {e}")
                    api_status = "error"

            # Перевіряємо БД
            from app.db.crud import YieldProductCRUD
            from app.models.yield_product import YieldProductFilter

            filters = YieldProductFilter(provider="MEXC")
            db_products = await YieldProductCRUD.filter_products(filters=filters, limit=None)
            db_count = len(db_products)

            # Визначаємо загальний статус
            if api_status == "success":
                status = "success"
                message = f"MEXC API працює. Продуктів в API: {api_products}, в БД: {db_count}"
            else:
                status = "warning"
                message = f"MEXC працює через БД (API недоступний). Продуктів в БД: {db_count}"

            return {
                "status": status,
                "message": message,
                "manual_mode": self.is_manual_mode,
                "api_status": api_status,
                "api_products": api_products,
                "db_products": db_count,
                "public_api": True
            }

        except Exception as e:
            logger.error(f"❌ Помилка перевірки MEXC: {e}")
            return {
                "status": "error",
                "message": f"Помилка тестування: {e}",
                "manual_mode": self.is_manual_mode,
                "public_api": True
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Перевірка здоров'я MEXC сервісу.

        Returns:
            Словник зі статусом здоров'я
        """
        try:
            connection_test = await self.test_connection()

            if connection_test["status"] == "success":
                return {
                    "status": "healthy",
                    "exchange": "mexc",
                    "mode": "api",
                    "api_status": connection_test.get("api_status"),
                    "products_count": connection_test.get("db_products", 0),
                    "api_products": connection_test.get("api_products", 0),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            elif connection_test["status"] == "warning":
                return {
                    "status": "degraded",
                    "exchange": "mexc",
                    "mode": "api",
                    "api_status": connection_test.get("api_status"),
                    "products_count": connection_test.get("db_products", 0),
                    "warning": connection_test.get("message"),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "exchange": "mexc",
                    "mode": "api",
                    "error": connection_test.get("message"),
                    "timestamp": datetime.now(UTC).isoformat()
                }

        except Exception as e:
            logger.error(f"❌ Помилка health check для MEXC: {e}")
            return {
                "status": "unhealthy",
                "exchange": "mexc",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }

