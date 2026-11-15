from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from collections import defaultdict

from app.config import settings
from app.utils.logger import logger
from ..base_service import BaseExchangeService
from .api import MEXCAPI
from .models import CurrencyResult, FinancialProduct


class MEXCService(BaseExchangeService):
    def __init__(self):
        super().__init__(exchange_name="mexc", api_class=MEXCAPI)
        self.is_manual_mode = getattr(settings, "mexc_manual_mode", False)

        if not self.api_client:
            self.api_client = self.api_class(self.api_key, self.api_secret)
            self.is_configured = True

        logger.info(f"✅ MEXCService ініціалізовано (manual_mode={self.is_manual_mode})")

    async def _normalize_products(self, raw_products: List[CurrencyResult]) -> List[Dict[str, Any]]:
        normalized_products = []

        for currency_result in raw_products:
            products_by_type = defaultdict(list)

            for product in currency_result.financialProductList:
                if not (product.financialState == 2 and not product.soldOut):
                    continue

                product_type = product.financialType
                products_by_type[product_type].append(product)

            for product_type, products in products_by_type.items():
                if not products:
                    continue

                min_apr_product = min(products, key=self._get_product_apr)

                normalized_product = self._normalize_single_product(
                    min_apr_product, currency_result.currency, product_type
                )

                if normalized_product:
                    normalized_products.append(normalized_product)

        logger.info(f"[MEXCService] Нормалізовано {len(normalized_products)} продуктів")
        return normalized_products

    def _get_product_apr(self, product: FinancialProduct) -> float:
        try:
            return float(product.showApr)

        except (ValueError, TypeError, AttributeError):
            return float("inf")

    def _normalize_single_product(
        self, product: FinancialProduct, currency: str, product_type: str
    ) -> Optional[Dict[str, Any]]:
        try:
            apr = self._get_product_apr(product)
            if apr == float("inf"):
                logger.warning(
                    f"[MEXCService] Пропускаю продукт {product.financialId} через невалідний APR"
                )
                return None

            if product_type == "FLEXIBLE":
                prod_type = "Flexible"
                lock_days = 0
                name = f"{currency} Flexible Savings"
                description = f"Flexible savings for {currency}"
            elif product_type == "FIXED":
                prod_type = "Locked"
                lock_days = product.fixedInvestPeriodCount or 30  # Default 30 days
                name = f"{currency} {lock_days} Days Fixed Savings"
                description = f"Fixed savings for {currency} ({lock_days} days)"
            else:
                logger.warning(f"[MEXCService] Невідомий тип продукту: {product_type}")
                return None

            risk_level = "Low" if currency in ["USDT", "USDC"] else "Medium"

            normalized = {
                "id": f"mexc_{prod_type.lower()}_{product.financialId}",
                "symbol": currency,
                "name": name,
                "provider": "MEXC",
                "apy": apr,
                "max_apy": apr,
                "is_cefi": True,
                "min_amount": 0.001,
                "max_amount": None,
                "lock_period_days": lock_days,
                "product_type": prod_type,
                "is_active": True,
                "risk_level": risk_level,
                "description": description,
                "website_url": "https://www.mexc.com/staking",
                "raw_data": product.model_dump(),
            }

            return normalized

        except Exception as e:
            logger.error(f"[MEXCService] Помилка нормалізації продукту {product.financialId}: {e}")
            return None

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if not self.api_client:
                logger.error("[MEXCService] API клієнт не ініціалізований")
                return []

            logger.info(f"[MEXCService] Отримання продуктів з MEXC API для {symbol or 'всіх'}")

            if symbol:
                products = await self.api_client.get_earn_products_by_asset(symbol)
                logger.info(f"[MEXCService] Отримано {len(products)} продуктів для {symbol}")
            else:
                logger.info("[MEXCService] Запит до MEXC API get_all_earn_products...")
                currencies = await self.api_client.get_all_earn_products()
                logger.info(f"[MEXCService] Отримано {len(currencies)} валют з API, нормалізую...")
                products = await self._normalize_products(currencies)
                logger.info(f"[MEXCService] Після нормалізації: {len(products)} продуктів")

            logger.info(f"[MEXCService] Отримано {len(products)} продуктів з API")
            return products

        except Exception as e:
            logger.error(f"[MEXCService] Помилка отримання продуктів з API: {e}", exc_info=True)
            return []

    async def sync_products_to_db(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        try:
            logger.info(
                f"🔄 Початок синхронізації {self.exchange_name} продуктів для {symbol or 'всіх'} з API"
            )

            products = await self.get_products_from_api(symbol)

            if not products:
                return {
                    "status": "warning",
                    "message": "Продукти не знайдено в API",
                    "products_count": 0,
                    "sync_stats": {"created": 0, "updated": 0, "errors": 0},
                }

            sync_stats = await self._save_products_to_db(products)

            return {
                "status": "success",
                "message": "Синхронізація завершена",
                "products_count": len(products),
                "sync_stats": sync_stats,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка синхронізації {self.exchange_name} продуктів: {e}")
            return {
                "status": "error",
                "message": f"Помилка синхронізації: {str(e)}",
                "products_count": 0,
                "sync_stats": {"created": 0, "updated": 0, "errors": 1},
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not symbol:
            logger.info("[MEXCService] Отримання всіх MEXC продуктів з БД")
        else:
            logger.info(f"[MEXCService] Отримання MEXC продуктів для {symbol} з БД")

        from app.db.crud import YieldProductCRUD
        from app.models.yield_product import YieldProductFilter

        try:
            filters = YieldProductFilter(provider="MEXC")
            db_products = await YieldProductCRUD.filter_products(filters=filters, limit=None)

            if symbol:
                db_products = [p for p in db_products if p.symbol == symbol.upper()]

            products = []
            for p in db_products:
                products.append(
                    {
                        "id": p.id,
                        "symbol": p.symbol,
                        "name": p.name,
                        "provider": p.provider,
                        "apy": p.apy,
                        "min_amount": p.min_amount or 0.0,
                        "max_amount": p.max_amount,
                        "lock_period_days": p.lock_period_days,
                        "product_type": getattr(
                            p, "product_type", "Flexible" if p.lock_period_days == 0 else "Locked"
                        ),
                        "is_active": p.is_active,
                        "risk_level": p.risk_level,
                        "description": p.description or "",
                        "website_url": p.website_url or "https://www.mexc.com/staking",
                        "raw_data": p.raw_data or {},
                    }
                )

            logger.info(f"✅ [MEXCService] Знайдено {len(products)} продуктів в БД")
            return products

        except Exception as e:
            logger.error(f"❌ [MEXCService] Помилка отримання продуктів з БД: {e}", exc_info=True)
            return []

    async def test_connection(self) -> Dict[str, Any]:
        try:
            api_status = "unknown"
            api_products = 0

            if self.api_client:
                try:
                    response = await self.api_client.get_earn_products(page=1, page_size=10)
                    api_products = len(response.result)
                    api_status = "success"
                except Exception as e:
                    logger.warning(f"[MEXCService] API недоступний: {e}")
                    api_status = "error"

            from app.db.crud import YieldProductCRUD
            from app.models.yield_product import YieldProductFilter

            filters = YieldProductFilter(provider="MEXC")
            db_products = await YieldProductCRUD.filter_products(filters=filters, limit=None)
            db_count = len(db_products)

            if api_status == "success":
                status = "success"
                message = f"MEXC API працює. Продуктів в API: {api_products}, в БД: {db_count}"
            else:
                status = "warning"
                message = f"MEXC працює через БД (API недоступний). Продуктів в БД: {db_count}"

            return {
                "status": status,
                "message": message,
                "manual_mode": self.is_manual_mode,
                "api_status": api_status,
                "api_products": api_products,
                "db_products": db_count,
                "public_api": True,
            }

        except Exception as e:
            logger.error(f"❌ Помилка перевірки MEXC: {e}")
            return {
                "status": "error",
                "message": f"Помилка тестування: {e}",
                "manual_mode": self.is_manual_mode,
                "public_api": True,
            }

    async def get_health_status(self) -> Dict[str, Any]:
        try:
            connection_test = await self.test_connection()

            if connection_test["status"] == "success":
                return {
                    "status": "healthy",
                    "exchange": "mexc",
                    "mode": "api",
                    "api_status": connection_test.get("api_status"),
                    "products_count": connection_test.get("db_products", 0),
                    "api_products": connection_test.get("api_products", 0),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            elif connection_test["status"] == "warning":
                return {
                    "status": "degraded",
                    "exchange": "mexc",
                    "mode": "api",
                    "api_status": connection_test.get("api_status"),
                    "products_count": connection_test.get("db_products", 0),
                    "warning": connection_test.get("message"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "exchange": "mexc",
                    "mode": "api",
                    "error": connection_test.get("message"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        except Exception as e:
            logger.error(f"❌ Помилка health check для MEXC: {e}")
            return {
                "status": "unhealthy",
                "exchange": "mexc",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
