import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import text

from app.utils.logger import logger
from app.db.database import db_manager
from app.db.crud import create_or_update_coins_popularity


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_MARKETS_ENDPOINT = "/coins/markets"
COINGECKO_TRENDING_ENDPOINT = "/search/trending"
COINGECKO_REQUEST_TIMEOUT = 30.0
COINGECKO_MAX_RETRIES = 3
COINGECKO_RETRY_DELAY = 2


DEFAULT_VS_CURRENCY = "usd"
DEFAULT_ORDER = "market_cap_desc"
DEFAULT_PER_PAGE = 250
DEFAULT_PAGE = 1


class CoinGeckoService:
    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self.timeout = COINGECKO_REQUEST_TIMEOUT

    async def get_top_coins_markets(
        self,
        vs_currency: str = DEFAULT_VS_CURRENCY,
        order: str = DEFAULT_ORDER,
        per_page: int = DEFAULT_PER_PAGE,
        page: int = DEFAULT_PAGE,
    ) -> List[Dict[str, Any]]:
        endpoint = COINGECKO_MARKETS_ENDPOINT
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }

        logger.info(f"[CoinGecko] Запит топ монет: {per_page} монет, сторінка {page}")

        for attempt in range(COINGECKO_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}{endpoint}", params=params)
                    response.raise_for_status()

                    data = response.json()
                    logger.info(f"[CoinGecko] ✅ Отримано {len(data)} монет з CoinGecko API")

                    return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = int(e.response.headers.get("Retry-After", COINGECKO_RETRY_DELAY))
                    logger.warning(f"[CoinGecko] Rate limit, чекаємо {wait_time} секунд...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:
                    if attempt < COINGECKO_MAX_RETRIES - 1:
                        wait_time = COINGECKO_RETRY_DELAY**attempt
                        logger.warning(f"[CoinGecko] Server error, retry in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                logger.error(
                    f"[CoinGecko] HTTP помилка {e.response.status_code}: {e.response.text}"
                )
                raise

            except Exception as e:
                logger.error(f"[CoinGecko] Помилка запиту: {e}")
                if attempt < COINGECKO_MAX_RETRIES - 1:
                    wait_time = COINGECKO_RETRY_DELAY**attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise Exception(
            f"Не вдалося отримати дані з CoinGecko API після {COINGECKO_MAX_RETRIES} спроб"
        )

    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        endpoint = COINGECKO_TRENDING_ENDPOINT

        logger.info("[CoinGecko] Запит trending cryptocurrencies")

        for attempt in range(COINGECKO_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response.raise_for_status()

                    data = response.json()

                    coins = []
                    if isinstance(data, dict) and "coins" in data:
                        for coin_item in data["coins"]:
                            if "item" in coin_item:
                                coin_data = coin_item["item"]

                                normalized_coin = self._normalize_trending_coin_data(coin_data)
                                coins.append(normalized_coin)

                    logger.info(f"[CoinGecko] ✅ Отримано {len(coins)} trending cryptocurrencies")
                    return coins

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = int(e.response.headers.get("Retry-After", COINGECKO_RETRY_DELAY))
                    logger.warning(f"[CoinGecko] Rate limit, чекаємо {wait_time} секунд...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:
                    if attempt < COINGECKO_MAX_RETRIES - 1:
                        wait_time = COINGECKO_RETRY_DELAY**attempt
                        logger.warning(f"[CoinGecko] Server error, retry in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                logger.error(
                    f"[CoinGecko] HTTP помилка {e.response.status_code}: {e.response.text}"
                )
                raise

            except Exception as e:
                logger.error(f"[CoinGecko] Помилка запиту: {e}")
                if attempt < COINGECKO_MAX_RETRIES - 1:
                    wait_time = COINGECKO_RETRY_DELAY**attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise Exception(
            f"Не вдалося отримати trending дані з CoinGecko API після {COINGECKO_MAX_RETRIES} спроб"
        )

    async def add_missing_htx_symbols(self) -> Dict[str, Any]:
        start_time = datetime.now()

        try:
            logger.info("[CoinGecko] 🔄 Початок додавання HTX символів до популярності")

            htx_symbols = await self._get_htx_symbols_from_products()

            if not htx_symbols:
                logger.warning("[CoinGecko] ⚠️ Не знайдено HTX символів")
                return {
                    "success": False,
                    "message": "Не знайдено HTX символів",
                    "symbols_processed": 0,
                    "symbols_added": 0,
                }

            added_count = 0
            session = db_manager.session_factory()
            try:
                for symbol in htx_symbols:
                    try:
                        popularity_data = {
                            "coin_id": f"htx_{symbol.lower()}",
                            "symbol": symbol.upper(),
                            "name": f"{symbol.upper()} (HTX Product)",
                            "market_cap_rank": 9999,
                            "current_price": None,
                            "market_cap": None,
                        }

                        await create_or_update_coins_popularity(session, popularity_data)
                        added_count += 1

                        if added_count % 10 == 0:
                            logger.info(f"[CoinGecko] Додано {added_count} HTX символів")

                    except Exception as e:
                        logger.error(f"[CoinGecko] Помилка додавання HTX символу {symbol}: {e}")

                await session.commit()
            finally:
                await session.close()

            duration = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "message": f"Додано {added_count} HTX символів до таблиці популярності",
                "symbols_processed": len(htx_symbols),
                "symbols_added": added_count,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Критична помилка додавання HTX символів: {e}")
            return {
                "success": False,
                "message": f"Помилка додавання HTX символів: {e}",
                "symbols_processed": 0,
                "symbols_added": 0,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }

    async def _get_htx_symbols_from_products(self) -> List[str]:
        session = db_manager.session_factory()
        try:
            from sqlalchemy import select, distinct
            from app.db.models import YieldProductDB

            result = await session.execute(
                select(distinct(YieldProductDB.symbol))
                .where(YieldProductDB.provider == "HTX")
                .where(YieldProductDB.is_active == True)
            )

            symbols = [row[0] for row in result.fetchall()]
            logger.info(f"[CoinGecko] Знайдено {len(symbols)} унікальних HTX символів")
            return symbols

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання HTX символів: {e}")
            return []
        finally:
            await session.close()

    async def update_coins_popularity(self) -> Dict[str, Any]:
        start_time = datetime.now()

        try:
            logger.info("[CoinGecko] 🔄 Початок оновлення рейтингу популярності монет (топ 250)")

            coins_data = await self.get_top_coins_markets(per_page=250, page=1)
            logger.info(
                f"[CoinGecko] Отримано {len(coins_data)} монет (топ 250 за ринковою капіталізацією)"
            )

            if not coins_data:
                logger.warning("[CoinGecko] ⚠️ Не отримано даних з CoinGecko API")
                return {
                    "success": False,
                    "message": "Не отримано даних з CoinGecko API",
                    "coins_processed": 0,
                    "coins_updated": 0,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                }

            processed = 0
            updated = 0
            errors = 0

            session = db_manager.session_factory()
            try:
                for coin_data in coins_data:
                    try:
                        normalized_coin = self._normalize_coin_data(coin_data)

                        await create_or_update_coins_popularity(session, normalized_coin)

                        processed += 1

                        if processed % 50 == 0:
                            logger.info(
                                f"[CoinGecko] Оброблено {processed}/{len(coins_data)} монет"
                            )

                    except Exception as e:
                        errors += 1
                        logger.error(
                            f"[CoinGecko] Помилка обробки монети {coin_data.get('symbol', '?')}: {e}"
                        )

                updated = processed - errors

                await session.commit()
            finally:
                await session.close()

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "success": True,
                "message": f"Оновлено рейтинг {updated} монет з CoinGecko",
                "coins_processed": processed,
                "coins_updated": updated,
                "errors": errors,
                "duration_seconds": duration,
                "updated_at": datetime.now().isoformat(),
            }

            logger.info(f"[CoinGecko] ✅ Оновлення завершено: {result['message']}")
            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"[CoinGecko] ❌ Помилка оновлення: {e}", exc_info=True)

            return {
                "success": False,
                "message": f"Помилка оновлення: {str(e)}",
                "coins_processed": 0,
                "coins_updated": 0,
                "errors": 1,
                "duration_seconds": duration,
            }

    def _normalize_coin_data(self, coin_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "coin_id": coin_data.get("id", ""),
            "symbol": coin_data.get("symbol", "").upper(),
            "name": coin_data.get("name", ""),
            "market_cap_rank": coin_data.get("market_cap_rank", 9999),
            "current_price": coin_data.get("current_price"),
            "market_cap": coin_data.get("market_cap"),
        }

    def _normalize_trending_coin_data(self, coin_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "coin_id": coin_data.get("id", ""),
            "coin_id_num": coin_data.get("coin_id", 0),
            "symbol": coin_data.get("symbol", "").upper(),
            "name": coin_data.get("name", ""),
            "market_cap_rank": coin_data.get("market_cap_rank", 9999),
            "thumb": coin_data.get("thumb", ""),
            "large": coin_data.get("large", ""),
            "slug": coin_data.get("slug", ""),
            "price_btc": coin_data.get("price_btc", 0.0),
            "score": coin_data.get("score", 0),
        }

    async def get_trending_score(self, symbol: str) -> Optional[int]:
        try:
            trending_coins = await self.get_trending_coins()

            normalized_symbol = symbol.upper()

            for coin in trending_coins:
                if coin.get("symbol") == normalized_symbol:
                    return coin.get("score", 0)

            return None

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання trending score для {symbol}: {e}")
            return None

    async def get_popularity_rank(self, symbol: str) -> Optional[int]:
        session = db_manager.session_factory()
        try:
            normalized_symbol = symbol.upper()

            result = await session.execute(
                text("""
                SELECT market_cap_rank
                FROM coins_popularity
                WHERE symbol = :symbol
                """),
                {"symbol": normalized_symbol},
            )

            rank = result.scalar()
            return rank

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання рейтингу для {symbol}: {e}")
            return None
        finally:
            await session.close()

    async def get_trending_stats(self) -> Dict[str, Any]:
        try:
            trending_coins = await self.get_trending_coins()

            return {
                "total_trending_coins": len(trending_coins),
                "trending_coins": trending_coins[:10],
                "last_update": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання trending статистики: {e}")
            return {"total_trending_coins": 0, "trending_coins": [], "last_update": None}

    async def get_popularity_stats(self) -> Dict[str, Any]:
        session = db_manager.session_factory()
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM coins_popularity"))
            total_coins = result.scalar()

            result = await session.execute(text("SELECT MAX(updated_at) FROM coins_popularity"))
            last_update = result.scalar()

            result = await session.execute(
                text("""
                SELECT symbol, market_cap_rank
                FROM coins_popularity
                ORDER BY market_cap_rank ASC
                LIMIT 5
                """)
            )
            top_coins = result.fetchall()

            return {
                "total_coins": total_coins,
                "last_update": last_update.isoformat() if last_update else None,
                "top_coins": [{"symbol": coin[0], "rank": coin[1]} for coin in top_coins],
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання статистики: {e}")
            return {"total_coins": 0, "last_update": None, "top_coins": []}
        finally:
            await session.close()


coingecko_service = CoinGeckoService()
