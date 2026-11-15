from typing import List, Dict, Optional, Any
import hmac
import hashlib
import time
from urllib.parse import urlencode, urljoin

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class GateAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key, api_secret=api_secret, base_url="https://api.gateio.ws/api/v4"
        )

    def get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def _generate_signature(
        self,
        method: str,
        path: str,
        query_string: str = "",
        body: str = "",
        timestamp: Optional[int] = None,
    ) -> tuple[Dict[str, str], int]:

        if timestamp is None:
            timestamp = int(time.time())

        body_hash = hashlib.sha512(body.encode("utf-8")).hexdigest()

        message = f"{method}\n{path}\n{query_string}\n{body_hash}\n{timestamp}"

        signature = hmac.new(
            self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha512
        ).hexdigest()

        auth_headers = {"KEY": self.api_key, "Timestamp": str(timestamp), "SIGN": signature}

        return auth_headers, timestamp

    async def get_uni_currencies(self, page: int = 1, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            path = "earn/uni/currencies"
            method = "GET"

            params = {}
            if page > 1:
                params["page"] = page
            if limit != 100:
                params["limit"] = limit

            logger.info(f"[GateAPI] Запит Uni Lend currencies (page={page}, limit={limit})")

            await self._ensure_client()

            url = urljoin(self.base_url + "/", path.lstrip("/"))

            request_headers = {"Content-Type": "application/json", "Accept": "application/json"}

            logger.debug(f"[GateAPI] {method} {url} params={params}")

            response = await self.client.request(
                method=method, url=url, params=params, headers=request_headers
            )

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                logger.info(f"[GateAPI] Отримано {len(data)} Uni Lend currencies")
                return data

            logger.warning(f"[GateAPI] Неочікувана структура відповіді: {type(data)}")
            return []

        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання Uni Lend currencies: {e}")
            return []

    async def get_uni_rates(self) -> List[Dict[str, Any]]:
        try:
            path = "earn/uni/rate"
            method = "GET"

            logger.info(f"[GateAPI] Запит Uni Lend estimated rates")

            await self._ensure_client()

            url = urljoin(self.base_url + "/", path.lstrip("/"))

            request_headers = {"Content-Type": "application/json", "Accept": "application/json"}

            logger.debug(f"[GateAPI] {method} {url}")

            response = await self.client.request(method=method, url=url, headers=request_headers)

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                logger.info(f"[GateAPI] Отримано {len(data)} Uni Lend estimated rates")
                return data

            logger.warning(f"[GateAPI] Неочікувана структура відповіді: {type(data)}")
            return []

        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання Uni Lend estimated rates: {e}")
            return []

    async def get_uni_currency(self, currency: str) -> Optional[Dict[str, Any]]:
        try:
            path = f"/api/v4/earn/uni/currencies/{currency}"
            method = "GET"

            auth_headers, timestamp = self._generate_signature(
                method=method, path=path, query_string="", body=""
            )

            headers = self.get_headers()
            headers.update(auth_headers)

            logger.info(f"[GateAPI] Запит деталей Uni Lend currency: {currency}")

            data = await self._make_request(method=method, path=path, headers=headers)

            return data

        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання деталей {currency}: {e}")
            return None

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"[GateAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''}")

            rates_data = await self.get_uni_rates()

            currencies_data = await self.get_uni_currencies(page=current, limit=size)

            if not rates_data:
                logger.warning("[GateAPI] Не отримано estimated rates для Flexible продуктів")
                return []

            currencies_dict = {c.get("currency", ""): c for c in currencies_data}

            if asset:
                rates_data = [
                    r for r in rates_data if r.get("currency", "").upper() == asset.upper()
                ]

            products = []
            for item in rates_data:
                try:
                    est_rate_str = item.get("est_rate", "0")
                    apy = float(est_rate_str) * 100 if est_rate_str else 0.0

                    currency = item.get("currency", "")

                    currency_info = currencies_dict.get(currency, {})

                    min_amount_str = currency_info.get("min_lend_amount", "0")
                    min_amount = float(min_amount_str) if min_amount_str else 0.0

                    max_amount_str = currency_info.get("max_lend_amount", "")

                    if max_amount_str and max_amount_str.isdigit():
                        max_amount_val = float(max_amount_str)
                        max_amount = max_amount_val if max_amount_val < 1000000 else None
                    else:
                        max_amount = None

                    is_active = True

                    product = {
                        "id": f"gate_flexible_{currency}",
                        "symbol": currency,
                        "name": f"{currency} Flexible Savings",
                        "provider": "gate",
                        "apy": apy,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                        "lock_period_days": 0,
                        "product_type": "Flexible",
                        "is_active": is_active,
                        "risk_level": "Low",
                        "description": f"Gate.io Uni Lend Flexible Savings for {currency}",
                        "website_url": "https://www.gate.com/simple-earn",
                        "raw_data": item,
                    }

                    products.append(product)

                except Exception as parse_error:
                    logger.warning(
                        f"[GateAPI] Помилка парсингу продукту {item.get('currency')}: {parse_error}"
                    )
                    continue

            logger.info(f"[GateAPI] ✅ Нормалізовано {len(products)} Flexible продуктів")
            return products

        except Exception as e:
            logger.error(f"[GateAPI] ❌ Помилка отримання Flexible продуктів: {e}")
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        logger.info("[GateAPI] Fixed Savings доступні тільки через manual JSON import")
        return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        try:
            logger.info("[GateAPI] Початок отримання всіх Earn продуктів")

            flexible_products = await self.get_flexible_savings_products()
            logger.info(f"[GateAPI] ✅ Отримано {len(flexible_products)} Flexible продуктів")

            normalized_products = []
            for product in flexible_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(f"[GateAPI] Помилка нормалізації продукту: {norm_error}")
                    normalized_products.append(product)

            logger.info(f"[GateAPI] ✅ Агреговано {len(normalized_products)} Earn продуктів")
            return normalized_products

        except Exception as e:
            logger.error(f"[GateAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"[GateAPI] Запит Earn продуктів для {asset}")

            flexible_products = await self.get_flexible_savings_products(asset=asset)

            normalized_products = []
            for product in flexible_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[GateAPI] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[GateAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []
