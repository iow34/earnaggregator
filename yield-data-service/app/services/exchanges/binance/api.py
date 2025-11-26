"""
Інтеграція з Binance API для отримання Earn продуктів.

Binance надає кілька типів Earn продуктів:
- Simple Earn Flexible (гнучкі заощадження)    -> GET /sapi/v1/simple-earn/flexible/list
- Simple Earn Locked (фіксовані заощадження)    -> GET /sapi/v1/simple-earn/locked/list
"""

from typing import List, Dict, Optional, Any
import hmac
import hashlib
import time
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class BinanceAPI(BaseExchange):
    """
    Клієнт для роботи з Binance API.

    Використовує актуальні endpoints Simple Earn (Flexible та Locked).
    """

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://api.binance.com"
        )

    def get_headers(self) -> Dict[str, str]:
        """
        Заголовки для запитів до Binance (публічні/підписані).
        """
        return {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Генерує HMAC SHA256 підпис для Binance (використовується для USER_DATA endpoints).
        """
        # Якщо params порожній — все одно включаємо timestamp (Binance вимагає timestamp)
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _prepare_signed_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Додає timestamp та підпис до params для підписаних endpoint-ів.
        """
        if params is None:
            params = {}
        # Binance потребує timestamp (в мс)
        params.setdefault("timestamp", int(time.time() * 1000))
        # Не модифікуємо params після підпису; створимо копію для підписування
        sign = self._generate_signature(params)
        params["signature"] = sign
        return params

    @staticmethod
    def _extract_list_from_response(resp: Any, candidates: List[str]) -> List[Dict[str, Any]]:
        """
        Корисна утиліта: зменшує boilerplate — шукає список продуктів у відповіді.
        Шукає ключі з candidates (наприклад 'rows', 'productList', 'data', 'result').
        Повертає list (може бути порожнім).
        """
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
            # іноді структура: {"data": {"rows": [...]}}
            if isinstance(v, dict):
                for subkey in candidates:
                    subv = v.get(subkey)
                    if isinstance(subv, list):
                        return subv

        # fallback: якщо є "rows" глибше
        for key in ['rows', 'productList', 'list', 'data', 'result']:
            # рекурсивний пошук простого виду
            val = resp.get(key)
            if isinstance(val, list):
                return val

        return []

    async def get_flexible_savings_products(self, asset: Optional[str] = None, current: int = 1, size: int = 100) -> List[Dict[str, Any]]:
        """
        Отримує Simple Earn Flexible products (коректний endpoint: /sapi/v1/simple-earn/flexible/list).

        Параметри:
            asset: (опціонально) символ токена (BTC, ETH...)
            current: сторінка (починається з 1)
            size: розмір сторінки (max 100)
        """
        try:
            path = "/sapi/v1/simple-earn/flexible/list"
            params: Dict[str, Any] = {"current": current, "size": size}
            if asset:
                params["asset"] = asset

            # це USER_DATA endpoint — підписуємо запит
            signed_params = self._prepare_signed_params(params)

            headers = self.get_headers()
            resp = await self._make_request("GET", path, params=signed_params, headers=headers)

            rows = self._extract_list_from_response(resp, ["rows", "data", "list"])
            products: List[Dict[str, Any]] = []

            for item in rows:
                # за прикладом офіційної відповіді: 'latestAnnualPercentageRate'
                apy_raw = item.get("latestAnnualPercentageRate") or item.get("annualPercentageRate") or item.get("annualizedRate")
                try:
                    apy = float(apy_raw) * 100 if apy_raw is not None else 0.0
                except Exception:
                    # якщо вже у відсотках або рядок із символом
                    try:
                        apy = float(str(apy_raw).replace('%', ''))
                    except Exception:
                        apy = 0.0

                product = {
                    "id": f"binance_simple_flex_{item.get('productId', item.get('asset', ''))}",
                    "symbol": item.get("asset") or item.get("assetName") or "",
                    "name": f"{item.get('asset', '')} Flexible Savings",
                    "provider": "Binance",
                    "apy": apy,
                    "min_amount": float(item.get("minPurchaseAmount") or item.get("minPurchaseAmt") or 0),
                    "lock_period_days": 0,
                    "is_active": bool(item.get("canPurchase", False)),
                    "description": item.get("assetDescription") or item.get("asset", ""),
                    "website_url": "https://www.binance.com/en/earn",
                    "raw_data": item
                }
                products.append(product)

            return products

        except Exception as e:
            # логування помилки — важливо для дебагу
            logger.error(f"[BinanceAPI] Помилка отримання Flexible Savings: {e}")
            return []

    async def get_locked_savings_products(self, asset: Optional[str] = None, current: int = 1, size: int = 100) -> List[Dict[str, Any]]:
        """
        Отримує Simple Earn Locked products (endpoint: /sapi/v1/simple-earn/locked/list).

        Параметри:
            asset: (опціонально) символ токена
            current: сторінка
            size: розмір сторінки
        """
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

            for item in rows:
                # Для Locked продуктів дані знаходяться в item['detail']
                detail = item.get('detail', item)

                # Отримуємо APY з detail
                apy_raw = detail.get("apr") or detail.get("annualizedRate") or detail.get("annualPercentageRate") or detail.get("latestAnnualPercentageRate")
                try:
                    apy = float(apy_raw) if apy_raw is not None else 0.0
                except Exception:
                    try:
                        apy = float(str(apy_raw).replace('%', ''))
                    except Exception:
                        apy = 0.0

                # Отримуємо символ з detail
                symbol = detail.get("asset") or detail.get("assetName") or item.get("asset") or ""

                # Фільтруємо продукти з невалідними символами (занадто короткі)
                if len(symbol) < 2:
                    logger.warning(f"[BinanceAPI] Пропущено Locked продукт з невалідним символом '{symbol}': {item.get('projectId')}")
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
                    "raw_data": item
                }
                products.append(product)

            return products

        except Exception as e:
            logger.error(f"[BinanceAPI] Помилка отримання Locked Savings: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Агрегує всі Earn продукти (Flexible, Locked) з повною пагінацією.

        Returns:
            List[Dict]: Список всіх Earn продуктів
        """
        all_products: List[Dict[str, Any]] = []
        try:
            # Отримуємо ВСІ Flexible продукти з пагінацією
            logger.info("[BinanceAPI] Початок отримання Flexible продуктів...")
            flexible_all = []
            current_page = 1
            max_pages = 50  # Захист від нескінченного циклу (50 сторінок * 100 = 5000 продуктів max)

            while current_page <= max_pages:
                flexible_page = await self.get_flexible_savings_products(current=current_page, size=100)

                if not flexible_page:
                    logger.info(f"[BinanceAPI] Flexible: сторінка {current_page} порожня, завершуємо")
                    break

                flexible_all.extend(flexible_page)
                logger.info(f"[BinanceAPI] Flexible: сторінка {current_page} - отримано {len(flexible_page)} продуктів (всього: {len(flexible_all)})")

                # Якщо отримали менше ніж розмір сторінки - це остання сторінка
                if len(flexible_page) < 100:
                    logger.info(f"[BinanceAPI] Flexible: отримано менше 100 продуктів, це остання сторінка")
                    break

                current_page += 1

            all_products.extend(flexible_all)
            logger.info(f"[BinanceAPI] ✅ Flexible продукти завершено: {len(flexible_all)} продуктів")

            # Отримуємо ВСІ Locked продукти з пагінацією
            logger.info("[BinanceAPI] Початок отримання Locked продуктів...")
            locked_all = []
            current_page = 1
            max_pages = 50  # Захист від нескінченного циклу

            while current_page <= max_pages:
                locked_page = await self.get_locked_savings_products(current=current_page, size=100)

                if not locked_page:
                    logger.info(f"[BinanceAPI] Locked: сторінка {current_page} порожня, завершуємо")
                    break

                locked_all.extend(locked_page)
                logger.info(f"[BinanceAPI] Locked: сторінка {current_page} - отримано {len(locked_page)} продуктів (всього: {len(locked_all)})")

                # Якщо отримали менше ніж розмір сторінки - це остання сторінка
                if len(locked_page) < 100:
                    logger.info(f"[BinanceAPI] Locked: отримано менше 100 продуктів, це остання сторінка")
                    break

                current_page += 1

            all_products.extend(locked_all)
            logger.info(f"[BinanceAPI] ✅ Locked продукти завершено: {len(locked_all)} продуктів")

            # Нормалізація (якщо у BaseExchange є метод normalize_earn_product)
            normalized: List[Dict[str, Any]] = []
            for p in all_products:
                try:
                    normalized.append(self.normalize_earn_product(p))
                except Exception:
                    normalized.append(p)

            logger.info(f"[BinanceAPI] ✅ Агреговано {len(normalized)} Earn продуктів (Flexible: {len(flexible_all)}, Locked: {len(locked_all)})")
            return normalized

        except Exception as e:
            logger.error(f"[BinanceAPI] ❌ Помилка агрегування Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Повертає Earn продукти для конкретного активу (фільтрація).
        """
        try:
            all_products = await self.get_earn_products()
            filtered = [p for p in all_products if p.get("symbol", "").upper() == asset.upper()]
            return filtered
        except Exception as e:
            logger.error(f"[BinanceAPI] Помилка фільтрації Earn продуктів по asset={asset}: {e}")
            return []
