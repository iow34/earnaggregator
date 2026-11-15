from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from ..base_service import BaseExchangeService
from .api import KrakenAPI
from app.utils.logger import logger


class KrakenService(BaseExchangeService):
    def __init__(self):
        super().__init__("kraken", KrakenAPI)

    async def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "status": "error",
                "message": "API ключі Kraken не налаштовані",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        try:
            logger.info("🧪 Тестування підключення до Kraken API...")
            start_time = datetime.now(UTC)

            products = await self.api_client.get_flexible_savings_products(size=1)

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до Kraken API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "products_found": len(products),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до Kraken API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"exchange:kraken:{symbol or 'all'}"

        cached_data = await self.cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Kraken продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        logger.info(f"💾 Запит до Kraken API для {symbol or 'всіх'} продуктів")
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

            logger.info(f"✅ Отримано {len(normalized_products)} продуктів з Kraken API")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання продуктів з Kraken: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info(f"🔄 Kraken: нормалізую {len(raw_products)} сирих продуктів")
        normalized = []

        for product in raw_products:
            try:
                apy_value = float(product.get("apy", 0))
                max_apy_value = float(product.get("max_apy", product.get("apy", 0)))
                corrected_max_apy = max(apy_value, max_apy_value)

                if max_apy_value < apy_value:
                    logger.warning(
                        f"⚠️ Kraken API повернув некоректні дані: apy={apy_value}, max_apy={max_apy_value}, виправлено на {corrected_max_apy}"
                    )

                raw_data = product.get("raw_data", {})
                lock_type_info = raw_data.get("lock_type", {})
                lock_period = int(product.get("lock_period_days", 0))  # default value

                if isinstance(lock_type_info, dict):
                    lock_type = lock_type_info.get("type", "")
                    if lock_type in ["flex", "instant"]:
                        product_type = "Flexible"
                    elif lock_type == "bonded":
                        product_type = "Bonded"
                    else:
                        product_type = "Fixed"  # fallback
                else:
                    product_type = "Flexible" if lock_period == 0 else "Fixed"

                normalized_product = {
                    "id": product.get("id", ""),
                    "symbol": product.get("symbol", "").upper(),
                    "name": product.get("name", f"Kraken {product.get('symbol', '')} Earn"),
                    "provider": "Kraken",
                    "apy": apy_value,
                    "is_cefi": True,
                    "min_amount": float(product.get("min_amount", 0)),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": lock_period,
                    "max_apy": corrected_max_apy,
                    "risk_level": self._determine_risk_level(product),
                    "is_active": bool(product.get("is_active", True)),
                    "website_url": product.get("website_url", "https://www.kraken.com/earn"),
                    "description": product.get("description", ""),
                    "raw_data": product.get("raw_data", product),
                    "product_type": product_type,
                }

                if not normalized_product["id"] or not normalized_product["symbol"]:
                    logger.warning(f"⚠️ Пропущено продукт з невалідними даними: {product}")
                    continue

                normalized.append(normalized_product)

            except Exception as e:
                logger.error(f"❌ Помилка нормалізації продукту Kraken: {e}")
                continue

        logger.info(f"✅ Нормалізовано {len(normalized)} продуктів Kraken")
        return normalized

    def _determine_risk_level(self, product: Dict[str, Any]) -> str:
        symbol = product.get("symbol", "").upper()

        low_risk_assets = {"USDT", "USDC", "DAI", "BUSD", "BTC", "ETH"}
        if symbol in low_risk_assets:
            return "Low"

        high_risk_assets = {"DOT", "ATOM", "KAVA", "KSM"}
        if symbol in high_risk_assets:
            return "High"

        return "Medium"
