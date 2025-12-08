"""
Сервіс для формування та оновлення таблиці top_products.

Логіка:
- Отримує trending монети з CoinGecko.
- Для кожної монети знаходить найкращий flexible APY у yield_products.
- Зберігає TOP 10 у таблицю top_products.
- Не видаляє попередні дані якщо CoinGecko недоступний.
"""

from typing import Dict, Any
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.coingecko_service import coingecko_service
from app.db.crud import TopProductCRUD
from app.utils.logger import logger


class TopProductsService:
    """Сервіс роботи з TOP продуктами."""

    async def update_top_products(self, db: AsyncSession, limit: int = 10) -> Dict[str, Any]:
        """
        Оновлює таблицю top_products.

        - Якщо CoinGecko недоступний: повертає помилку, старі дані залишаються.
        - Якщо продукт не знайдено: best_apy = 0.0, best_exchange/product_id = None.
        """
        start_time = datetime.now(UTC)
        updated = 0
        coins_processed = 0

        try:
            trending_coins = await coingecko_service.get_trending_coins()
            if not trending_coins:
                logger.warning("[TopProducts] ⚠️ Не отримано trending монет з CoinGecko")
                return {
                    "success": False,
                    "message": "CoinGecko trending недоступний",
                    "products_updated": 0,
                    "coins_processed": 0,
                }

            for rank, coin in enumerate(trending_coins[:limit], start=1):
                symbol = coin.get("symbol", "").upper()
                if not symbol:
                    logger.warning(f"[TopProducts] ⚠️ Пропуск монети без символу: {coin}")
                    continue

                coin_name = coin.get("name")
                market_cap_rank = coin.get("market_cap_rank")

                best_product = await TopProductCRUD.get_best_flexible_product(db, symbol)
                best_apy = float(best_product.apy) if best_product else 0.0
                best_exchange = best_product.provider if best_product else None
                product_id = best_product.id if best_product else None

                await TopProductCRUD.upsert_top_product(
                    db=db,
                    rank=rank,
                    symbol=symbol,
                    coin_name=coin_name,
                    market_cap_rank=market_cap_rank,
                    best_apy=best_apy,
                    best_exchange=best_exchange,
                    product_id=product_id,
                )
                updated += 1
                coins_processed += 1

            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.info(f"[TopProducts] ✅ Оновлено {updated} записів за {duration:.2f}s")

            return {
                "success": True,
                "message": "top_products оновлено",
                "products_updated": updated,
                "coins_processed": coins_processed,
                "duration_seconds": duration,
            }

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"[TopProducts] ❌ Помилка оновлення top_products: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "products_updated": updated,
                "coins_processed": coins_processed,
                "duration_seconds": duration,
            }


top_products_service = TopProductsService()

