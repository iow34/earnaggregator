from typing import List, Dict, Optional, Any
import hmac
import hashlib
import time
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class BinanceAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.binance.com")

    def get_headers(self) -> Dict[str, str]:
        return {"X-MBX-APIKEY": self.api_key, "Content-Type": "application/json"}

    def _generate_signature(self, params: Dict[str, Any]) -> str:

        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _prepare_signed_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}

        params.setdefault("timestamp", int(time.time() * 1000))

        sign = self._generate_signature(params)
        params["signature"] = sign
        return params

    @staticmethod
    def _extract_list_from_response(resp: Any, candidates: List[str]) -> List[Dict[str, Any]]:
        if resp is None:
            return []
        if isinstance(resp, list):
            return resp
        if not isinstance(resp, dict):
            return []

        for key in candidates:
            v = resp.get(key)
            if isinstance(v, list):
                return v

            if isinstance(v, dict):
                for subkey in candidates:
                    subv = v.get(subkey)
                    if isinstance(subv, list):
                        return subv

        for key in ["rows", "productList", "list", "data", "result"]:
            val = resp.get(key)
            if isinstance(val, list):
                return val

        return []

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/sapi/v1/simple-earn/flexible/list"
            params: Dict[str, Any] = {"current": current, "size": size}
            if asset:
                params["asset"] = asset

            signed_params = self._prepare_signed_params(params)

            headers = self.get_headers()
            resp = await self._make_request("GET", path, params=signed_params, headers=headers)

            rows = self._extract_list_from_response(resp, ["rows", "data", "list"])
            products: List[Dict[str, Any]] = []

            for item in rows:
                apy_raw = (
                    item.get("latestAnnualPercentageRate")
                    or item.get("annualPercentageRate")
                    or item.get("annualizedRate")
                )
                try:
                    apy = float(apy_raw) * 100 if apy_raw is not None else 0.0
                except Exception:
                    try:
                        apy = float(str(apy_raw).replace("%", ""))
                    except Exception:
                        apy = 0.0

                product = {
                    "id": f"binance_simple_flex_{item.get('productId', item.get('asset', ''))}",
                    "symbol": item.get("asset") or item.get("assetName") or "",
                    "name": f"{item.get('asset', '')} Flexible Savings",
                    "provider": "Binance",
                    "apy": apy,
                    "min_amount": float(
                        item.get("minPurchaseAmount") or item.get("minPurchaseAmt") or 0
                    ),
                    "lock_period_days": 0,
                    "is_active": bool(item.get("canPurchase", False)),
                    "description": item.get("assetDescription") or item.get("asset", ""),
                    "website_url": "https://www.binance.com/en/earn",
                    "raw_data": item,
                }
                products.append(product)

            return products

        except Exception as e:
            logger.error(f"[BinanceAPI] Помилка отримання Flexible Savings: {e}")
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            path = "/sapi/v1/simple-earn/locked/list"
            params: Dict[str, Any] = {"current": current, "size": size}
            if asset:
                params["asset"] = asset

            signed_params = self._prepare_signed_params(params)
            headers = self.get_headers()
            resp = await self._make_request("GET", path, params=signed_params, headers=headers)

            rows = self._extract_list_from_response(resp, ["rows", "data", "list"])
            products: List[Dict[str, Any]] = []
            skipped_symbols = []

            for item in rows:
                detail = item.get("detail", item)

                apy_raw = (
                    detail.get("apr")
                    or detail.get("annualizedRate")
                    or detail.get("annualPercentageRate")
                    or detail.get("latestAnnualPercentageRate")
                )
                try:
                    apy = float(apy_raw) if apy_raw is not None else 0.0
                except Exception:
                    try:
                        apy = float(str(apy_raw).replace("%", ""))
                    except Exception:
                        apy = 0.0

                symbol = detail.get("asset") or detail.get("assetName") or item.get("asset") or ""

                if len(symbol) < 2:
                    skipped_symbols.append(f"{symbol}:{item.get('projectId')}")
                    continue

                product = {
                    "id": f"binance_simple_locked_{item.get('projectId', item.get('productId', ''))}",
                    "symbol": symbol,
                    "name": f"{symbol} Locked Savings ({detail.get('duration', 0)} days)",
                    "provider": "Binance",
                    "apy": apy,
                    "min_amount": float(item.get("quota", {}).get("minimum", 0)),
                    "lock_period_days": int(detail.get("duration") or detail.get("term") or 0),
                    "is_active": detail.get("status", "").upper() == "PURCHASING",
                    "description": f"Locked savings for {symbol}",
                    "website_url": "https://www.binance.com/en/earn",
                    "raw_data": item,
                }
                products.append(product)

            if skipped_symbols:
                logger.warning(
                    f"[BinanceAPI] Пропущено {len(skipped_symbols)} Locked продуктів з невалідними символами: {', '.join(skipped_symbols[:5])}{'...' if len(skipped_symbols) > 5 else ''}"
                )

            return products

        except Exception as e:
            logger.error(f"[BinanceAPI] Помилка отримання Locked Savings: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        all_products: List[Dict[str, Any]] = []
        try:
            logger.info("[BinanceAPI] Початок отримання Flexible продуктів...")
            flexible_all = []
            current_page = 1
            max_pages = 50

            while current_page <= max_pages:
                flexible_page = await self.get_flexible_savings_products(
                    current=current_page, size=100
                )

                if not flexible_page:
                    logger.info(
                        f"[BinanceAPI] Flexible: сторінка {current_page} порожня, завершуємо"
                    )
                    break

                flexible_all.extend(flexible_page)
                logger.info(
                    f"[BinanceAPI] Flexible: сторінка {current_page} - отримано {len(flexible_page)} продуктів (всього: {len(flexible_all)})"
                )

                if len(flexible_page) < 100:
                    logger.info(
                        f"[BinanceAPI] Flexible: отримано менше 100 продуктів, це остання сторінка"
                    )
                    break

                current_page += 1

            all_products.extend(flexible_all)
            logger.info(
                f"[BinanceAPI] ✅ Flexible продукти завершено: {len(flexible_all)} продуктів"
            )

            logger.info("[BinanceAPI] Початок отримання Locked продуктів...")
            locked_all = []
            current_page = 1
            max_pages = 50

            while current_page <= max_pages:
                locked_page = await self.get_locked_savings_products(current=current_page, size=100)

                if not locked_page:
                    logger.info(f"[BinanceAPI] Locked: сторінка {current_page} порожня, завершуємо")
                    break

                locked_all.extend(locked_page)
                logger.info(
                    f"[BinanceAPI] Locked: сторінка {current_page} - отримано {len(locked_page)} продуктів (всього: {len(locked_all)})"
                )

                if len(locked_page) < 100:
                    logger.info(
                        f"[BinanceAPI] Locked: отримано менше 100 продуктів, це остання сторінка"
                    )
                    break

                current_page += 1

            all_products.extend(locked_all)
            logger.info(f"[BinanceAPI] ✅ Locked продукти завершено: {len(locked_all)} продуктів")

            normalized: List[Dict[str, Any]] = []
            for p in all_products:
                try:
                    normalized.append(self.normalize_earn_product(p))
                except Exception:
                    normalized.append(p)

            logger.info(
                f"[BinanceAPI] ✅ Агреговано {len(normalized)} Earn продуктів (Flexible: {len(flexible_all)}, Locked: {len(locked_all)})"
            )
            return normalized

        except Exception as e:
            logger.error(f"[BinanceAPI] ❌ Помилка агрегування Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        try:
            all_products = await self.get_earn_products()
            filtered = [p for p in all_products if p.get("symbol", "").upper() == asset.upper()]
            return filtered
        except Exception as e:
            logger.error(f"[BinanceAPI] Помилка фільтрації Earn продуктів по asset={asset}: {e}")
            return []
