from typing import List, Dict, Optional, Any
import hmac
import hashlib
import base64
import datetime
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger
from app.utils.rate_limiter import rate_limiter


class OKXAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str = ""):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://www.okx.com")
        self.api_passphrase = api_passphrase

        if not rate_limiter.get_limiter("okx"):
            rate_limiter.create_limiter("okx", max_requests=3, per_seconds=1.0)

        logger.info(f"✅ OKXAPI ініціалізовано з URL: {self.base_url}")

    def _generate_timestamp(self) -> str:
        now = datetime.datetime.utcnow()

        timestamp = now.isoformat(timespec="milliseconds") + "Z"
        return timestamp

    def _generate_signature(
        self, timestamp: str, method: str, request_path: str, body: str = ""
    ) -> str:

        message = timestamp + method.upper() + request_path + body

        mac = hmac.new(self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)

        signature = base64.b64encode(mac.digest()).decode("utf-8")

        return signature

    def get_headers(
        self, method: str = "GET", request_path: str = "/", body: str = ""
    ) -> Dict[str, str]:
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(timestamp, method, request_path, body)

        headers = {
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.api_passphrase,
        }

        logger.debug(
            f"[OKXAPI] Headers generated: key={self.api_key[:8]}***, timestamp={timestamp}"
        )

        return headers

    async def _make_okx_request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Rate limiting
        await rate_limiter.acquire("okx", tokens=1, timeout=10.0)

        query_string = ""
        if params:
            query_string = "?" + urlencode(params)
        request_path = path + query_string

        headers = self.get_headers(method=method, request_path=request_path)

        response = await self._make_request(
            method=method, path=path, params=params, headers=headers
        )

        return response

    async def get_onchain_earn_products(
        self,
        product_id: Optional[str] = None,
        protocol_type: Optional[str] = None,
        ccy: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            path = "/api/v5/finance/staking-defi/offers"
            params = {}

            if product_id:
                params["productId"] = product_id
            if protocol_type:
                params["protocolType"] = protocol_type
            if ccy:
                params["ccy"] = ccy

            logger.info(f"[OKXAPI] Запит On-chain earn продуктів: params={params}")

            response = await self._make_okx_request("GET", path, params)

            code = response.get("code", "-1")
            if code != "0":
                error_msg = response.get("msg", "Unknown error")
                logger.error(f"[OKXAPI] Помилка API: code={code}, msg={error_msg}")
                return []

            data = response.get("data", [])
            if not data:
                logger.info("[OKXAPI] On-chain earn: немає доступних продуктів")
                return []

            products = []
            for item in data:
                try:
                    product = self._normalize_onchain_product(item)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації On-chain продукту: {e}")
                    continue

            logger.info(f"[OKXAPI] ✅ Отримано {len(products)} On-chain earn продуктів")
            return products

        except Exception as e:
            logger.warning(
                f"[OKXAPI] ⚠️ On-chain продукти недоступні (потрібна аутентифікація): {e}"
            )
            logger.info("[OKXAPI] ✅ Повертаємо порожній список On-chain продуктів")
            return []

    def _normalize_onchain_product(self, item: Dict[str, Any]) -> Dict[str, Any]:

        apy_raw = item.get("apy", "0")
        try:
            apy = float(apy_raw) * 100
        except:
            apy = 0.0

        term = item.get("term", "")
        lock_days = 0
        if term and term.isdigit():
            lock_days = int(term)

        min_amount = 0.0
        max_amount = None
        invest_data = item.get("investData", [])
        if invest_data and len(invest_data) > 0:
            first_invest = invest_data[0]
            try:
                min_amount = float(first_invest.get("minAmt", "0"))
            except:
                min_amount = 0.0

            max_amt_str = first_invest.get("maxAmt", "")
            if max_amt_str:
                try:
                    max_amount = float(max_amt_str)
                except:
                    max_amount = None

        state = item.get("state", "")
        is_active = state.lower() == "purchasable"

        product_id = item.get("productId", "")
        ccy = item.get("ccy", "")

        if not ccy:
            product_name = item.get("termName", item.get("name", ""))
            if "/" in product_name:
                ccy = product_name.split("/")[0].strip()
            elif " " in product_name:
                ccy = product_name.split(" ")[0].strip()
            else:
                ccy = product_name.strip()

        unified_id = f"okx_onchain_{product_id}"

        protocol = item.get("protocol", "")
        name = f"{ccy} On-chain Earn ({protocol})" if protocol else f"{ccy} On-chain Earn"

        product = {
            "id": unified_id,
            "symbol": ccy,
            "name": name,
            "provider": "OKX",
            "apy": apy,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "lock_period_days": lock_days,
            "product_type": "OnChain",
            "is_active": is_active,
            "risk_level": "Medium",
            "can_early_redeem": item.get("earlyRedeem", False),
            "protocol": protocol,
            "description": f"On-chain staking for {ccy} via {protocol}",
            "website_url": "https://www.okx.com/earn/onchain",
            "raw_data": item,
        }

        return product

    async def get_simple_earn_flexible_products(
        self, ccy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            path = "/api/v5/finance/savings/lending-rate-summary"
            params = {}

            if ccy:
                params["ccy"] = ccy

            logger.info(f"[OKXAPI] Запит Simple Earn Flexible продуктів: params={params}")

            response = await self._make_okx_request("GET", path, params)

            code = response.get("code", "-1")
            if code != "0":
                error_msg = response.get("msg", "Unknown error")
                logger.warning(f"[OKXAPI] Simple Earn недоступний: code={code}, msg={error_msg}")
                return []

            data = response.get("data", [])
            if not data:
                logger.info("[OKXAPI] Simple Earn: немає доступних продуктів")
                return []

            products = []
            for item in data:
                try:
                    product = self._normalize_simple_earn_product(item)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації Simple Earn продукту: {e}")
                    continue

            logger.info(f"[OKXAPI] ✅ Отримано {len(products)} Simple Earn продуктів")
            return products

        except Exception as e:
            logger.error(f"[OKXAPI] ❌ Помилка отримання Simple Earn продуктів: {e}", exc_info=True)
            return []

    def _normalize_simple_earn_product(self, item: Dict[str, Any]) -> Dict[str, Any]:

        rate_raw = (
            item.get("estRate")
            or item.get("avgRate")
            or item.get("preRate")
            or item.get("rate")
            or "0"
        )
        try:
            apy = float(rate_raw) * 100
        except:
            apy = 0.0

        try:
            min_amt_str = item.get("minAmt", "0")
            min_amount = float(min_amt_str) if min_amt_str else 0.0
        except:
            min_amount = 0.0

        max_amt_str = item.get("maxAmt", "")
        max_amount = None
        if max_amt_str:
            try:
                max_amount = float(max_amt_str)
            except:
                max_amount = None

        is_active = True

        ccy = item.get("ccy", "")
        unified_id = f"okx_simple_flex_{ccy}"
        name = f"{ccy} Simple Earn Flexible"

        product = {
            "id": unified_id,
            "symbol": ccy,
            "name": name,
            "provider": "OKX",
            "apy": apy,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "lock_period_days": 0,
            "product_type": "SimpleFlexible",
            "is_active": is_active,
            "risk_level": "Low",
            "can_early_redeem": True,
            "description": f"Simple Earn flexible savings for {ccy}",
            "website_url": "https://www.okx.com/earn/savings",
            "raw_data": item,
        }

        return product

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        all_products = []

        try:
            logger.info("[OKXAPI] Початок агрегації всіх Earn продуктів")

            onchain_products = await self.get_onchain_earn_products()
            all_products.extend(onchain_products)
            logger.info(f"[OKXAPI] ✅ On-chain: {len(onchain_products)} продуктів")

            simple_earn_products = await self.get_simple_earn_flexible_products()
            all_products.extend(simple_earn_products)
            logger.info(f"[OKXAPI] ✅ Simple Earn: {len(simple_earn_products)} продуктів")

            normalized = []
            for product in all_products:
                try:
                    norm_product = self.normalize_earn_product(product)
                    normalized.append(norm_product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації: {e}")
                    normalized.append(product)

            logger.info(f"[OKXAPI] ✅ Агреговано {len(normalized)} продуктів")
            return normalized

        except Exception as e:
            logger.error(f"[OKXAPI] ❌ Помилка агрегації Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        try:
            all_products = []

            onchain = await self.get_onchain_earn_products(ccy=asset)
            all_products.extend(onchain)

            simple = await self.get_simple_earn_flexible_products(ccy=asset)
            all_products.extend(simple)

            logger.info(f"[OKXAPI] Знайдено {len(all_products)} продуктів для {asset}")
            return all_products

        except Exception as e:
            logger.error(f"[OKXAPI] Помилка отримання продуктів для {asset}: {e}")
            return []

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.get_simple_earn_flexible_products(ccy=asset)

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.get_onchain_earn_products(ccy=asset)
