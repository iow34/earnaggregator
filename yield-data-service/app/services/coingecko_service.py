"""
Сервіс для отримання даних популярності монет з CoinGecko API.

Відповідно до ТЗ: Сортування продуктів у Telegram-боті за параметром "Популярні"
"""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import text

from app.utils.logger import logger
from app.db.database import db_manager
from app.db.crud import create_or_update_coins_popularity

# Налаштування CoinGecko API
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_MARKETS_ENDPOINT = "/coins/markets"
COINGECKO_TRENDING_ENDPOINT = "/search/trending"
COINGECKO_REQUEST_TIMEOUT = 30.0
COINGECKO_MAX_RETRIES = 3
COINGECKO_RETRY_DELAY = 2

# Параметри запиту
DEFAULT_VS_CURRENCY = "usd"
DEFAULT_ORDER = "market_cap_desc"
DEFAULT_PER_PAGE = 250
DEFAULT_PAGE = 1


class CoinGeckoService:
    """
    Сервіс для роботи з CoinGecko API.

    Відповідає за отримання та зберігання рейтингу популярності монет.
    """

    def __init__(self):
        """
        Ініціалізує CoinGecko сервіс.
        """
        self.base_url = COINGECKO_BASE_URL
        self.timeout = COINGECKO_REQUEST_TIMEOUT

    async def get_top_coins_markets(
        self,
        vs_currency: str = DEFAULT_VS_CURRENCY,
        order: str = DEFAULT_ORDER,
        per_page: int = DEFAULT_PER_PAGE,
        page: int = DEFAULT_PAGE
    ) -> List[Dict[str, Any]]:
        """
        Отримує топ монет з CoinGecko API.

        Args:
            vs_currency: Валюта порівняння (usd)
            order: Порядок сортування (market_cap_desc)
            per_page: Кількість результатів на сторінку (макс 250)
            page: Номер сторінки

        Returns:
            List[Dict]: Список монет з даними
        """
        endpoint = COINGECKO_MARKETS_ENDPOINT
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": "false"  # Не потрібні графіки
        }

        logger.info(f"[CoinGecko] Запит топ монет: {per_page} монет, сторінка {page}")

        for attempt in range(COINGECKO_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}{endpoint}",
                        params=params
                    )
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
                        wait_time = COINGECKO_RETRY_DELAY ** attempt
                        logger.warning(f"[CoinGecko] Server error, retry in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                logger.error(f"[CoinGecko] HTTP помилка {e.response.status_code}: {e.response.text}")
                raise

            except Exception as e:
                logger.error(f"[CoinGecko] Помилка запиту: {e}")
                if attempt < COINGECKO_MAX_RETRIES - 1:
                    wait_time = COINGECKO_RETRY_DELAY ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise Exception(f"Не вдалося отримати дані з CoinGecko API після {COINGECKO_MAX_RETRIES} спроб")

    async def get_trending_coins(self) -> List[Dict[str, Any]]:
        """
        Отримує trending cryptocurrencies з CoinGecko API.

        Returns:
            List[Dict]: Список trending монет з базовими даними
        """
        endpoint = COINGECKO_TRENDING_ENDPOINT

        logger.info("[CoinGecko] Запит trending cryptocurrencies")

        for attempt in range(COINGECKO_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    response.raise_for_status()

                    data = response.json()

                    # Витягуємо монети з відповіді
                    coins = []
                    if isinstance(data, dict) and "coins" in data:
                        for coin_item in data["coins"]:
                            if "item" in coin_item:
                                coin_data = coin_item["item"]
                                # Нормалізуємо дані trending монети
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
                        wait_time = COINGECKO_RETRY_DELAY ** attempt
                        logger.warning(f"[CoinGecko] Server error, retry in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                logger.error(f"[CoinGecko] HTTP помилка {e.response.status_code}: {e.response.text}")
                raise

            except Exception as e:
                logger.error(f"[CoinGecko] Помилка запиту: {e}")
                if attempt < COINGECKO_MAX_RETRIES - 1:
                    wait_time = COINGECKO_RETRY_DELAY ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise Exception(f"Не вдалося отримати trending дані з CoinGecko API після {COINGECKO_MAX_RETRIES} спроб")

    async def add_missing_htx_symbols(self) -> Dict[str, Any]:
        """
        Додає HTX символи, які відсутні в таблиці популярності.

        HTX може мати продукти для монет, які не входять в топ CoinGecko.
        Додаємо їх з market_cap_rank = 9999 для можливості сортування.
        """
        start_time = datetime.now()

        try:
            logger.info("[CoinGecko] 🔄 Початок додавання HTX символів до популярності")

            # Отримуємо всі HTX символи з продуктів
            htx_symbols = await self._get_htx_symbols_from_products()

            if not htx_symbols:
                logger.warning("[CoinGecko] ⚠️ Не знайдено HTX символів")
                return {
                    "success": False,
                    "message": "Не знайдено HTX символів",
                    "symbols_processed": 0,
                    "symbols_added": 0
                }

            added_count = 0
            session = db_manager.session_factory()
            try:
                for symbol in htx_symbols:
                    try:
                        # Завжди додаємо/оновлюємо HTX символи з низьким пріоритетом
                        # Це гарантує, що HTX продукти зможуть сортуватися за популярністю
                        popularity_data = {
                            "coin_id": f"htx_{symbol.lower()}",  # Унікальний ID для HTX
                            "symbol": symbol.upper(),
                            "name": f"{symbol.upper()} (HTX Product)",
                            "market_cap_rank": 9999,  # Низький пріоритет після основних монет
                            "current_price": None,
                            "market_cap": None
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
                "duration_seconds": duration
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Критична помилка додавання HTX символів: {e}")
            return {
                "success": False,
                "message": f"Помилка додавання HTX символів: {e}",
                "symbols_processed": 0,
                "symbols_added": 0,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }

    async def _get_htx_symbols_from_products(self) -> List[str]:
        """
        Отримує всі унікальні символи HTX продуктів з бази даних.
        """
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
        """
        Оновлює дані популярності монет у базі даних.

        Викликає CoinGecko API та зберігає дані в таблицю coins_popularity.
        Отримує тільки топ 250 монет за ринковою капіталізацією.

        Returns:
            Dict: Статистика оновлення
        """
        start_time = datetime.now()

        try:
            logger.info("[CoinGecko] 🔄 Початок оновлення рейтингу популярності монет (топ 250)")

            # Отримуємо тільки топ 250 монет з CoinGecko API
            coins_data = await self.get_top_coins_markets(per_page=250, page=1)
            logger.info(f"[CoinGecko] Отримано {len(coins_data)} монет (топ 250 за ринковою капіталізацією)")

            if not coins_data:
                logger.warning("[CoinGecko] ⚠️ Не отримано даних з CoinGecko API")
                return {
                    "success": False,
                    "message": "Не отримано даних з CoinGecko API",
                    "coins_processed": 0,
                    "coins_updated": 0,
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }

            # Статистика обробки
            processed = 0
            updated = 0
            errors = 0

            # Зберігаємо дані в БД
            session = db_manager.session_factory()
            try:
                for coin_data in coins_data:
                    try:
                        # Нормалізуємо дані
                        normalized_coin = self._normalize_coin_data(coin_data)

                        # Зберігаємо або оновлюємо в БД
                        await create_or_update_coins_popularity(session, normalized_coin)

                        processed += 1

                        # Логуємо кожні 50 монет
                        if processed % 50 == 0:
                            logger.info(f"[CoinGecko] Оброблено {processed}/{len(coins_data)} монет")

                    except Exception as e:
                        errors += 1
                        logger.error(f"[CoinGecko] Помилка обробки монети {coin_data.get('symbol', '?')}: {e}")

                # Підраховуємо оновлені записи
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
                "updated_at": datetime.now().isoformat()
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
                "duration_seconds": duration
            }

    def _normalize_coin_data(self, coin_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормалізує дані монети з CoinGecko API.

        Args:
            coin_data: Сирі дані з API

        Returns:
            Dict: Нормалізовані дані для БД
        """
        return {
            "coin_id": coin_data.get("id", ""),
            "symbol": coin_data.get("symbol", "").upper(),  # Переводимо в верхній регістр
            "name": coin_data.get("name", ""),
            "market_cap_rank": coin_data.get("market_cap_rank", 9999),
            "current_price": coin_data.get("current_price"),
            "market_cap": coin_data.get("market_cap")
        }

    def _normalize_trending_coin_data(self, coin_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормалізує дані trending монети з CoinGecko API.

        Args:
            coin_data: Сирі дані з trending API

        Returns:
            Dict: Нормалізовані дані trending монети
        """
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
            "score": coin_data.get("score", 0)
        }

    async def get_trending_score(self, symbol: str) -> Optional[int]:
        """
        Отримує trending score монети за символом.

        Args:
            symbol: Символ монети (BTC, ETH, тощо)

        Returns:
            Optional[int]: Trending score або None якщо не знайдено
        """
        try:
            # Отримуємо trending дані
            trending_coins = await self.get_trending_coins()

            # Шукаємо за нормалізованим символом
            normalized_symbol = symbol.upper()

            for coin in trending_coins:
                if coin.get("symbol") == normalized_symbol:
                    return coin.get("score", 0)

            return None

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання trending score для {symbol}: {e}")
            return None

    async def get_popularity_rank(self, symbol: str) -> Optional[int]:
        """
        Отримує рейтинг популярності монети за символом.

        Args:
            symbol: Символ монети (BTC, ETH, тощо)

        Returns:
            Optional[int]: Рейтинг популярності або None якщо не знайдено
        """
        session = db_manager.session_factory()
        try:
            # Шукаємо за нормалізованим символом
            normalized_symbol = symbol.upper()

            # Виконуємо запит до БД
            result = await session.execute(
                text("""
                SELECT market_cap_rank
                FROM coins_popularity
                WHERE symbol = :symbol
                """),
                {"symbol": normalized_symbol}
            )

            rank = result.scalar()
            return rank

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання рейтингу для {symbol}: {e}")
            return None
        finally:
            await session.close()

    async def get_trending_stats(self) -> Dict[str, Any]:
        """
        Отримує статистику по trending cryptocurrencies.

        Returns:
            Dict: Статистика trending
        """
        try:
            trending_coins = await self.get_trending_coins()

            return {
                "total_trending_coins": len(trending_coins),
                "trending_coins": trending_coins[:10],  # Повертаємо топ-10
                "last_update": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання trending статистики: {e}")
            return {
                "total_trending_coins": 0,
                "trending_coins": [],
                "last_update": None
            }

    async def get_popularity_stats(self) -> Dict[str, Any]:
        """
        Отримує статистику по даним популярності.

        Returns:
            Dict: Статистика
        """
        session = db_manager.session_factory()
        try:
            # Підраховуємо загальну кількість
            result = await session.execute(
                text("SELECT COUNT(*) FROM coins_popularity")
            )
            total_coins = result.scalar()

            # Знаходимо останнє оновлення
            result = await session.execute(
                text("SELECT MAX(updated_at) FROM coins_popularity")
            )
            last_update = result.scalar()

            # Знаходимо топ-5 монет
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
                "top_coins": [{"symbol": coin[0], "rank": coin[1]} for coin in top_coins]
            }

        except Exception as e:
            logger.error(f"[CoinGecko] Помилка отримання статистики: {e}")
            return {
                "total_coins": 0,
                "last_update": None,
                "top_coins": []
            }
        finally:
            await session.close()


# Глобальний екземпляр сервісу
coingecko_service = CoinGeckoService()
