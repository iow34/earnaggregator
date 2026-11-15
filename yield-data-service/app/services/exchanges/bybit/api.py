from typing import List, Dict, Optional, Any

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class BybitAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.bybit.com")

    def get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def get_flexible_saving_products(
        self, coin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            params = {"category": "FlexibleSaving"}
            if coin:
                params["coin"] = coin.upper()

            logger.info(
                f"[BybitAPI] Запит FlexibleSaving продуктів{f' для {coin}' if coin else ''}"
            )
            data = await self._make_request("GET", "/v5/earn/product", params=params)

            products = []
            items = data.get("result", {}).get("list", [])

            for item in items:
                estimate_apr = item.get("estimateApr", "0%")
                try:
                    apy = float(estimate_apr.replace("%", ""))
                except (ValueError, AttributeError):
                    apy = 0.0

                duration = item.get("duration", "").strip()
                term_days = int(item.get("term") or 0)

                if not duration or duration == "":
                    product_type = "Flexible"
                    term_days = 0
                else:
                    product_type = duration

                coin_name = item.get("coin", "")
                if product_type == "Fixed" and term_days > 0:
                    name = f"{coin_name} Easy Earn Fixed ({term_days} днів)"
                else:
                    name = f"{coin_name} Easy Earn Flexible"

                product = {
                    "id": f"bybit_flexsaving_{item.get('productId', '')}",
                    "symbol": item.get("coin", ""),
                    "name": name,
                    "apy": apy,
                    "min_amount": float(item.get("minStakeAmount") or 0),
                    "max_amount": float(item.get("maxStakeAmount") or 0),
                    "lock_period_days": term_days,
                    "is_active": item.get("status") == "Available",
                    "description": f"Bybit Easy Earn - {product_type} ({item.get('status', 'Unknown')})",
                    "website_url": "https://www.bybit.com/earn",
                    "product_type": product_type,
                    "category": "FlexibleSaving",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[BybitAPI] Отримано {len(products)} FlexibleSaving продуктів")
            return products

        except Exception as e:
            logger.error(f"[BybitAPI] Помилка отримання FlexibleSaving: {e}")
            return []

    async def get_onchain_products(self, coin: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            params = {"category": "OnChain"}
            if coin:
                params["coin"] = coin.upper()

            logger.info(f"[BybitAPI] Запит OnChain продуктів{f' для {coin}' if coin else ''}")
            data = await self._make_request("GET", "/v5/earn/product", params=params)

            products = []
            items = data.get("result", {}).get("list", [])

            for item in items:
                estimate_apr = item.get("estimateApr", "0%")
                try:
                    apy = float(estimate_apr.replace("%", ""))
                except (ValueError, AttributeError):
                    apy = 0.0

                duration = item.get("duration", "Flexible").strip()
                term_days = int(item.get("term") or 0)

                if duration == "Fixed" and term_days > 0:
                    product_type = "Fixed"
                else:
                    product_type = "Flexible"
                    term_days = 0

                coin_name = item.get("coin", "")
                if product_type == "Fixed":
                    name = f"{coin_name} OnChain Fixed ({term_days} днів)"
                else:
                    name = f"{coin_name} OnChain Flexible"

                product = {
                    "id": f"bybit_onchain_{item.get('productId', '')}",
                    "symbol": coin_name,
                    "name": name,
                    "apy": apy,
                    "min_amount": float(item.get("minStakeAmount") or 0),
                    "max_amount": float(item.get("maxStakeAmount") or 0),
                    "lock_period_days": term_days,
                    "is_active": item.get("status") == "Available",
                    "description": f"Bybit OnChain - {product_type} ({item.get('status', 'Unknown')})",
                    "website_url": "https://www.bybit.com/earn",
                    "product_type": product_type,
                    "category": "OnChain",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[BybitAPI] Отримано {len(products)} OnChain продуктів")
            return products

        except Exception as e:
            logger.error(f"[BybitAPI] Помилка отримання OnChain: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        logger.warning("[BybitAPI] 🔴🔴🔴 get_earn_products() БУВ ВИКЛИКАНИЙ! 🔴🔴🔴")
        all_products = []

        try:
            logger.info("[BybitAPI] Початок отримання всіх Earn продуктів")

            try:
                logger.info("[BybitAPI] Викликаємо get_flexible_saving_products...")
                flexible_products = await self.get_flexible_saving_products()
                logger.info(
                    f"[BybitAPI] ✅ Отримано {len(flexible_products)} FlexibleSaving продуктів"
                )
                all_products.extend(flexible_products)
            except Exception as flex_error:
                logger.error(f"[BybitAPI] ❌ Помилка отримання FlexibleSaving: {flex_error}")

            try:
                logger.info("[BybitAPI] Викликаємо get_onchain_products...")
                onchain_products = await self.get_onchain_products()
                logger.info(f"[BybitAPI] ✅ Отримано {len(onchain_products)} OnChain продуктів")
                all_products.extend(onchain_products)
            except Exception as onchain_error:
                logger.error(f"[BybitAPI] ❌ Помилка отримання OnChain: {onchain_error}")

            logger.info("[BybitAPI] Перевірка наявності інших категорій Earn продуктів...")
            try:
                all_categories_data = await self._make_request("GET", "/v5/earn/product")
                all_items = all_categories_data.get("result", {}).get("list", [])

                categories_found = {}
                for item in all_items:
                    cat = item.get("category", "Unknown")
                    if cat not in categories_found:
                        categories_found[cat] = []
                    categories_found[cat].append(item)

                logger.info(f"[BybitAPI] Знайдені категорії: {list(categories_found.keys())}")
                for cat, items in categories_found.items():
                    if cat not in ["FlexibleSaving", "OnChain"]:
                        logger.warning(
                            f"[BybitAPI] ⚠️ Знайдена нова категорія '{cat}' з {len(items)} продуктами! Потрібно додати підтримку."
                        )

                        for item in items:
                            logger.info(
                                f"[BybitAPI] Додаємо продукт з нової категорії {cat}: {item.get('coin', '?')} - {item.get('productId', '?')}"
                            )
                            all_products.append(self._parse_earn_product(item))

            except Exception as cat_error:
                logger.warning(f"[BybitAPI] Не вдалося перевірити інші категорії: {cat_error}")

            logger.info(f"[BybitAPI] Нормалізація {len(all_products)} продуктів...")
            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(f"[BybitAPI] Помилка нормалізації продукту: {norm_error}")
                    normalized_products.append(product)

            logger.info(
                f"[BybitAPI] ✅ Агреговано {len(normalized_products)} Earn продуктів (Flexible: {len(flexible_products)}, OnChain: {len(onchain_products)})"
            )
            return normalized_products

        except Exception as e:
            logger.error(f"[BybitAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True)
            return []

    def _parse_earn_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        category = item.get("category", "Unknown")

        estimate_apr = item.get("estimateApr", "0%")
        try:
            apy = float(estimate_apr.replace("%", ""))
        except (ValueError, AttributeError):
            apy = 0.0

        duration = item.get("duration", "").strip()
        term_days = int(item.get("term") or 0)

        if category == "FlexibleSaving":
            product_type = "Flexible"
            term_days = 0
        elif category == "OnChain":
            if duration == "Fixed" and term_days > 0:
                product_type = "Fixed"
            else:
                product_type = "Flexible"
                term_days = 0
        else:
            if duration == "Fixed" and term_days > 0:
                product_type = "Fixed"
            elif not duration or duration == "":
                product_type = "Flexible"
            else:
                product_type = duration

        coin_name = item.get("coin", "")
        if category == "FlexibleSaving":
            name = f"{coin_name} Easy Earn Flexible"
        elif category == "OnChain":
            if product_type == "Fixed":
                name = f"{coin_name} OnChain Fixed ({term_days} днів)"
            else:
                name = f"{coin_name} OnChain Flexible"
        else:
            if product_type == "Fixed" and term_days > 0:
                name = f"{coin_name} {category} Fixed ({term_days} днів)"
            else:
                name = f"{coin_name} {category} Flexible"

        return {
            "id": f"bybit_{category.lower()}_{item.get('productId', '')}",
            "symbol": coin_name,
            "name": name,
            "apy": apy,
            "min_amount": float(item.get("minStakeAmount") or 0),
            "max_amount": float(item.get("maxStakeAmount") or 0),
            "lock_period_days": term_days,
            "is_active": item.get("status") == "Available",
            "description": f"Bybit {category} - {product_type}",
            "website_url": "https://www.bybit.com/earn",
            "product_type": product_type,
            "category": category,
            "raw_data": item,
        }

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        all_products = []

        try:
            flexible_products = await self.get_flexible_saving_products(coin=asset)
            onchain_products = await self.get_onchain_products(coin=asset)

            all_products.extend(flexible_products)
            all_products.extend(onchain_products)

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[BybitAPI] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[BybitAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.get_flexible_saving_products(asset)

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.get_onchain_products(asset)
