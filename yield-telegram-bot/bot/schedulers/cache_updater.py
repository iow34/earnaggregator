import asyncio
from datetime import datetime, UTC
from typing import Optional

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.cache_manager import cache_manager
from bot.services.api_client import APIClient


class CacheUpdater:
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self.running:
            logger.warning("Cache updater вже запущений")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("🚀 Cache updater запущений")

    async def stop(self) -> None:
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Cache updater зупинений")

    async def _run_scheduler(self) -> None:
        try:
            while self.running:
                try:
                    await self._update_all_caches()
                except Exception as e:
                    logger.error(f"Помилка в циклі оновлення кешу: {e}", exc_info=True)

                await asyncio.sleep(900)

        except asyncio.CancelledError:
            logger.info("Cache updater скасований")
            raise
        except Exception as e:
            logger.error(f"Критична помилка в cache updater: {e}", exc_info=True)
            raise

    async def _update_all_caches(self) -> None:
        logger.info("🔄 Початок оновлення кешу...")

        await self._update_main_menu_cache()

        await self._update_trending_cache()

        logger.info("✅ Оновлення кешу завершено")

    async def _update_main_menu_cache(self) -> None:
        try:
            logger.info("📱 Оновлення кешу головного меню...")

            from bot.handlers.main_menu import _format_top_10_section, _format_exchanges_quick_view

            api_client = APIClient()

            try:
                top10_task = _format_top_10_section(api_client)
                exchanges_task = _format_exchanges_quick_view(api_client, telegram_id=0)

                top10_text, exchanges_text = await asyncio.gather(top10_task, exchanges_task)

                text = "💰 <b>Crypto Earn Products</b>\n\n"
                text += top10_text
                text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                text += exchanges_text
                text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                text += "💡 <i>Натисніть на біржу або використовуйте команди нижче:</i>"

                menu_data = {
                    "text": text,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "version": "v1",
                }

                cache_key = "main_menu:v1"
                success = await cache_manager.set(cache_key, menu_data, ttl=settings.MAIN_MENU_TTL)

                if success:
                    logger.info(
                        f"💾 Кеш головного меню оновлено на {settings.MAIN_MENU_TTL} секунд"
                    )
                else:
                    logger.warning("⚠️ Не вдалося оновити кеш головного меню")

            finally:
                await api_client.close()

        except Exception as e:
            logger.error(f"❌ Помилка оновлення кешу головного меню: {e}", exc_info=True)

    async def _update_trending_cache(self) -> None:
        try:
            logger.info("📈 Оновлення кешу trending даних...")

            api_client = APIClient()

            try:
                trending_data = await api_client.get_trending_coins()

                if trending_data.get("success"):
                    cache_key = "trending_coins"
                    success = await cache_manager.set(
                        cache_key, trending_data, ttl=settings.TRENDING_TTL
                    )

                    if success:
                        logger.info(
                            f"💾 Кеш trending coins оновлено на {settings.TRENDING_TTL} секунд"
                        )
                    else:
                        logger.warning("⚠️ Не вдалося оновити кеш trending coins")

            finally:
                await api_client.close()

        except Exception as e:
            logger.error(f"❌ Помилка оновлення кешу trending даних: {e}", exc_info=True)

    async def force_update_cache(self, cache_type: str = "all") -> bool:
        try:
            logger.info(f"🔄 Примусове оновлення кешу: {cache_type}")

            if cache_type in ("all", "main_menu"):
                await self._update_main_menu_cache()

            if cache_type in ("all", "trending"):
                await self._update_trending_cache()

            logger.info(f"✅ Примусове оновлення кешу '{cache_type}' завершено")
            return True

        except Exception as e:
            logger.error(
                f"❌ Помилка примусового оновлення кешу '{cache_type}': {e}", exc_info=True
            )
            return False


cache_updater = CacheUpdater()


async def start_cache_updater():
    await cache_updater.start()


async def stop_cache_updater():
    await cache_updater.stop()


async def force_cache_update(cache_type: str = "all"):
    return await cache_updater.force_update_cache(cache_type)
