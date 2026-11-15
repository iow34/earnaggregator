from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
import asyncio

from app.config import settings
from app.utils.logger import logger
from app.services.cache import cache_manager, get_exchange_cache_key
from app.db.database import get_database_session
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD
from app.db.models import YieldProductDB
from app.models.yield_product import YieldProductUpdate
from ..base_service import BaseExchangeService
from .api import BitgetAPI


class BitgetService(BaseExchangeService):
    def __init__(self):

        self.exchange_name = "bitget"
        self.api_client: Optional[BitgetAPI] = None
        self.cache_ttl = 3600
        self.cache_manager = cache_manager
        self.is_configured = False

        logger.info("🔧 BitgetService створено (очікує initialize())")

    async def initialize(self):
        api_key = settings.bitget_api_key
        api_secret = settings.bitget_api_secret
        api_passphrase = settings.bitget_api_passphrase

        if not api_key or not api_secret or not api_passphrase:
            logger.warning(
                "⚠️ Bitget API ключі не налаштовані повністю. "
                f"API Key: {'✅' if api_key else '❌'}, "
                f"API Secret: {'✅' if api_secret else '❌'}, "
                f"API Passphrase: {'✅' if api_passphrase else '❌'}. "
                "Сервіс працюватиме в обмеженому режимі."
            )
            self.is_configured = False
            return

        self.api_client = BitgetAPI(api_key, api_secret, api_passphrase)
        self.is_configured = True
        logger.info("✅ BitgetService ініціалізовано з повною аутентифікацією")

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.api_client:
            logger.error("❌ Bitget API клієнт не ініціалізовано")
            return []

        try:
            if symbol:
                products = await self.api_client.get_earn_products_by_asset(asset=symbol)
            else:
                products = await self.api_client.get_earn_products()

            logger.info(f"[BitgetService] Отримано {len(products)} продуктів з API")
            return products

        except Exception as e:
            logger.error(f"[BitgetService] Помилка отримання продуктів з API: {e}", exc_info=True)
            return []

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:

        if not self.api_client or not self.is_configured:
            await self.initialize()

        cache_key = get_exchange_cache_key("bitget", symbol or "all")

        try:
            cached_data = await self.cache_manager.get_cached_data(cache_key)

            if cached_data:
                logger.info(f"[BitgetService] ✅ Дані отримано з кешу: {cache_key}")
                return cached_data

            logger.info(f"[BitgetService] 🔄 Кеш порожній, запит до API")
            products = await self.get_products_from_api(symbol)

            if products:
                await self.cache_manager.set_cached_data(cache_key, products, self.cache_ttl)
                logger.info(f"[BitgetService] ✅ Дані збережено в кеш: {len(products)} продуктів")

            return products

        except Exception as e:
            logger.error(f"[BitgetService] Помилка кешування: {e}", exc_info=True)

            return await self.get_products_from_api(symbol)

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []

        for product in raw_products:
            try:
                required_fields = ["id", "symbol", "name", "provider", "apy"]
                if not all(field in product for field in required_fields):
                    logger.warning(
                        f"[BitgetService] Продукт пропущено (відсутні поля): {product.get('id')}"
                    )
                    continue

                apy = product.get("apy", 0)
                if not (0 <= apy <= 1000):
                    logger.warning(f"[BitgetService] Невалідний APY {apy}% для {product.get('id')}")
                    continue

                product["is_cefi"] = True

                normalized.append(product)

            except Exception as e:
                logger.warning(f"[BitgetService] Помилка нормалізації продукту: {e}")
                continue

        logger.info(
            f"[BitgetService] Нормалізовано {len(normalized)} з {len(raw_products)} продуктів"
        )
        return normalized

    async def sync_products_to_db(self, symbol: Optional[str] = None) -> Dict[str, Any]:

        if not self.api_client or not self.is_configured:
            await self.initialize()

        try:
            logger.info(f"🔄 Початок синхронізації Bitget продуктів для {symbol or 'всіх'}")

            products = await self.get_products_with_cache(symbol)

            if not products:
                return {
                    "status": "warning",
                    "message": "Продукти не знайдено",
                    "products_count": 0,
                    "sync_stats": {"created": 0, "updated": 0, "errors": 0},
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            normalized_products = await self._normalize_products(products)

            sync_stats = await self._save_products_to_db(normalized_products)

            return {
                "status": "success",
                "message": "Синхронізація завершена",
                "products_count": len(normalized_products),
                "sync_stats": sync_stats,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка синхронізації Bitget продуктів: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Помилка синхронізації: {str(e)}",
                "products_count": 0,
                "sync_stats": {"created": 0, "updated": 0, "errors": 1},
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def _save_products_to_db(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        stats = {"created": 0, "updated": 0, "errors": 0}

        async with get_database_session() as db:
            try:
                for product_data in products:
                    try:
                        existing_product = await YieldProductCRUD.get_product_by_id(
                            db, product_data["id"]
                        )

                        if existing_product:
                            update_data = YieldProductUpdate(
                                name=product_data["name"],
                                apy=product_data["apy"],
                                is_cefi=product_data.get("is_cefi", True),
                                min_amount=product_data.get("min_amount"),
                                max_amount=product_data.get("max_amount"),
                                lock_period_days=product_data["lock_period_days"],
                                max_apy=product_data.get("max_apy", product_data["apy"]),
                                risk_level=product_data["risk_level"],
                                is_active=product_data["is_active"],
                                website_url=product_data.get("website_url"),
                                description=product_data.get("description"),
                                raw_data=product_data.get("raw_data"),
                            )
                            updated = await YieldProductCRUD.update_product(
                                db, product_data["id"], update_data
                            )
                            if updated:
                                stats["updated"] += 1
                        else:
                            db_product = YieldProductDB(
                                id=product_data["id"],
                                symbol=product_data["symbol"],
                                name=product_data["name"],
                                provider=product_data["provider"],
                                apy=product_data["apy"],
                                is_cefi=product_data.get("is_cefi", True),
                                min_amount=product_data.get("min_amount"),
                                max_amount=product_data.get("max_amount"),
                                lock_period_days=product_data["lock_period_days"],
                                max_apy=product_data.get("max_apy", product_data["apy"]),
                                risk_level=product_data["risk_level"],
                                is_active=product_data["is_active"],
                                website_url=product_data.get("website_url"),
                                description=product_data.get("description"),
                                raw_data=product_data.get("raw_data"),
                            )

                            db.add(db_product)
                            await db.commit()
                            await db.refresh(db_product)
                            stats["created"] += 1

                        await ExchangeDataCRUD.create_exchange_data(
                            db,
                            product_id=product_data["id"],
                            exchange="bitget",
                            raw_data=product_data.get("raw_data", {}),
                            api_endpoint="/api/v2/earn/savings/product",
                            request_timestamp=datetime.now(UTC).replace(tzinfo=None),
                        )

                    except Exception as e:
                        logger.error(
                            f"❌ Помилка збереження продукту {product_data.get('id', 'unknown')}: {e}"
                        )
                        stats["errors"] += 1
                        continue

                logger.info(
                    f"✅ Bitget продукти збережено: "
                    f"{stats['created']} створено, "
                    f"{stats['updated']} оновлено, "
                    f"{stats['errors']} помилок"
                )

            except Exception as e:
                logger.error(f"❌ Помилка збереження продуктів Bitget: {e}", exc_info=True)
                stats["errors"] += len(products)

        return stats

    async def test_connection(self) -> Dict[str, Any]:
        if not self.api_client:
            return {
                "status": "error",
                "message": "Bitget API клієнт не ініціалізовано. Перевірте налаштування API ключів.",
            }

        start_time = datetime.now()

        try:
            products = await self.api_client.get_flexible_savings_products(size=1)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            if products is not None:
                return {
                    "status": "success",
                    "message": "Підключення до Bitget API успішне",
                    "response_time_ms": duration_ms,
                    "products_found": len(products),
                }
            else:
                return {
                    "status": "error",
                    "message": "Не вдалося отримати дані з Bitget API",
                    "response_time_ms": duration_ms,
                }

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": "error",
                "message": f"Помилка підключення до Bitget API: {str(e)}",
                "response_time_ms": duration_ms,
            }

    async def get_health_status(self) -> Dict[str, Any]:
        try:
            connection_test = await self.test_connection()

            return {
                "service": "bitget",
                "configured": self.is_configured,
                "connection": connection_test,
                "cache_stats": await self.cache_manager.get_cache_stats(),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            return {
                "service": "bitget",
                "configured": self.is_configured,
                "connection": {"status": "error", "message": str(e)},
                "timestamp": datetime.now(UTC).isoformat(),
            }
