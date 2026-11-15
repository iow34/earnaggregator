from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from collections import defaultdict

from app.config import settings
from app.utils.logger import logger
from ..base_service import BaseExchangeService
from .api import BitMartAPI


class BitMartService(BaseExchangeService):
    def __init__(self):
        super().__init__(exchange_name="bitmart", api_class=BitMartAPI)

        self.api_client = self.api_class("", "")
        self.is_configured = True

        logger.info("✅ BitMartService ініціалізовано")

    def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_products = []

        products_by_coin_and_type = defaultdict(lambda: defaultdict(list))

        for product in raw_products:
            if product.get("saleState") != 1:
                continue

            coin_name = product.get("coinName")
            product_type = product.get("productType")

            products_by_coin_and_type[coin_name][product_type].append(product)

        for coin_name, type_products in products_by_coin_and_type.items():
            for product_type, products in type_products.items():
                if not products:
                    continue

                min_apr_product = min(products, key=self._get_product_apr)

                normalized_product = self._normalize_single_product(
                    min_apr_product, coin_name, product_type
                )

                if normalized_product:
                    normalized_products.append(normalized_product)

        logger.info(f"[BitMartService] Нормалізовано {len(normalized_products)} продуктів")
        return normalized_products

    def _get_product_apr(self, product: Dict[str, Any]) -> float:
        try:
            if product.get("rateType") == 1 and product.get("tierRules"):
                tier_rules = product.get("tierRules", [])
                return min(float(tier.get("pec", "0")) for tier in tier_rules)
            else:
                annual_profit_pec = product.get("annualProfitPec", "0%")
                return float(annual_profit_pec.replace("%", ""))

        except (ValueError, TypeError, AttributeError):
            return float("inf")

    def _normalize_single_product(
        self, product: Dict[str, Any], coin_name: str, product_type: str
    ) -> Optional[Dict[str, Any]]:
        try:
            apr = self._get_product_apr(product)
            if apr == float("inf"):
                logger.warning(
                    f"[BitMartService] Пропускаю продукт {product.get('id')} через невалідний APR"
                )
                return None

            lock_day = product.get("lockDay", 0)

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
                logger.warning(
                    f"[BitMartService] Невідомий тип продукту: {product_type}, lockDay: {lock_day}"
                )
                return None

            risk_level = "Low" if coin_name in ["USDT", "USDC"] else "Medium"

            min_amount = self._get_product_min_amount(product)

            normalized_product = {
                "id": f"bitmart_{product_type}_{product.get('id')}",
                "symbol": coin_name,
                "name": name,
                "provider": "BitMart",
                "apy": apr,
                "max_apy": apr,
                "min_amount": min_amount,
                "max_amount": None,
                "lock_period_days": lock_days,
                "product_type": prod_type,
                "is_cefi": True,
                "is_active": True,
                "risk_level": risk_level,
                "description": description,
                "website_url": "https://www.bitmart.com/earn",
                "raw_data": product,
            }

            return normalized_product

        except Exception as e:
            logger.error(f"[BitMartService] Помилка нормалізації продукту {product.get('id')}: {e}")
            return None

    def _get_product_min_amount(self, product: Dict[str, Any]) -> float:
        try:
            return float(product.get("minSubcription", 0))
        except (ValueError, TypeError):
            return 0.0

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            logger.info(
                f"[BitMartService] Отримання продуктів з API{' для ' + symbol if symbol else ''}"
            )

            api_response = await self.api_client.get_earn_products_direct(
                coin_name=symbol if symbol else None
            )

            raw_products = self.api_client.extract_products_from_response(api_response)

            normalized_products = self._normalize_products(raw_products)

            logger.info(f"[BitMartService] Отримано {len(normalized_products)} продуктів з API")
            return normalized_products

        except Exception as e:
            logger.error(f"[BitMartService] Помилка отримання продуктів з API: {e}")
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            cache_key = self._get_cache_key(symbol)

            cached_data = await self.cache_manager.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"[BitMartService] Продукти отримано з кешу для {symbol or 'всіх'}")
                return cached_data

            logger.info(
                f"[BitMartService] Продукти не знайдено в кеші, запитуємо API для {symbol or 'всіх'}"
            )
            products = await self.get_products_from_api(symbol)

            if products:
                await self.cache_manager.set_cached_data(
                    cache_key, products, expiration=self.cache_ttl
                )
                logger.info(f"[BitMartService] Продукти збережено в кеш на {self.cache_ttl} секунд")

            return products

        except Exception as e:
            logger.error(f"[BitMartService] Помилка отримання продуктів з кешем: {e}")
            return []

    def _get_cache_key(self, symbol: Optional[str] = None) -> str:
        base_key = f"bitmart_products"
        if symbol and isinstance(symbol, str):
            return f"{base_key}_{symbol.upper()}"
        return base_key

    async def test_connection(self) -> Dict[str, Any]:
        try:
            logger.info("[BitMartService] Тестування підключення до BitMart")

            if hasattr(self.api_client, "test_connection"):
                return await self.api_client.test_connection()
            else:
                products = await self.get_products_from_api()
                return {
                    "status": "success",
                    "message": f"✅ Підключення успішне. Отримано {len(products)} продуктів",
                    "products_count": len(products),
                }

        except Exception as e:
            logger.error(f"[BitMartService] Помилка тестування підключення: {e}")
            return {
                "status": "error",
                "message": f"❌ Помилка підключення: {str(e)}",
                "products_count": 0,
            }

    async def get_health_status(self) -> Dict[str, Any]:
        try:
            test_result = await self.test_connection()

            return {
                "service": "bitmart",
                "status": test_result["status"],
                "message": test_result["message"],
                "products_count": test_result["products_count"],
                "configured": self.is_configured,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"[BitMartService] Помилка перевірки здоров'я: {e}")
            return {
                "service": "bitmart",
                "status": "error",
                "message": f"❌ Помилка здоров'я: {str(e)}",
                "products_count": 0,
                "configured": self.is_configured,
                "timestamp": datetime.now(UTC).isoformat(),
            }
