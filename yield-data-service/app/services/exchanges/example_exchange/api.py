from typing import List, Dict, Optional, Any

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class ExampleAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.example.com")

    def get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "X-API-Key": self.api_key}

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/v1/earn/flexible"
            params = {"page": current, "limit": size}
            if asset:
                params["asset"] = asset

            logger.info(f"[ExampleAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''}")

            data = await self._make_request("GET", path, params=params)

            products = []
            items = data.get("data", {}).get("products", [])

            for item in items:
                apy = float(item.get("apy", 0))

                product = {
                    "id": f"example_flex_{item.get('id', '')}",
                    "symbol": item.get("symbol", ""),
                    "name": f"{item.get('symbol', '')} Flexible Savings",
                    "provider": "Example",
                    "apy": apy,
                    "min_amount": float(item.get("min_amount", 0)),
                    "lock_period_days": 0,
                    "is_active": item.get("status") == "active",
                    "description": item.get("description", ""),
                    "website_url": "https://www.example.com/earn",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[ExampleAPI] Отримано {len(products)} Flexible продуктів")
            return products

        except Exception as e:
            logger.error(f"[ExampleAPI] Помилка отримання Flexible: {e}")
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/v1/earn/locked"
            params = {"page": current, "limit": size}
            if asset:
                params["asset"] = asset

            logger.info(f"[ExampleAPI] Запит Locked продуктів{f' для {asset}' if asset else ''}")
            data = await self._make_request("GET", path, params=params)

            products = []
            items = data.get("data", {}).get("products", [])

            for item in items:
                apy = float(item.get("apy", 0))
                lock_days = int(item.get("lock_period", 0))

                product = {
                    "id": f"example_locked_{item.get('id', '')}",
                    "symbol": item.get("symbol", ""),
                    "name": f"{item.get('symbol', '')} Locked Savings ({lock_days} days)",
                    "provider": "Example",
                    "apy": apy,
                    "min_amount": float(item.get("min_amount", 0)),
                    "lock_period_days": lock_days,
                    "is_active": item.get("status") == "active",
                    "description": f"Locked savings for {item.get('symbol', '')}",
                    "website_url": "https://www.example.com/earn",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[ExampleAPI] Отримано {len(products)} Locked продуктів")
            return products

        except Exception as e:
            logger.error(f"[ExampleAPI] Помилка отримання Locked: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        all_products = []

        try:
            logger.info("[ExampleAPI] Початок отримання всіх Earn продуктів")

            flexible_products = await self.get_flexible_savings_products()
            all_products.extend(flexible_products)
            logger.info(f"[ExampleAPI] ✅ Отримано {len(flexible_products)} Flexible продуктів")

            locked_products = await self.get_locked_savings_products()
            all_products.extend(locked_products)
            logger.info(f"[ExampleAPI] ✅ Отримано {len(locked_products)} Locked продуктів")

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(f"[ExampleAPI] Помилка нормалізації продукту: {norm_error}")
                    normalized_products.append(product)

            logger.info(f"[ExampleAPI] ✅ Агреговано {len(normalized_products)} Earn продуктів")
            return normalized_products

        except Exception as e:
            logger.error(
                f"[ExampleAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True
            )
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        all_products = []

        try:
            flexible_products = await self.get_flexible_savings_products(asset=asset)
            locked_products = await self.get_locked_savings_products(asset=asset)

            all_products.extend(flexible_products)
            all_products.extend(locked_products)

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[ExampleAPI] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[ExampleAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []
