from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from ..base_service import BaseExchangeService
from .api import ExampleAPI
from app.utils.logger import logger


class ExampleService(BaseExchangeService):
    def __init__(self):
        super().__init__("example", ExampleAPI)

    async def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "status": "error",
                "message": "API ключі Example не налаштовані",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        try:
            logger.info("🧪 Тестування підключення до Example API...")
            start_time = datetime.now(UTC)

            products = await self.api_client.get_flexible_savings_products(size=1)

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до Example API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "products_found": len(products),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до Example API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"exchange:example:{symbol or 'all'}"

        cached_data = await self.cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Example продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        logger.info(f"💾 Запит до Example API для {symbol or 'всіх'} продуктів")
        try:
            if symbol:
                products = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                products = await self.api_client.get_earn_products()

            normalized_products = await self._normalize_products(products)

            cache_data = {
                "products": normalized_products,
                "count": len(normalized_products),
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol,
            }
            await self.cache_manager.set_cached_data(cache_key, cache_data, self.cache_ttl)

            logger.info(f"✅ Отримано {len(normalized_products)} продуктів з Example API")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з Example: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info(f"🔄 Example: нормалізую {len(raw_products)} сирих продуктів")
        normalized = []

        for product in raw_products:
            try:
                normalized_product = {
                    "id": product.get("id", ""),
                    "symbol": product.get("symbol", "").upper(),
                    "name": product.get("name", f"Example {product.get('symbol', '')} Earn"),
                    "provider": "Example",
                    "apy": float(product.get("apy", 0)),
                    "is_cefi": True,
                    "min_amount": float(product.get("min_amount", 0)),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": int(product.get("lock_period_days", 0)),
                    "max_apy": max(
                        float(product.get("apy", 0)),
                        float(product.get("max_apy", product.get("apy", 0))),
                    ),
                    "risk_level": self._determine_risk_level(product),
                    "is_active": bool(product.get("is_active", True)),
                    "website_url": product.get("website_url", "https://www.example.com/earn"),
                    "description": product.get("description", ""),
                    "raw_data": product,
                    "last_checked": datetime.now(UTC),
                }

                if normalized_product["id"] and normalized_product["symbol"]:
                    normalized.append(normalized_product)
                else:
                    logger.warning(
                        f"⚠️ Пропускаємо продукт через відсутність обов'язкових полів: {product}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Помилка нормалізації продукту {product.get('id', 'unknown')}: {e}"
                )
                continue

        return normalized

    def _determine_risk_level(self, product: Dict[str, Any]) -> str:
        lock_period = product.get("lock_period_days", 0)

        if lock_period == 0:  # Flexible
            return "Low"
        elif lock_period <= 30:
            return "Medium"
        else:
            return "High"
