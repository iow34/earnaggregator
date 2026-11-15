from typing import List, Dict, Optional, Any
import hmac
import hashlib
import base64
import time
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class BitgetAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str = ""):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.bitget.com")
        self.api_passphrase = api_passphrase

        logger.info(f"✅ BitgetAPI ініціалізовано з URL: {self.base_url}")

    def _generate_timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def _generate_signature(
        self, timestamp: str, method: str, request_path: str, query_string: str = "", body: str = ""
    ) -> str:

        if query_string and not query_string.startswith("?"):
            query_string = "?" + query_string

        message = timestamp + method.upper() + request_path + query_string + body

        logger.debug(f"[BitgetAPI] Signature message: {message[:100]}...")

        mac = hmac.new(self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)

        signature = base64.b64encode(mac.digest()).decode("utf-8")

        return signature

    def get_headers(
        self, method: str = "GET", request_path: str = "/", query_string: str = "", body: str = ""
    ) -> Dict[str, str]:
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(timestamp, method, request_path, query_string, body)

        headers = {
            "Content-Type": "application/json",
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.api_passphrase,
            "locale": "en-US",
        }

        logger.debug(f"[BitgetAPI] Headers: key={self.api_key[:8]}***, timestamp={timestamp}")

        return headers

    def _parse_ladder_apy(self, apy_list: List[Dict[str, Any]]) -> tuple[float, float]:
        if not apy_list:
            return 0.0, 0.0

        apys = []
        for tier in apy_list:
            try:
                apy_value = float(tier.get("currentApy", 0))
                apys.append(apy_value)
            except (ValueError, TypeError):
                logger.warning(f"[BitgetAPI] Неможливо парсити APY: {tier.get('currentApy')}")
                continue

        if not apys:
            return 0.0, 0.0

        return min(apys), max(apys)

    def _parse_min_max_amounts(
        self, apy_list: List[Dict[str, Any]]
    ) -> tuple[Optional[float], Optional[float]]:
        if not apy_list:
            return None, None

        try:
            min_amount = float(apy_list[0].get("minStepVal", 0))

            max_step_val = apy_list[-1].get("maxStepVal", "")

            max_amount = None
            if max_step_val and max_step_val != "":
                try:
                    max_val = float(max_step_val)

                    if max_val < 1e10:
                        max_amount = max_val
                except (ValueError, TypeError):
                    max_amount = None

            return min_amount, max_amount

        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"[BitgetAPI] Помилка парсингу min/max amounts: {e}")
            return None, None

    def _determine_risk_level(self, product_level: str, coin: str) -> str:

        stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD"]
        if coin.upper() in stablecoins:
            return "Low"

        if product_level == "beginner":
            return "Low"
        elif product_level == "VIP":
            return "Medium"
        else:
            return "Low"

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/api/v2/earn/savings/product"

            params = {"filter": "available"}
            if asset:
                params["coin"] = asset

            query_string = urlencode(params)

            headers = self.get_headers(
                method="GET", request_path=path, query_string=query_string, body=""
            )

            logger.info(f"[BitgetAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''}")

            response = await self._make_request("GET", path, params=params, headers=headers)

            if response.get("code") != "00000":
                logger.error(f"[BitgetAPI] API помилка: {response.get('msg', 'Unknown error')}")
                return []

            data = response.get("data", [])
            if not isinstance(data, list):
                logger.warning(f"[BitgetAPI] Очікувався список, отримано: {type(data)}")
                return []

            products = []
            for item in data:
                if item.get("periodType") != "flexible":
                    continue

                if item.get("status") != "in_progress":
                    continue

                coin = item.get("coin", "")
                apy_type = item.get("apyType", "single")
                apy_list = item.get("apyList", [])

                if apy_type == "ladder" and apy_list:
                    min_apy, max_apy = self._parse_ladder_apy(apy_list)
                    min_amount, max_amount = self._parse_min_max_amounts(apy_list)
                else:
                    # Single APY
                    try:
                        apy_value = float(apy_list[0].get("currentApy", 0)) if apy_list else 0.0
                    except (ValueError, TypeError, IndexError):
                        apy_value = 0.0
                    min_apy = apy_value
                    max_apy = apy_value
                    min_amount = None
                    max_amount = None

                advance_redeem = item.get("advanceRedeem", "")
                settle_method = item.get("settleMethod", "")
                description_parts = []
                if advance_redeem:
                    description_parts.append(f"Advance redeem: {advance_redeem}")
                if settle_method:
                    description_parts.append(f"Settle: {settle_method}")
                description = (
                    "; ".join(description_parts)
                    if description_parts
                    else f"{coin} Flexible Savings"
                )

                product = {
                    "id": f"bitget_flex_{item.get('productId', coin)}",
                    "symbol": coin,
                    "name": f"{coin} Flexible Savings",
                    "provider": "bitget",
                    "apy": min_apy,
                    "max_apy": max_apy,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "lock_period_days": 0,
                    "product_type": "Flexible",
                    "is_active": True,
                    "risk_level": self._determine_risk_level(
                        item.get("productLevel", "normal"), coin
                    ),
                    "description": description,
                    "website_url": "https://www.bitget.com/earn",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[BitgetAPI] ✅ Отримано {len(products)} Flexible продуктів")
            return products

        except Exception as e:
            logger.error(f"[BitgetAPI] ❌ Помилка отримання Flexible продуктів: {e}", exc_info=True)
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/api/v2/earn/savings/product"

            params = {"filter": "available"}
            if asset:
                params["coin"] = asset

            query_string = urlencode(params)

            headers = self.get_headers(
                method="GET", request_path=path, query_string=query_string, body=""
            )

            logger.info(f"[BitgetAPI] Запит Fixed продуктів{f' для {asset}' if asset else ''}")

            response = await self._make_request("GET", path, params=params, headers=headers)

            if response.get("code") != "00000":
                logger.error(f"[BitgetAPI] API помилка: {response.get('msg', 'Unknown error')}")
                return []

            data = response.get("data", [])
            if not isinstance(data, list):
                logger.warning(f"[BitgetAPI] Очікувався список, отримано: {type(data)}")
                return []

            products = []
            for item in data:
                if item.get("periodType") != "fixed":
                    continue

                if item.get("status") != "in_progress":
                    continue

                coin = item.get("coin", "")
                period = item.get("period", "0")

                try:
                    lock_days = int(period)
                except (ValueError, TypeError):
                    logger.warning(f"[BitgetAPI] Неможливо парсити період: {period}")
                    lock_days = 0

                if lock_days == 0:
                    continue

                apy_type = item.get("apyType", "single")
                apy_list = item.get("apyList", [])

                if apy_type == "ladder" and apy_list:
                    min_apy, max_apy = self._parse_ladder_apy(apy_list)
                    min_amount, max_amount = self._parse_min_max_amounts(apy_list)
                else:
                    try:
                        apy_value = float(apy_list[0].get("currentApy", 0)) if apy_list else 0.0
                    except (ValueError, TypeError, IndexError):
                        apy_value = 0.0
                    min_apy = apy_value
                    max_apy = apy_value
                    min_amount = None
                    max_amount = None

                advance_redeem = item.get("advanceRedeem", "")
                settle_method = item.get("settleMethod", "")
                description_parts = [f"Fixed savings for {lock_days} days"]
                if advance_redeem:
                    description_parts.append(f"Advance redeem: {advance_redeem}")
                if settle_method:
                    description_parts.append(f"Settle: {settle_method}")
                description = "; ".join(description_parts)

                product = {
                    "id": f"bitget_fixed_{item.get('productId', f'{coin}_{lock_days}')}",
                    "symbol": coin,
                    "name": f"{coin} Fixed Savings ({lock_days} days)",
                    "provider": "bitget",
                    "apy": min_apy,
                    "max_apy": max_apy,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "lock_period_days": lock_days,
                    "product_type": "Fixed",
                    "is_active": True,
                    "risk_level": self._determine_risk_level(
                        item.get("productLevel", "normal"), coin
                    ),
                    "description": description,
                    "website_url": "https://www.bitget.com/earn",
                    "raw_data": item,
                }
                products.append(product)

            logger.info(f"[BitgetAPI] ✅ Отримано {len(products)} Fixed продуктів")
            return products

        except Exception as e:
            logger.error(f"[BitgetAPI] ❌ Помилка отримання Fixed продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        all_products = []

        try:
            logger.info("[BitgetAPI] 🔄 Початок отримання всіх Earn продуктів")

            flexible_products = await self.get_flexible_savings_products()
            all_products.extend(flexible_products)
            logger.info(f"[BitgetAPI] ✅ Flexible: {len(flexible_products)} продуктів")

            fixed_products = await self.get_locked_savings_products()
            all_products.extend(fixed_products)
            logger.info(f"[BitgetAPI] ✅ Fixed: {len(fixed_products)} продуктів")

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(
                        f"[BitgetAPI] Помилка нормалізації продукту {product.get('id')}: {norm_error}"
                    )
                    normalized_products.append(product)

            logger.info(
                f"[BitgetAPI] ✅ Всього агреговано {len(normalized_products)} Earn продуктів"
            )
            return normalized_products

        except Exception as e:
            logger.error(
                f"[BitgetAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True
            )
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        all_products = []

        try:
            logger.info(f"[BitgetAPI] 🔍 Пошук продуктів для {asset}")

            flexible_products = await self.get_flexible_savings_products(asset=asset)
            fixed_products = await self.get_locked_savings_products(asset=asset)

            all_products.extend(flexible_products)
            all_products.extend(fixed_products)

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[BitgetAPI] ✅ Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[BitgetAPI] ❌ Помилка пошуку продуктів для {asset}: {e}", exc_info=True)
            return []
