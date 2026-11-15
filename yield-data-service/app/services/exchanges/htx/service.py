from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from app.config import settings
from app.utils.logger import logger
from app.services.coingecko_service import coingecko_service
from ..base_service import BaseExchangeService
from .api import HTXAPI


class HTXService(BaseExchangeService):
    def __init__(self):
        super().__init__("htx", HTXAPI)

    async def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "status": "error",
                "message": "API ключі HTX не налаштовані",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        try:
            logger.info("🧪 Тестування підключення до HTX API...")
            start_time = datetime.now(UTC)

            products = await self.api_client.get_flexible_savings_products(size=1)

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до HTX API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "products_found": len(products),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до HTX API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.api_client:
            logger.error("❌ HTX API клієнт не ініціалізовано")
            return []

        try:
            if symbol:
                products = await self.api_client.get_earn_products_by_asset(asset=symbol)
            else:
                products = await self.api_client.get_earn_products()

            if products:
                products = await self.sort_products_by_popularity(products)

            return products
        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з HTX API: {e}", exc_info=True)
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"exchange:htx:{symbol or 'all'}"

        try:
            cached_data = await self.cache_manager.get_cached_data(cache_key)
            if cached_data:
                logger.info(f"✅ HTX дані отримано з кешу (key: {cache_key})")

                if cached_data:
                    cached_data = await self.sort_products_by_popularity(cached_data)
                return cached_data
        except Exception as cache_error:
            logger.warning(f"⚠️ Помилка читання кешу HTX: {cache_error}")

        logger.info(f"🔄 Отримання HTX даних з API{f' для {symbol}' if symbol else ''}")
        products = await self.get_products_from_api(symbol)

        if products:
            try:
                await self.cache_manager.set_cached_data(cache_key, products, self.cache_ttl)
                logger.info(f"💾 HTX дані збережено в кеш (TTL: {self.cache_ttl}s)")
            except Exception as cache_error:
                logger.warning(f"⚠️ Помилка збереження в кеш: {cache_error}")

        return products

    async def sort_products_by_popularity(
        self, products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not products:
            return []

        products_with_popularity = []
        for product in products:
            symbol = product.get("symbol", "").upper()
            if symbol:
                popularity_rank = await coingecko_service.get_popularity_rank(symbol)

                popularity_rank = popularity_rank if popularity_rank is not None else 9999
            else:
                popularity_rank = 9999

            product_with_rank = product.copy()
            product_with_rank["_popularity_rank"] = popularity_rank
            products_with_popularity.append(product_with_rank)

        sorted_products = sorted(
            products_with_popularity, key=lambda p: (p["_popularity_rank"], -p.get("apy", 0))
        )

        for product in sorted_products:
            product.pop("_popularity_rank", None)

        logger.info(
            f"✅ HTX продукти відсортовані за популярністю: {len(sorted_products)} продуктів"
        )
        return sorted_products

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not raw_products:
            return []

        products_with_popularity = []
        for product in raw_products:
            symbol = product.get("symbol", "").upper()
            if symbol:
                popularity_rank = await coingecko_service.get_popularity_rank(symbol)

                popularity_rank = popularity_rank if popularity_rank is not None else 9999
            else:
                popularity_rank = 9999

            product_with_rank = product.copy()
            product_with_rank["_popularity_rank"] = popularity_rank
            products_with_popularity.append(product_with_rank)

        sorted_products = sorted(
            products_with_popularity, key=lambda p: (p["_popularity_rank"], -p.get("apy", 0))
        )

        for product in sorted_products:
            product.pop("_popularity_rank", None)

        logger.info(
            f"✅ HTX продукти відсортовані за популярністю: {len(sorted_products)} продуктів"
        )
        return sorted_products

    async def get_health_status(self) -> Dict[str, Any]:
        try:
            if not self.is_configured:
                return {
                    "status": "unhealthy",
                    "exchange": "htx",
                    "reason": "API ключі не налаштовані",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            test_result = await self.test_connection()

            if test_result.get("status") == "success":
                return {
                    "status": "healthy",
                    "exchange": "htx",
                    "api_status": "active",
                    "response_time_ms": test_result.get("response_time_ms"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            else:
                return {
                    "status": "degraded",
                    "exchange": "htx",
                    "reason": test_result.get("message"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        except Exception as e:
            logger.error(f"❌ Помилка перевірки здоров'я HTX: {e}")
            return {
                "status": "unhealthy",
                "exchange": "htx",
                "reason": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            }
