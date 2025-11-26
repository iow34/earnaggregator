"""
Базовий клас для всіх сервісів бірж.

Забезпечує уніфікований інтерфейс та спільну функціональність
для всіх сервісів бірж в системі.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime, UTC

from app.services.cache import cache_manager, get_exchange_cache_key
from app.services.exchanges.base_exchange import BaseExchange
from app.db.database import get_database_session
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD
from app.db.models import YieldProductDB
from app.models.yield_product import YieldProductUpdate
from app.config import settings
from app.utils.logger import logger


class BaseExchangeService(ABC):
    """
    Базовий клас для всіх сервісів бірж.

    Забезпечує уніфікований інтерфейс та спільну логіку
    для роботи з різними біржами.
    """

    def __init__(self, exchange_name: str, api_class: type):
        """
        Ініціалізує базовий сервіс біржі.

        Args:
            exchange_name: Назва біржі (binance, bybit, etc.)
            api_class: Клас API клієнта для цієї біржі
        """
        self.exchange_name = exchange_name
        self.api_class = api_class

        # Налаштування API
        self.api_key = getattr(settings, f"{exchange_name}_api_key", "")
        self.api_secret = getattr(settings, f"{exchange_name}_api_secret", "")

        # Ініціалізуємо API клієнт
        self.api_client = None
        self.cache_ttl = 1800  # 30 хвилин

        # Ініціалізуємо cache manager
        self.cache_manager = cache_manager

        # Перевіряємо конфігурацію
        self.is_configured = self._check_configuration()

        if self.is_configured:
            self.api_client = api_class(self.api_key, self.api_secret)
        else:
            logger.warning(f"⚠️ API ключі для {exchange_name} не налаштовані")

    def _check_configuration(self) -> bool:
        """Перевіряє чи налаштовані API ключі."""
        return bool(self.api_key and self.api_secret)

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Тестує підключення до API біржі."""
        pass

    @abstractmethod
    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Отримує продукти з кешуванням."""
        pass

    @abstractmethod
    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Нормалізує сирі дані продуктів."""
        pass

    async def sync_products_to_db(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Синхронізує продукти з API в базу даних.

        Args:
            symbol: Опціональний символ для синхронізації

        Returns:
            Dict з результатами синхронізації
        """
        try:
            logger.info(f"🔄 Початок синхронізації {self.exchange_name} продуктів для {symbol or 'всіх'}")

            # Отримуємо продукти
            products = await self.get_products_with_cache(symbol)

            if not products:
                return {
                    "status": "warning",
                    "message": "Продукти не знайдено",
                    "products_count": 0,
                    "sync_stats": {"created": 0, "updated": 0, "errors": 0}
                }

            # Зберігаємо в БД
            sync_stats = await self._save_products_to_db(products)

            return {
                "status": "success",
                "message": "Синхронізація завершена",
                "products_count": len(products),
                "sync_stats": sync_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Помилка синхронізації {self.exchange_name} продуктів: {e}")
            return {
                "status": "error",
                "message": f"Помилка синхронізації: {str(e)}",
                "products_count": 0,
                "sync_stats": {"created": 0, "updated": 0, "errors": 1},
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def _save_products_to_db(self, products: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Зберігає продукти в базу даних.

        Args:
            products: Список нормалізованих продуктів

        Returns:
            Dict з кількістю створених/оновлених продуктів
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
                                is_cefi=product_data["is_cefi"],
                                min_amount=product_data["min_amount"],
                                max_amount=product_data.get("max_amount"),
                                lock_period_days=product_data["lock_period_days"],
                                max_apy=product_data["max_apy"],
                                risk_level=product_data["risk_level"],
                                is_active=product_data["is_active"],
                                website_url=product_data.get("website_url"),
                                description=product_data.get("description"),
                                product_type=product_data.get("product_type"),
                                raw_data=product_data.get("raw_data")
                            )
                            updated = await YieldProductCRUD.update_product(
                                db, product_data["id"], update_data
                            )
                            if updated:
                                stats["updated"] += 1
                        else:
                            # Створюємо новий
                            # Обрізаємо символ до 20 символів якщо він занадто довгий
                            symbol = product_data["symbol"][:20] if len(product_data["symbol"]) > 20 else product_data["symbol"]
                            
                            db_product = YieldProductDB(
                                id=product_data["id"],
                                symbol=symbol,
                                name=product_data["name"],
                                provider=product_data["provider"],
                                apy=product_data["apy"],
                                is_cefi=product_data["is_cefi"],
                                min_amount=product_data["min_amount"],
                                max_amount=product_data.get("max_amount"),
                                lock_period_days=product_data["lock_period_days"],
                                max_apy=product_data["max_apy"],
                                risk_level=product_data["risk_level"],
                                is_active=product_data["is_active"],
                                website_url=product_data.get("website_url"),
                                description=product_data.get("description"),
                                product_type=product_data.get("product_type"),
                                raw_data=product_data.get("raw_data")
                            )

                            db.add(db_product)
                            await db.commit()
                            await db.refresh(db_product)
                            stats["created"] += 1

                        # Зберігаємо raw дані (оновлюємо якщо існує)
                        try:
                            await ExchangeDataCRUD.create_exchange_data(
                                db,
                                product_id=product_data["id"],
                                exchange=self.exchange_name,
                                raw_data=product_data.get("raw_data", {}),
                                api_endpoint=f"/v1/{self.exchange_name}/",
                                request_timestamp=datetime.now(UTC).replace(tzinfo=None)
                            )
                        except Exception as exchange_data_error:
                            # Якщо duplicate key - ігноруємо, це нормально при оновленні
                            if "unique_product_exchange" in str(exchange_data_error) or "duplicate key" in str(exchange_data_error).lower():
                                logger.debug(f"ℹ️ Exchange data вже існує для {product_data['id']} на {self.exchange_name}, пропускаємо")
                            else:
                                logger.warning(f"⚠️ Помилка збереження exchange data для {product_data['id']}: {exchange_data_error}")

                    except Exception as e:
                        logger.error(f"❌ Помилка збереження продукту {product_data.get('id', 'unknown')}: {e}")
                        stats["errors"] += 1
                        continue

                logger.info(f"✅ {self.exchange_name.title()} продукти збережено: {stats['created']} створено, {stats['updated']} оновлено, {stats['errors']} помилок")

            except Exception as e:
                logger.error(f"❌ Помилка збереження продуктів {self.exchange_name}: {e}")
                stats["errors"] += len(products)

        return stats

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Повертає статус здоров'я сервісу.

        Returns:
            Dict з інформацією про стан сервісу
        """
        try:
            connection_test = await self.test_connection()

            return {
                "service": self.exchange_name,
                "configured": self.is_configured,
                "connection": connection_test,
                "cache_stats": await cache_manager.get_cache_stats(),
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            return {
                "service": self.exchange_name,
                "configured": self.is_configured,
                "connection": {
                    "status": "error",
                    "message": str(e)
                },
                "timestamp": datetime.now(UTC).isoformat()
            }
