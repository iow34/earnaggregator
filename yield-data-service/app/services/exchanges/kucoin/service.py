"""
Service layer for KuCoin Earn (Savings) products.

Coordinates API client calls, normalization, caching and DB sync.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
import time

from ..base_service import BaseExchangeService
from .api import KuCoinAPI
from app.utils.logger import logger
from app.services.cache import cache_manager, get_exchange_cache_key
from app.utils.metrics import EXTERNAL_API_CALLS, observe_latency, AGGREGATION_LATENCY_SECONDS
from app.config import settings


class KuCoinService(BaseExchangeService):
    """Service for handling KuCoin Earn products."""

    def __init__(self):
        super().__init__("kucoin", KuCoinAPI)
        self.cache_ttl = 3600

    async def initialize(self):
        """Initialize KuCoin API client with key/secret/passphrase."""
        try:
            api_key = getattr(settings, "kucoin_api_key", "")
            api_secret = getattr(settings, "kucoin_api_secret", "")
            api_passphrase = getattr(settings, "kucoin_api_passphrase", "")

            if not api_key or not api_secret or not api_passphrase:
                logger.warning("⚠️ KuCoin API keys are not fully configured")
                self.api_client = KuCoinAPI(api_key or "", api_secret or "", api_passphrase or "")
                self.is_configured = False
            else:
                self.api_client = KuCoinAPI(api_key, api_secret, api_passphrase)
                self.is_configured = True
                logger.info("✅ KuCoin API client initialized")
        except Exception as e:
            logger.error(f"❌ KuCoin initialize error: {e}")
            self.is_configured = False
            self.api_client = KuCoinAPI("", "", "")

    async def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            if not self.api_client:
                return {"status": "error", "message": "KuCoin API client not initialized"}

            # Minimal test: fetch 1 page of flexible products
            products = await self.api_client.get_flexible_savings_products()
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "status": "success",
                "message": "KuCoin connectivity OK",
                "response_time_ms": round(duration_ms, 2),
                "products_found": len(products),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return {
                "status": "error",
                "message": str(e),
                "response_time_ms": round(duration_ms, 2),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.api_client:
            logger.error("❌ KuCoin API client not initialized")
            return []
        try:
            start = time.perf_counter()
            if symbol:
                data = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                data = await self.api_client.get_earn_products()
            AGGREGATION_LATENCY_SECONDS.observe(time.perf_counter() - start)
            EXTERNAL_API_CALLS.labels(exchange="kucoin", status="success").inc()
            return data
        except Exception as e:
            EXTERNAL_API_CALLS.labels(exchange="kucoin", status="error").inc()
            logger.error(f"❌ KuCoin API error: {e}")
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = get_exchange_cache_key("kucoin", symbol)

        cached = await cache_manager.get_cached_data(cache_key)
        if cached is not None:
            logger.info(f"🎯 KuCoin products from cache for {symbol or 'all'}")
            return cached.get("products", [])

        raw = await self.get_products_from_api(symbol)
        normalized = await self._normalize_products(raw)

        await cache_manager.set_cached_data(
            cache_key,
            {
                "products": normalized,
                "count": len(normalized),
                "timestamp": datetime.now(UTC).isoformat(),
                "symbol": symbol,
                "source": "kucoin_api",
            },
            self.cache_ttl,
        )

        return normalized

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in raw_products:
            try:
                # From KuCoin docs: returnRate is like "0.50000000" for 50%
                return_rate_str = item.get("returnRate", "0") or "0"
                apy = round(float(return_rate_str) * 100.0, 4)

                currency = (item.get("currency") or "").upper().strip()
                product_id = str(item.get("id", ""))

                if not currency or len(currency) < 2:
                    logger.warning(
                        f"⚠️ KuCoin пропускаємо продукт без валюти: {item.get('id', 'unknown')}"
                    )
                    continue

                # Status: "ONGOING" means active

                status_val = str(item.get("status", ""))
                is_active = status_val == "ONGOING"

                # Duration: 0 for flexible, otherwise days
                duration = int(item.get("duration", 0) or 0)
                is_flexible = duration == 0

                # Category/Type: DEMAND for flexible, TIME for fixed
                category = item.get("category", "").upper()
                if category == "DEMAND":
                    is_flexible = True
                elif category == "TIME":
                    is_flexible = False

                # Limits: userLowerLimit (min), userUpperLimit (max)
                min_amount = float(item.get("userLowerLimit") or 0)
                max_amount = (
                    float(item.get("userUpperLimit"))
                    if item.get("userUpperLimit") not in (None, "", "0")
                    else None
                )

                risk_level = (
                    "Low"
                    if currency in {"USDT", "USDC", "DAI", "BUSD", "FDUSD", "USD"}
                    else "Medium"
                )

                product_name = f"{currency} {'Flexible' if is_flexible else 'Fixed'} Savings"
                if not is_flexible:
                    product_name += f" ({duration}d)"

                unique_suffix = f"{currency}_{item.get('returnRate', '0')}_{duration}"
                normalized.append(
                    {
                        "id": f"kucoin_{'flexible' if is_flexible else 'fixed'}_{product_id}_{unique_suffix}",
                        "symbol": currency,
                        "name": product_name,
                        "provider": "KuCoin",
                        "apy": apy,
                        "is_cefi": True,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                        "lock_period_days": 0 if is_flexible else duration,
                        "max_apy": apy,
                        "risk_level": risk_level,
                        "is_active": is_active,
                        "website_url": "https://www.kucoin.com/earn",
                        "description": f"category={category} redeemType={item.get('redeemType')} earlyRedeemSupported={item.get('earlyRedeemSupported')}",
                        "raw_data": item,
                        "last_checked": datetime.now(UTC),
                        "is_flexible": is_flexible,
                        "product_type": "Flexible" if is_flexible else "Fixed",
                    }
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ KuCoin normalize error for item {item.get('id', 'unknown')}: {e}"
                )
                logger.warning(
                    f"   Item data: currency={item.get('currency')}, returnRate={item.get('returnRate')}, status={item.get('status')}"
                )
                continue

        return normalized
