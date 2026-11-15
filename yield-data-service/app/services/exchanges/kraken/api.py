from typing import List, Dict, Optional, Any
import hmac
import hashlib
import time
import base64
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger


try:
    from kraken.spot.earn import Earn as KrakenEarnSDK  # python-kraken-sdk >= 3.x
except Exception:
    KrakenEarnSDK = None


class KrakenAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.kraken.com")

    def get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/x-www-form-urlencoded", "API-Key": self.api_key}

    def _generate_signature(self, urlpath: str, data: Dict[str, Any], nonce: str) -> str:
        try:
            postdata = urlencode(data)
            encoded = (nonce + postdata).encode("utf-8")

            message = urlpath.encode("utf-8") + hashlib.sha256(encoded).digest()

            secret_decoded = base64.b64decode(self.api_secret)
            signature = hmac.new(secret_decoded, message, hashlib.sha512)

            return base64.b64encode(signature.digest()).decode("utf-8")

        except Exception as e:
            logger.error(f"[KrakenAPI] Помилка генерації підпису: {e}")
            raise

    async def _make_kraken_request(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        await self._ensure_client()

        nonce = str(int(time.time() * 1000))

        data = params or {}
        data["nonce"] = nonce

        signature = self._generate_signature(path, data, nonce)

        headers = self.get_headers()
        headers["API-Sign"] = signature

        url = self.base_url + path

        logger.debug(f"[KrakenAPI] POST {path} params={list(data.keys())}")

        try:
            response = await self.client.post(url=url, data=data, headers=headers)

            response.raise_for_status()
            result = response.json()

            if result.get("error") and len(result["error"]) > 0:
                error_msg = ", ".join(result["error"])
                logger.error(f"[KrakenAPI] API помилка: {error_msg}")
                raise Exception(f"Kraken API error: {error_msg}")

            return result.get("result", {})

        except Exception as e:
            logger.error(f"[KrakenAPI] Помилка запиту до {path}: {e}")
            raise

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        all_products: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        try:
            if KrakenEarnSDK is not None:
                logger.info("[KrakenAPI] Використовую python-kraken-sdk для Flexible")
                client = KrakenEarnSDK(key=self.api_key, secret=self.api_secret)
                while True:
                    result = client.list_earn_strategies(
                        asset=asset.upper() if asset else None, limit=size, cursor=cursor
                    )

                    if isinstance(result, dict):
                        items = (
                            (result.get("result") or {}).get("items") or result.get("items") or []
                        )
                        next_cursor = (result.get("result") or {}).get("next_cursor") or result.get(
                            "next_cursor"
                        )
                    else:
                        items = list(result) if result else []
                        next_cursor = None

                    if not items:
                        logger.info("[KrakenAPI] Немає елементів (manual flex)")
                        return all_products

                    for item in items:
                        if not item.get("can_allocate", False):
                            continue

                        lock_type = item.get("lock_type", {})
                        if isinstance(lock_type, dict) and lock_type.get("type") not in [
                            "flex",
                            "instant",
                        ]:
                            continue

                        try:
                            rate_str = (item.get("apr_estimate") or {}).get("low", "0")

                            apy = float(rate_str) if rate_str is not None else 0.0
                            min_amount = float(item.get("allocation_fee", 0) or 0)
                            max_amount = None
                            cap = item.get("user_cap")
                            if cap and cap != "unlimited":
                                try:
                                    max_amount = float(cap)
                                except Exception:
                                    max_amount = None

                            all_products.append(
                                {
                                    "id": f"kraken_flex_{item.get('id', '')}",
                                    "symbol": (item.get("asset") or "").upper(),
                                    "name": f"{item.get('asset', '')} Flexible Staking",
                                    "provider": "Kraken",
                                    "apy": apy,
                                    "min_amount": min_amount,
                                    "max_amount": max_amount,
                                    "lock_period_days": 0,
                                    "product_type": "Flexible",
                                    "is_active": True,
                                    "description": item.get("description")
                                    or f"Flexible staking for {item.get('asset', '')}",
                                    "website_url": "https://www.kraken.com/earn",
                                    "raw_data": item,
                                }
                            )
                        except Exception as e:
                            logger.warning(f"[KrakenAPI] Помилка парсингу (SDK) Flexible: {e}")
                            continue

                    if not next_cursor:
                        break
                    cursor = next_cursor
                    await self._rate_limit_delay()

            else:
                path = "/0/private/Earn/Strategies"
                while True:
                    params: Dict[str, Any] = {"limit": size, "lock_type": ["flex"]}
                    if asset:
                        params["asset"] = asset.upper()
                    if cursor:
                        params["cursor"] = cursor

                    logger.info(
                        f"[KrakenAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''} (cursor: {cursor or 'start'})"
                    )
                    try:
                        result = await self._make_kraken_request(path, params)
                    except Exception as e:
                        if "Invalid arguments" in str(e):
                            logger.warning(
                                "[KrakenAPI] Invalid arguments для lock_type, повтор без lock_type"
                            )
                            fallback_params = dict(params)
                            fallback_params.pop("lock_type", None)
                            result = await self._make_kraken_request(path, fallback_params)
                        else:
                            raise

                    items = result.get("items", [])
                    next_cursor = result.get("next_cursor")
                    if not items:
                        break

                for item in items:
                    if not item.get("can_allocate", False):
                        continue
                    try:
                        rate_str = (item.get("apr_estimate") or {}).get("low", "0")
                        try:
                            apy = float(rate_str)
                        except Exception:
                            apy = 0.0

                        min_amount_str = item.get("allocation_fee", "0")
                        try:
                            min_amount = float(min_amount_str)
                        except Exception:
                            min_amount = 0.0

                        max_amount = None
                        max_amount_str = item.get("user_cap")
                        if max_amount_str and max_amount_str != "unlimited":
                            try:
                                max_amount = float(max_amount_str)
                            except Exception:
                                max_amount = None

                        product = {
                            "id": f"kraken_flex_{item.get('id', '')}",
                            "symbol": item.get("asset", "").upper(),
                            "name": f"{item.get('asset', '')} Flexible Staking",
                            "provider": "Kraken",
                            "apy": apy,
                            "min_amount": min_amount,
                            "max_amount": max_amount,
                            "lock_period_days": 0,
                            "product_type": "Flexible",
                            "is_active": True,
                            "description": item.get("description")
                            or f"Flexible staking for {item.get('asset', '')}",
                            "website_url": "https://www.kraken.com/earn",
                            "raw_data": item,
                        }
                        all_products.append(product)
                    except Exception as e:
                        logger.warning(f"[KrakenAPI] Помилка парсингу Flexible продукту: {e}")
                        continue

                if not next_cursor:
                    logger.info("[KrakenAPI] Досягнуто кінця сторінок (manual flex)")
                    return all_products
                cursor = next_cursor
                await self._rate_limit_delay()

            logger.info(f"[KrakenAPI] ✅ Отримано {len(all_products)} Flexible продуктів")
            return all_products
        except Exception as e:
            logger.error(f"[KrakenAPI] ❌ Помилка отримання Flexible продуктів: {e}")
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        all_products: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        try:
            if KrakenEarnSDK is not None:
                logger.info("[KrakenAPI] Використовую python-kraken-sdk для Bonded")
                client = KrakenEarnSDK(key=self.api_key, secret=self.api_secret)
                while True:
                    result = client.list_earn_strategies(
                        asset=asset.upper() if asset else None, limit=size, cursor=cursor
                    )
                    if isinstance(result, dict):
                        items = (
                            (result.get("result") or {}).get("items") or result.get("items") or []
                        )
                        next_cursor = (result.get("result") or {}).get("next_cursor") or result.get(
                            "next_cursor"
                        )
                    else:
                        items = list(result) if result else []
                        next_cursor = None

                    if not items:
                        logger.info("[KrakenAPI] Немає елементів (SDK bonded)")
                        return all_products

                    for item in items:
                        if not item.get("can_allocate", False):
                            continue

                        lock_type = item.get("lock_type", {})
                        if isinstance(lock_type, dict) and lock_type.get("type") != "bonded":
                            continue

                        try:
                            lock_type_info = item.get("lock_type", {})
                            bonding_period = lock_type_info.get("bonding_period", 0)
                            try:
                                lock_days = int(bonding_period)
                            except Exception:
                                lock_days = 0
                            if lock_days <= 0:
                                continue

                            rate_str = (item.get("apr_estimate") or {}).get("low", "0")

                            apy = float(rate_str) if rate_str is not None else 0.0
                            min_amount = float(item.get("allocation_fee", 0) or 0)
                            max_amount = None
                            cap = item.get("user_cap")
                            if cap and cap != "unlimited":
                                try:
                                    max_amount = float(cap)
                                except Exception:
                                    max_amount = None

                            product = {
                                "id": f"kraken_bonded_{item.get('id', '')}",
                                "symbol": (item.get("asset") or "").upper(),
                                "name": f"{item.get('asset', '')} Bonded Staking ({lock_days} days)",
                                "provider": "Kraken",
                                "apy": apy,
                                "min_amount": min_amount,
                                "max_amount": max_amount,
                                "lock_period_days": lock_days,
                                "product_type": "Fixed",
                                "is_active": True,
                                "description": f"Bonded staking for {item.get('asset', '')} with {lock_days} days lock period",
                                "website_url": "https://www.kraken.com/earn",
                                "raw_data": item,
                            }
                            all_products.append(product)
                        except Exception as e:
                            logger.warning(f"[KrakenAPI] Помилка парсингу (SDK) Bonded: {e}")
                            continue

                    if not next_cursor:
                        break
                    cursor = next_cursor
                    await self._rate_limit_delay()

            else:
                path = "/0/private/Earn/Strategies"

                while True:
                    params: Dict[str, Any] = {"limit": size, "lock_type": ["bonded"]}
                    if asset:
                        params["asset"] = asset.upper()
                    if cursor:
                        params["cursor"] = cursor

                    logger.info(
                        f"[KrakenAPI] Запит Bonded продуктів{f' для {asset}' if asset else ''} (cursor: {cursor or 'start'})"
                    )
                    result = await self._make_kraken_request(path, params)

                    items = result.get("items", [])
                    next_cursor = result.get("next_cursor")
                    if not items:
                        logger.info("[KrakenAPI] Немає елементів (manual bonded)")
                        return all_products

                for item in items:
                    if not item.get("can_allocate", False):
                        continue
                    try:
                        lock_type_info = item.get("lock_type", {})
                        bonding_period = lock_type_info.get("bonding_period", 0)
                        try:
                            lock_days = int(bonding_period)
                        except Exception:
                            lock_days = 0
                        if lock_days <= 0:
                            continue

                        rate_str = (item.get("apr_estimate") or {}).get("low", "0")
                        try:
                            apy = float(rate_str)
                        except Exception:
                            apy = 0.0

                        min_amount_str = item.get("allocation_fee", "0")
                        try:
                            min_amount = float(min_amount_str)
                        except Exception:
                            min_amount = 0.0

                        max_amount = None
                        max_amount_str = item.get("user_cap")
                        if max_amount_str and max_amount_str != "unlimited":
                            try:
                                max_amount = float(max_amount_str)
                            except Exception:
                                max_amount = None

                        product = {
                            "id": f"kraken_bonded_{item.get('id', '')}",
                            "symbol": item.get("asset", "").upper(),
                            "name": f"{item.get('asset', '')} Bonded Staking ({lock_days} days)",
                            "provider": "Kraken",
                            "apy": apy,
                            "min_amount": min_amount,
                            "max_amount": max_amount,
                            "lock_period_days": lock_days,
                            "product_type": "Fixed",
                            "is_active": True,
                            "description": f"Bonded staking for {item.get('asset', '')} with {lock_days} days lock period",
                            "website_url": "https://www.kraken.com/earn",
                            "raw_data": item,
                        }
                        all_products.append(product)
                    except Exception as e:
                        logger.warning(f"[KrakenAPI] Помилка парсингу Bonded продукту: {e}")
                        continue

                if not next_cursor:
                    logger.info("[KrakenAPI] Досягнуто кінця сторінок (manual bonded)")
                    return all_products
                cursor = next_cursor
                await self._rate_limit_delay()

            logger.info(f"[KrakenAPI] ✅ Отримано {len(all_products)} Bonded продуктів")
            return all_products
        except Exception as e:
            logger.error(f"[KrakenAPI] ❌ Помилка отримання Bonded продуктів: {e}")
            return []

    async def test_other_endpoints(self) -> Dict[str, Any]:
        results = {}
        try:
            if KrakenEarnSDK is not None:
                logger.info("[KrakenAPI] Тестую інші приватні ендпоінти...")
                client = KrakenEarnSDK(key=self.api_key, secret=self.api_secret)

                try:
                    from kraken.spot.user import User

                    user_client = User(key=self.api_key, secret=self.api_secret)
                    balance = user_client.get_account_balance()
                    results["balance"] = {
                        "status": "success",
                        "count": len(balance) if balance else 0,
                    }
                except Exception as e:
                    results["balance"] = {"status": "error", "error": str(e)}

                try:
                    from kraken.spot.trade import Trade

                    trade_client = Trade(key=self.api_key, secret=self.api_secret)
                    trade_balance = trade_client.get_trade_balance()
                    results["trade_balance"] = {
                        "status": "success",
                        "count": len(trade_balance) if trade_balance else 0,
                    }
                except Exception as e:
                    results["trade_balance"] = {"status": "error", "error": str(e)}

                try:
                    alloc_status = client.get_allocation_status()
                    results["allocation_status"] = {
                        "status": "success",
                        "count": len(alloc_status) if alloc_status else 0,
                    }
                except Exception as e:
                    results["allocation_status"] = {"status": "error", "error": str(e)}
            else:
                results["sdk"] = {"status": "error", "error": "SDK не доступний"}
        except Exception as e:
            results["general"] = {"status": "error", "error": str(e)}
        return results

    async def test_different_strategies(self) -> Dict[str, Any]:
        results = {}

        if KrakenEarnSDK is None:
            return {"error": "SDK не доступний"}

        client = KrakenEarnSDK(key=self.api_key, secret=self.api_secret)

        test_cases = [
            {"name": "flex_only", "lock_type": ["flex"]},
            {"name": "bonded_only", "lock_type": ["bonded"]},
            {"name": "all_lock_types", "lock_type": ["flex", "bonded", "timed", "instant"]},
            {"name": "no_lock_type", "lock_type": None},
            {"name": "with_asset_ETH", "lock_type": ["flex"], "asset": "ETH"},
            {"name": "with_asset_BTC", "lock_type": ["flex"], "asset": "BTC"},
        ]

        for test_case in test_cases:
            try:
                logger.info(f"[KrakenAPI] Тестую: {test_case['name']}")
                params = {"limit": 10}
                if test_case.get("lock_type"):
                    params["lock_type"] = test_case["lock_type"]
                if test_case.get("asset"):
                    params["asset"] = test_case["asset"]

                result = client.list_earn_strategies(**params)
                count = 0
                if isinstance(result, dict):
                    items = (result.get("result") or {}).get("items") or result.get("items") or []
                    count = len(items)
                elif result:
                    count = len(list(result))

                results[test_case["name"]] = {"status": "success", "count": count, "params": params}
                logger.info(f"[KrakenAPI] {test_case['name']}: знайдено {count} продуктів")

            except Exception as e:
                results[test_case["name"]] = {"status": "error", "error": str(e), "params": params}
                logger.warning(f"[KrakenAPI] {test_case['name']}: помилка - {e}")

        return results

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        all_products = []

        try:
            if KrakenEarnSDK is None:
                logger.error("[KrakenAPI] SDK не доступний")
                return []

            logger.info("[KrakenAPI] 🔄 Отримуємо всі Earn продукти без lock_type фільтра...")
            client = KrakenEarnSDK(key=self.api_key, secret=self.api_secret)

            cursor = None
            while True:
                result = client.list_earn_strategies(limit=100, cursor=cursor)

                if isinstance(result, dict):
                    items = (result.get("result") or {}).get("items") or result.get("items") or []
                    next_cursor = (result.get("result") or {}).get("next_cursor") or result.get(
                        "next_cursor"
                    )
                else:
                    items = list(result) if result else []
                    next_cursor = None

                if not items:
                    break

                for item in items:
                    if not item.get("can_allocate", False):
                        continue

                    try:
                        lock_type_info = item.get("lock_type", {})
                        if isinstance(lock_type_info, dict):
                            lock_type = lock_type_info.get("type", "")
                        else:
                            lock_type = str(lock_type_info)

                        if lock_type in ["flex", "instant"]:
                            product_type = "Flexible"
                            lock_days = 0
                        elif lock_type == "bonded":
                            product_type = "Bonded"
                            bonding_period = lock_type_info.get("bonding_period", 0)
                            try:
                                lock_days = int(bonding_period / 86400) if bonding_period > 0 else 0
                            except Exception:
                                lock_days = 0
                        else:
                            continue

                        rate_str = (item.get("apr_estimate") or {}).get("low", "0")
                        try:
                            apy = float(rate_str)
                        except Exception:
                            apy = 0.0

                        min_amount_str = item.get("allocation_fee", "0")
                        try:
                            min_amount = float(min_amount_str)
                        except Exception:
                            min_amount = 0.0

                        max_amount = None
                        max_amount_str = item.get("user_cap")
                        if max_amount_str and max_amount_str != "unlimited":
                            try:
                                max_amount = float(max_amount_str)
                            except Exception:
                                max_amount = None

                        product = {
                            "id": f"kraken_{lock_type}_{item.get('id', '')}",
                            "symbol": item.get("asset", "").upper(),
                            "name": f"{item.get('asset', '')} {product_type} Staking",
                            "provider": "Kraken",
                            "apy": apy,
                            "min_amount": min_amount,
                            "max_amount": max_amount,
                            "lock_period_days": lock_days,
                            "product_type": product_type,
                            "is_active": True,
                            "description": item.get("description")
                            or f"{product_type} staking for {item.get('asset', '')}",
                            "website_url": "https://www.kraken.com/earn",
                            "raw_data": item,
                        }
                        all_products.append(product)

                    except Exception as e:
                        logger.warning(f"[KrakenAPI] Помилка парсингу продукту: {e}")
                        continue

                if not next_cursor:
                    break
                cursor = next_cursor
                await self._rate_limit_delay()

            logger.info(f"[KrakenAPI] ✅ Отримано {len(all_products)} Earn продуктів")
            return all_products

        except Exception as e:
            logger.error(
                f"[KrakenAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True
            )
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        all_products = []

        try:
            flexible_products = await self.get_flexible_savings_products(asset=asset)
            bonded_products = await self.get_locked_savings_products(asset=asset)

            all_products.extend(flexible_products)
            all_products.extend(bonded_products)

            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[KrakenAPI] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[KrakenAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []

    async def _rate_limit_delay(self):
        import asyncio

        await asyncio.sleep(0.6)
