"""
Сервіс для роботи з Bitget Earn продуктами.

Інкапсулює логіку взаємодії з BitgetAPI, кешуванням в Redis,
синхронізацією в PostgreSQL та обробкою помилок.
"""

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
    """
    Сервіс для роботи з продуктами Bitget Earn.
    
    Забезпечує:
    - Отримання продуктів з API
    - Кешування в Redis (TTL: 60 хвилин)
    - Синхронізацію в PostgreSQL
    - Обробку ladder APY
    - Graceful degradation при помилках
    """

    def __init__(self):
        """Ініціалізує Bitget сервіс."""
        # Не викликаємо super().__init__ бо нам потрібна власна логіка для passphrase
        self.exchange_name = "bitget"
        self.api_client: Optional[BitgetAPI] = None
        self.cache_ttl = 3600  # 60 хвилин
        self.cache_manager = cache_manager
        self.is_configured = False
        
        logger.info("🔧 BitgetService створено (очікує initialize())")

    async def initialize(self):
        """Ініціалізує Bitget API клієнт з ключами з settings."""
        api_key = settings.bitget_api_key
        api_secret = settings.bitget_api_secret
        api_passphrase = settings.bitget_api_passphrase
        
        # Перевірка наявності всіх ключів (включно з passphrase)
        # Перевіряємо що всі ключі є і не порожні
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
        """
        Отримує продукти безпосередньо з Bitget API.
        
        Args:
            symbol: Опціональний символ для фільтрації
        
        Returns:
            List[Dict]: Список нормалізованих продуктів
        """
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
        """
        Отримує продукти з кешуванням (Redis).
        
        Логіка:
        1. Спробувати отримати з Redis кешу
        2. Якщо кеш порожній - запитати API
        3. Зберегти в кеш з TTL 60 хвилин
        4. Повернути результат
        
        Args:
            symbol: Опціональний символ для фільтрації
        
        Returns:
            List[Dict]: Список продуктів
        """
        # Ініціалізація API клієнта якщо потрібно
        if not self.api_client or not self.is_configured:
            await self.initialize()

        # Генеруємо ключ кешу
        cache_key = get_exchange_cache_key("bitget", symbol or "all")
        
        try:
            # Спроба отримати з кешу
            cached_data = await self.cache_manager.get_cached_data(cache_key)
            
            if cached_data:
                logger.info(f"[BitgetService] ✅ Дані отримано з кешу: {cache_key}")
                return cached_data
            
            # Якщо кеш порожній - запитуємо API
            logger.info(f"[BitgetService] 🔄 Кеш порожній, запит до API")
            products = await self.get_products_from_api(symbol)
            
            if products:
                # Зберігаємо в кеш
                await self.cache_manager.set_cached_data(cache_key, products, self.cache_ttl)
                logger.info(f"[BitgetService] ✅ Дані збережено в кеш: {len(products)} продуктів")
            
            return products
            
        except Exception as e:
            logger.error(f"[BitgetService] Помилка кешування: {e}", exc_info=True)
            # Fallback до прямого API запиту
            return await self.get_products_from_api(symbol)

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Додаткова нормалізація продуктів (якщо потрібна).
        
        Args:
            raw_products: Сирі продукти з API
        
        Returns:
            List[Dict]: Нормалізовані продукти
        """
        normalized = []
        
        for product in raw_products:
            try:
                # Перевірка обов'язкових полів
                required_fields = ["id", "symbol", "name", "provider", "apy"]
                if not all(field in product for field in required_fields):
                    logger.warning(f"[BitgetService] Продукт пропущено (відсутні поля): {product.get('id')}")
                    continue
                
                # Валідація APY (має бути >= 0 і <= 1000%)
                apy = product.get("apy", 0)
                if not (0 <= apy <= 1000):
                    logger.warning(f"[BitgetService] Невалідний APY {apy}% для {product.get('id')}")
                    continue
                
                # Додаємо поле is_cefi (Bitget - централізована біржа)
                product["is_cefi"] = True
                
                normalized.append(product)
                
            except Exception as e:
                logger.warning(f"[BitgetService] Помилка нормалізації продукту: {e}")
                continue
        
        logger.info(f"[BitgetService] Нормалізовано {len(normalized)} з {len(raw_products)} продуктів")
        return normalized

    async def sync_products_to_db(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Синхронізує продукти з API в базу даних.
        
        Процес:
        1. Отримати продукти з API (з кешем)
        2. Нормалізувати продукти
        3. Зберегти в PostgreSQL (UPSERT)
        4. Повернути статистику
        
        Args:
            symbol: Опціональний символ для синхронізації
        
        Returns:
            Dict з результатами синхронізації
        """
        # Ініціалізація API клієнта якщо потрібно
        if not self.api_client or not self.is_configured:
            await self.initialize()

        try:
            logger.info(f"🔄 Початок синхронізації Bitget продуктів для {symbol or 'всіх'}")

            # Отримуємо продукти
            products = await self.get_products_with_cache(symbol)
            
            if not products:
                return {
                    "status": "warning",
                    "message": "Продукти не знайдено",
                    "products_count": 0,
                    "sync_stats": {"created": 0, "updated": 0, "errors": 0},
                    "timestamp": datetime.now(UTC).isoformat()
                }
            
            # Додаткова нормалізація
            normalized_products = await self._normalize_products(products)
            
            # Зберігаємо в БД
            sync_stats = await self._save_products_to_db(normalized_products)
            
            return {
                "status": "success",
                "message": "Синхронізація завершена",
                "products_count": len(normalized_products),
                "sync_stats": sync_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Помилка синхронізації Bitget продуктів: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Помилка синхронізації: {str(e)}",
                "products_count": 0,
                "sync_stats": {"created": 0, "updated": 0, "errors": 1},
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def _save_products_to_db(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Зберігає продукти в базу даних PostgreSQL.
        
        Використовує UPSERT логіку:
        - Якщо продукт існує - оновлює
        - Якщо не існує - створює новий
        
        Args:
            products: Список нормалізованих продуктів
        
        Returns:
            Dict з статистикою: {"created": N, "updated": M, "errors": K}
        """
        stats = {"created": 0, "updated": 0, "errors": 0}
        
        async with get_database_session() as db:
            try:
                for product_data in products:
                    try:
                        # Перевіряємо чи продукт існує
                        existing_product = await YieldProductCRUD.get_product_by_id(db, product_data["id"])
                        
                        if existing_product:
                            # Оновлюємо існуючий
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
                                raw_data=product_data.get("raw_data")
                            )
                            updated = await YieldProductCRUD.update_product(
                                db, product_data["id"], update_data
                            )
                            if updated:
                                stats["updated"] += 1
                        else:
                            # Створюємо новий
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
                                raw_data=product_data.get("raw_data")
                            )
                            
                            db.add(db_product)
                            await db.commit()
                            await db.refresh(db_product)
                            stats["created"] += 1
                        
                        # Зберігаємо raw дані в exchange_data таблицю
                        await ExchangeDataCRUD.create_exchange_data(
                            db,
                            product_id=product_data["id"],
                            exchange="bitget",
                            raw_data=product_data.get("raw_data", {}),
                            api_endpoint="/api/v2/earn/savings/product",
                            request_timestamp=datetime.now(UTC).replace(tzinfo=None)
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ Помилка збереження продукту {product_data.get('id', 'unknown')}: {e}")
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
        """
        Тестує підключення до Bitget API.
        
        Returns:
            Dict з результатом тесту підключення
        """
        if not self.api_client:
            return {
                "status": "error",
                "message": "Bitget API клієнт не ініціалізовано. Перевірте налаштування API ключів."
            }
        
        start_time = datetime.now()
        
        try:
            # Спробуємо отримати 1 продукт для тесту
            products = await self.api_client.get_flexible_savings_products(size=1)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if products is not None:
                return {
                    "status": "success",
                    "message": "Підключення до Bitget API успішне",
                    "response_time_ms": duration_ms,
                    "products_found": len(products)
                }
            else:
                return {
                    "status": "error",
                    "message": "Не вдалося отримати дані з Bitget API",
                    "response_time_ms": duration_ms
                }
                
        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": "error",
                "message": f"Помилка підключення до Bitget API: {str(e)}",
                "response_time_ms": duration_ms
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Повертає статус здоров'я сервісу Bitget.
        
        Returns:
            Dict з інформацією про стан сервісу
        """
        try:
            connection_test = await self.test_connection()
            
            return {
                "service": "bitget",
                "configured": self.is_configured,
                "connection": connection_test,
                "cache_stats": await self.cache_manager.get_cache_stats(),
                "timestamp": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            return {
                "service": "bitget",
                "configured": self.is_configured,
                "connection": {
                    "status": "error",
                    "message": str(e)
                },
                "timestamp": datetime.now(UTC).isoformat()
            }

