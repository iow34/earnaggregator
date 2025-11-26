"""
Сервіс для роботи з BitMart продуктами.

BitMart працює в API mode - дані отримуються автоматично через публічний API
та зберігаються в PostgreSQL з автоматичною синхронізацією.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from collections import defaultdict

from app.config import settings
from app.utils.logger import logger
from ..base_service import BaseExchangeService
from .api import BitMartAPI
# from .models import BitMartEarnAPIResponse, AddInfo  # Не використовуємо більше Pydantic моделі


class BitMartService(BaseExchangeService):
    """
    Сервіс для роботи з BitMart продуктами.

    BitMart працює в API mode:
    - Дані отримуються через публічний API BitMart
    - Продукти нормалізуються та зберігаються в PostgreSQL
    - Сервіс працює з кешуванням та автоматичною синхронізацією
    - Підтримує фільтрацію по мінімальному APR для кожного типу продукту
    """

    def __init__(self):
        """Ініціалізація BitMartService."""
        super().__init__(exchange_name="bitmart", api_class=BitMartAPI)

        # Для BitMart API ключі не потрібні, тому завжди ініціалізуємо клієнт
        # Використовуємо порожні рядки для API ключів оскільки вони не потрібні
        self.api_client = self.api_class("", "")
        self.is_configured = True

        logger.info("✅ BitMartService ініціалізовано")

    def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Нормалізація продуктів з BitMart API до стандарту EarnAggregator.

        Згідно з техзавданням:
        - Фільтрує активні продукти (saleState=1)
        - Для кожного coinName і типу обирає тільки один варіант з мінімальним APR
        - Нормалізує дані до стандартного формату

        Args:
            raw_products: Список AddInfo з API

        Returns:
            Список нормалізованих продуктів
        """
        normalized_products = []

        # Групуємо продукти по coinName і productType для вибору мінімального APR
        products_by_coin_and_type = defaultdict(lambda: defaultdict(list))

        for product in raw_products:
            if product.get('saleState') != 1:  # Тільки активні продукти
                continue

            coin_name = product.get('coinName')
            product_type = product.get('productType')

            products_by_coin_and_type[coin_name][product_type].append(product)

        # Для кожного coin і типу обираємо продукт з мінімальним APR
        for coin_name, type_products in products_by_coin_and_type.items():
            for product_type, products in type_products.items():
                if not products:
                    continue

                # Знаходимо продукт з мінімальним APR
                min_apr_product = min(products, key=self._get_product_apr)

                # Нормалізуємо продукт
                normalized_product = self._normalize_single_product(
                    min_apr_product,
                    coin_name,
                    product_type
                )

                if normalized_product:
                    normalized_products.append(normalized_product)

        logger.info(f"[BitMartService] Нормалізовано {len(normalized_products)} продуктів")
        return normalized_products

    def _get_product_apr(self, product: Dict[str, Any]) -> float:
        """
        Отримує APR продукту для порівняння.

        Args:
            product: AddInfo продукт як словник

        Returns:
            APR як float
        """
        try:
            if product.get('rateType') == 1 and product.get('tierRules'):
                # Tiered APR - обираємо мінімальний pec
                tier_rules = product.get('tierRules', [])
                return min(float(tier.get('pec', '0')) for tier in tier_rules)
            else:
                # Фіксований APR
                annual_profit_pec = product.get('annualProfitPec', '0%')
                return float(annual_profit_pec.replace('%', ''))

        except (ValueError, TypeError, AttributeError):
            return float('inf')

    def _normalize_single_product(
        self,
        product: Dict[str, Any],
        coin_name: str,
        product_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Нормалізує один продукт до стандарту EarnAggregator.

        Args:
            product: AddInfo з API
            coin_name: Символ валюти
            product_type: Тип продукту (flexible/fixed)

        Returns:
            Нормалізований продукт або None при помилці
        """
        try:
            apr = self._get_product_apr(product)
            if apr == float('inf'):
                logger.warning(f"[BitMartService] Пропускаю продукт {product.get('id')} через невалідний APR")
                return None

            # Визначаємо тип продукту
            lock_day = product.get('lockDay', 0)

            # Мапінг типів BitMart до стандартних
            if product_type in ["flexible", "agility"] and lock_day == 0:
                prod_type = "Flexible"
                lock_days = 0
                name = f"{coin_name} Flexible Savings"
                description = f"Flexible savings for {coin_name}"
            elif product_type in ["fixed", "locked"] and lock_day > 0:
                prod_type = "Locked"
                lock_days = lock_day
                name = f"{coin_name} {lock_days} Days Fixed Savings"
                description = f"Fixed savings for {coin_name} ({lock_days} days)"
            elif product_type == "promotions":
                # Промоційні продукти - обробляємо як locked якщо є lockDay, інакше flexible
                if lock_day > 0:
                    prod_type = "Locked"
                    lock_days = lock_day
                    name = f"{coin_name} {lock_days} Days Promo Savings"
                    description = f"Promotional fixed savings for {coin_name} ({lock_days} days)"
                else:
                    prod_type = "Flexible"
                    lock_days = 0
                    name = f"{coin_name} Promo Flexible Savings"
                    description = f"Promotional flexible savings for {coin_name}"
            else:
                logger.warning(f"[BitMartService] Невідомий тип продукту: {product_type}, lockDay: {lock_day}")
                return None

            # Визначаємо рівень ризику
            risk_level = "Low" if coin_name in ["USDT", "USDC"] else "Medium"

            # Отримуємо мінімальну суму
            min_amount = self._get_product_min_amount(product)

            # Створюємо нормалізований продукт
            normalized_product = {
                "id": f"bitmart_{product_type}_{product.get('id')}",
                "symbol": coin_name,
                "name": name,
                "provider": "BitMart",
                "apy": apr,
                "max_apy": apr,  # Для BitMart max_apy = apy
                "min_amount": min_amount,
                "max_amount": None,  # BitMart не надає max_amount
                "lock_period_days": lock_days,
                "product_type": prod_type,
                "is_cefi": True,
                "is_active": True,
                "risk_level": risk_level,
                "description": description,
                "website_url": "https://www.bitmart.com/earn",
                "raw_data": product
            }

            return normalized_product

        except Exception as e:
            logger.error(f"[BitMartService] Помилка нормалізації продукту {product.get('id')}: {e}")
            return None

    def _get_product_min_amount(self, product: Dict[str, Any]) -> float:
        """
        Отримує мінімальну суму для продукту.

        Args:
            product: AddInfo продукт як словник

        Returns:
            float: Мінімальна сума
        """
        try:
            return float(product.get('minSubcription', 0))
        except (ValueError, TypeError):
            return 0.0

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти безпосередньо з BitMart API.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            Список нормалізованих продуктів
        """
        try:
            logger.info(f"[BitMartService] Отримання продуктів з API{' для ' + symbol if symbol else ''}")

            # Отримуємо дані з API
            api_response = await self.api_client.get_earn_products_direct(
                coin_name=symbol if symbol else None
            )

            # Витягуємо продукти з відповіді
            raw_products = self.api_client.extract_products_from_response(api_response)

            # Нормалізуємо продукти
            normalized_products = self._normalize_products(raw_products)

            logger.info(f"[BitMartService] Отримано {len(normalized_products)} продуктів з API")
            return normalized_products

        except Exception as e:
            logger.error(f"[BitMartService] Помилка отримання продуктів з API: {e}")
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти з кешуванням.

        Args:
            symbol: Опціональний символ для фільтрації

        Returns:
            Список продуктів
        """
        try:
            # Створюємо ключ кешу
            cache_key = self._get_cache_key(symbol)

            # Спробуємо отримати з кешу
            cached_data = await self.cache_manager.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"[BitMartService] Продукти отримано з кешу для {symbol or 'всіх'}")
                return cached_data

            # Якщо немає в кеші - отримуємо з API
            logger.info(f"[BitMartService] Продукти не знайдено в кеші, запитуємо API для {symbol or 'всіх'}")
            products = await self.get_products_from_api(symbol)

            # Зберігаємо в кеш
            if products:
                await self.cache_manager.set_cached_data(cache_key, products, expiration=self.cache_ttl)
                logger.info(f"[BitMartService] Продукти збережено в кеш на {self.cache_ttl} секунд")

            return products

        except Exception as e:
            logger.error(f"[BitMartService] Помилка отримання продуктів з кешем: {e}")
            return []

    def _get_cache_key(self, symbol: Optional[str] = None) -> str:
        """Створює ключ кешу для продуктів."""
        base_key = f"bitmart_products"
        if symbol and isinstance(symbol, str):
            return f"{base_key}_{symbol.upper()}"
        return base_key

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестує підключення до BitMart API.

        Returns:
            Dict з результатами тесту
        """
        try:
            logger.info("[BitMartService] Тестування підключення до BitMart")

            # Делегую тест до API клієнта
            if hasattr(self.api_client, 'test_connection'):
                return await self.api_client.test_connection()
            else:
                # Ручний тест
                products = await self.get_products_from_api()
                return {
                    "status": "success",
                    "message": f"✅ Підключення успішне. Отримано {len(products)} продуктів",
                    "products_count": len(products)
                }

        except Exception as e:
            logger.error(f"[BitMartService] Помилка тестування підключення: {e}")
            return {
                "status": "error",
                "message": f"❌ Помилка підключення: {str(e)}",
                "products_count": 0
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Перевіряє стан здоров'я сервісу.

        Returns:
            Dict зі статусом здоров'я
        """
        try:
            # Тестуємо підключення
            test_result = await self.test_connection()

            return {
                "service": "bitmart",
                "status": test_result["status"],
                "message": test_result["message"],
                "products_count": test_result["products_count"],
                "configured": self.is_configured,
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"[BitMartService] Помилка перевірки здоров'я: {e}")
            return {
                "service": "bitmart",
                "status": "error",
                "message": f"❌ Помилка здоров'я: {str(e)}",
                "products_count": 0,
                "configured": self.is_configured,
                "timestamp": datetime.now(UTC).isoformat()
            }
