from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, UTC

from app.db.crud import PriorityProductCRUD, YieldProductCRUD
from app.utils.logger import logger


class PriorityProductsService:
    PRIORITY_SYMBOLS = ["BTC", "ETH", "SOL", "USDT"]

    ACTIVE_EXCHANGES = [
        "binance",
        "bybit",
        "bitmart",
        "okx",
        "mexc",
        "gate",
        "bitget",
        "kraken",
        "kucoin",
        "htx",
    ]

    EXCHANGE_TO_PROVIDER = {
        "binance": "Binance",
        "bybit": "Bybit",
        "bitmart": "BitMart",
        "okx": "OKX",
        "mexc": "MEXC",
        "gate": "gate",
        "bitget": "bitget",
        "kraken": "Kraken",
        "kucoin": "KuCoin",
        "htx": "HTX",
    }

    @staticmethod
    async def update_priority_products_for_exchange(db: AsyncSession, exchange: str) -> int:
        updated_count = 0

        try:
            logger.info(f"🔄 Оновлення priority_products для {exchange}")

            for symbol in PriorityProductsService.PRIORITY_SYMBOLS:
                try:
                    provider = PriorityProductsService.EXCHANGE_TO_PROVIDER.get(
                        exchange.lower(), exchange.title()
                    )

                    logger.info(f"🔍 Пошук продуктів для {exchange}/{symbol} з provider={provider}")
                    products = await YieldProductCRUD.get_products_by_symbol_and_provider(
                        db, symbol, provider
                    )

                    logger.info(
                        f"📊 {exchange}/{symbol}: знайдено {len(products)} продуктів "
                        f"з provider={provider}"
                    )

                    if products:
                        for p in products[:3]:
                            logger.info(
                                f"  - {p.symbol} {p.provider} APY={p.apy}% "
                                f"lock={p.lock_period_days} active={p.is_active}"
                            )

                    flexible_products = [
                        p for p in products if p.lock_period_days == 0 and p.is_active
                    ]

                    logger.info(
                        f"⚡ {exchange}/{symbol}: після фільтрації flexible: {len(flexible_products)} продуктів"
                    )

                    if flexible_products:
                        for p in flexible_products[:3]:
                            logger.info(f"  Flexible: {p.symbol} APY={p.apy}% product_id={p.id}")

                    if flexible_products:
                        best_product = max(flexible_products, key=lambda p: p.apy)

                        await PriorityProductCRUD.upsert_priority_product(
                            db=db,
                            exchange=exchange,
                            symbol=symbol,
                            apy=best_product.apy,
                            is_active=best_product.is_active,
                            product_id=best_product.id,
                            lock_period_days=0,
                        )
                        updated_count += 1
                        logger.info(
                            f"✅ {exchange}/{symbol}: APY={best_product.apy}% "
                            f"(product_id={best_product.id})"
                        )
                    else:
                        await PriorityProductCRUD.upsert_priority_product(
                            db=db,
                            exchange=exchange,
                            symbol=symbol,
                            apy=0.0,
                            is_active=False,
                            product_id=None,
                            lock_period_days=0,
                        )
                        updated_count += 1
                        logger.warning(f"⚠️ {exchange}/{symbol}: продукт не знайдено, APY=0.0%")

                except Exception as e:
                    logger.error(f"❌ Помилка оновлення {exchange}/{symbol}: {e}", exc_info=True)

                    try:
                        await PriorityProductCRUD.upsert_priority_product(
                            db=db,
                            exchange=exchange,
                            symbol=symbol,
                            apy=0.0,
                            is_active=False,
                            product_id=None,
                            lock_period_days=0,
                        )
                        updated_count += 1
                    except Exception as inner_e:
                        logger.error(f"❌ Критична помилка створення fallback запису: {inner_e}")

            logger.info(f"✅ Оновлено {updated_count} priority продуктів для {exchange}")
            return updated_count

        except Exception as e:
            logger.error(
                f"❌ Критична помилка оновлення priority_products для {exchange}: {e}",
                exc_info=True,
            )
            return updated_count

    @staticmethod
    async def update_all_exchanges(db: AsyncSession) -> dict:
        stats = {}
        total_updated = 0

        try:
            logger.info("🔄 Початок оновлення priority_products для всіх бірж")

            for exchange in PriorityProductsService.ACTIVE_EXCHANGES:
                try:
                    count = await PriorityProductsService.update_priority_products_for_exchange(
                        db, exchange
                    )
                    stats[exchange] = count
                    total_updated += count
                except Exception as e:
                    logger.error(f"❌ Помилка оновлення {exchange}: {e}", exc_info=True)
                    stats[exchange] = 0

            logger.info(
                f"✅ Оновлення priority_products завершено: "
                f"{total_updated} продуктів оновлено для {len(stats)} бірж"
            )

            stats["total"] = total_updated
            return stats

        except Exception as e:
            logger.error(f"❌ Критична помилка оновлення всіх бірж: {e}", exc_info=True)
            return stats


priority_products_service = PriorityProductsService()
