"""
KuCoin API client for Earn (Savings) products.

Implements KuCoin-specific authentication (KC-API-KEY v2) and endpoints
for fetching Flexible and Fixed savings products.
"""

from typing import Dict, List, Optional, Any
import base64
import hmac
import hashlib
import time
from urllib.parse import urlencode

from app.utils.logger import logger
import asyncio
from ..base_exchange import BaseExchange
from app.config import settings


class KuCoinAPI(BaseExchange):
    """
    Client for KuCoin Earn Savings endpoints.
    """

    def __init__(self, api_key: str, api_secret: str, api_passphrase: Optional[str] = None):
        super().__init__(api_key=api_key, api_secret=api_secret, base_url="https://api.kucoin.com")
        # Passphrase is required for signed requests (v2)
        self.api_passphrase = api_passphrase or getattr(settings, "kucoin_api_passphrase", "")
        self.api_key_version = "2"

    def get_headers(self) -> Dict[str, str]:
        # Base headers; signed requests will add KC-* headers per call
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _sign(self, method: str, path: str, query: str = "", body: str = "") -> Dict[str, str]:
        """
        Generate KuCoin v2 headers (KC-API-*) for a signed request.
        """
        timestamp_ms = str(int(time.time() * 1000))
        prehash = f"{timestamp_ms}{method.upper()}{path}{query}{body}"

        signature = base64.b64encode(hmac.new(self.api_secret.encode("utf-8"), prehash.encode("utf-8"), hashlib.sha256).digest()).decode()

        passphrase_raw = self.api_passphrase or ""
        passphrase = base64.b64encode(hmac.new(self.api_secret.encode("utf-8"), passphrase_raw.encode("utf-8"), hashlib.sha256).digest()).decode()

        return {
            "KC-API-KEY": self.api_key or "",
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp_ms,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": self.api_key_version,
        }

    async def _get_request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make unsigned GET request for public endpoints."""
        params = params or {}
        query = f"?{urlencode(params)}" if params else ""

        # Simple exponential backoff for 429/5xx
        max_attempts = 3
        backoff = 1.0
        for attempt in range(max_attempts):
            try:
                return await self._make_request("GET", f"{path}{query}", auth_required=False)
            except Exception as e:
                msg = str(e)
                if any(code in msg for code in ["429", "500", "502", "503", "504"]) and attempt < max_attempts - 1:
                    logger.warning(f"[KuCoinAPI] Backoff {backoff}s due to error: {msg}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

    async def _signed_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make signed GET request for private endpoints."""
        params = params or {}
        # Ensure deterministic ordering for signature
        query = f"?{urlencode(sorted(params.items()))}" if params else ""
        headers = self._sign("GET", path, query, "")

        # Simple exponential backoff for 429/5xx
        max_attempts = 3
        backoff = 1.0
        for attempt in range(max_attempts):
            try:
                return await self._make_request("GET", f"{path}{query}", headers=headers, auth_required=True)
            except Exception as e:
                msg = str(e)
                if any(code in msg for code in ["429", "500", "502", "503", "504"]) and attempt < max_attempts - 1:
                    logger.warning(f"[KuCoinAPI] Backoff {backoff}s due to error: {msg}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

    async def get_flexible_savings_products(self, currency: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch current Flexible savings products."""
        try:
            params: Dict[str, Any] = {"fundsType": "FLEXIBLE"}
            if currency:
                params["currency"] = currency
            # This endpoint actually requires authentication despite docs saying otherwise
            data = await self._signed_get("/api/v1/earn/saving/products", params)
            items = data.get("data", []) if isinstance(data, dict) else []
            logger.info(f"[KuCoinAPI] FLEXIBLE fetched: {len(items)}")
            return items
        except Exception as e:
            logger.error(f"[KuCoinAPI] Flexible fetch error: {e}")
            return []

    async def get_locked_savings_products(self, currency: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch current Fixed savings products."""
        try:
            params: Dict[str, Any] = {"fundsType": "FIXED"}
            if currency:
                params["currency"] = currency
            # This endpoint actually requires authentication despite docs saying otherwise
            data = await self._signed_get("/api/v1/earn/saving/products", params)
            items = data.get("data", []) if isinstance(data, dict) else []
            logger.info(f"[KuCoinAPI] FIXED fetched: {len(items)}")
            return items
        except Exception as e:
            logger.error(f"[KuCoinAPI] Fixed fetch error: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        flexible = await self.get_flexible_savings_products()
        fixed = await self.get_locked_savings_products()
        return [*flexible, *fixed]

    async def get_earn_products_by_asset(self, symbol: str) -> List[Dict[str, Any]]:
        flexible = await self.get_flexible_savings_products(currency=symbol)
        fixed = await self.get_locked_savings_products(currency=symbol)
        return [*flexible, *fixed]


