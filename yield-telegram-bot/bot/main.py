import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.fsm.strategy import FSMStrategy

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.metrics import metrics_collector
from bot.db.database import init_database, shutdown_database, create_tables
from bot.schedulers.cache_updater import start_cache_updater, stop_cache_updater
from bot.schedulers.log_cleaner import log_cleaner
from bot.middleware.logging import LoggingMiddleware
from bot.middleware.throttling import ThrottlingMiddleware
from bot.middleware.tracking import TrackingMiddleware
from bot.services.event_processor import event_processor
from bot.services.session_manager import session_manager
from bot.handlers import (
    start,
    help,
    recommendations,
    language,
    main_menu,
    exchange_products,
    filtered_products,
    callback_handlers,
)
from bot.broadcasts.scheduler import BroadcastScheduler
from bot.broadcasts.queue import BroadcastQueue


broadcast_queue = BroadcastQueue()
broadcast_scheduler = BroadcastScheduler(queue=broadcast_queue)


@asynccontextmanager
async def lifespan_context():
    logger.info("🚀 Ініціалізація бота...")

    db_ok = await init_database()
    if not db_ok:
        logger.error("❌ Не вдалося ініціалізувати БД. Вихід.")
        sys.exit(1)

    await create_tables()
    logger.info("✅ БД ініціалізована та таблиці перевірені")

    metrics_collector.start_server(port=8001)
    logger.info("✅ Prometheus метрики запущені на порту 8001")

    await start_cache_updater()
    logger.info("✅ Cache updater запущений")

    try:
        await session_manager.initialize()
        await event_processor.initialize()
        await event_processor.start_processing()
        logger.info("✅ Tracking система ініціалізована")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося ініціалізувати tracking систему: {e}")

    try:
        await log_cleaner.start()
        logger.info("✅ Log cleaner запущений")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося запустити log cleaner: {e}")

    try:
        await broadcast_scheduler.start()
        logger.info("✅ Broadcast scheduler запущений")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося запустити broadcast scheduler: {e}")

    await warmup_cache()

    yield

    logger.info("🛑 Завершення роботи бота...")

    try:
        await broadcast_scheduler.stop()
        logger.info("✅ Broadcast scheduler зупинений")
    except Exception as e:
        logger.error(f"⚠️ Помилка зупинки broadcast scheduler: {e}")

    try:
        await log_cleaner.stop()
        logger.info("✅ Log cleaner зупинений")
    except Exception as e:
        logger.error(f"⚠️ Помилка зупинки log cleaner: {e}")

    try:
        await event_processor.stop_processing()
        logger.info("✅ Event processor зупинений")
    except Exception as e:
        logger.error(f"⚠️ Помилка зупинки event processor: {e}")

    await stop_cache_updater()
    logger.info("✅ Cache updater зупинений")

    await shutdown_database()
    logger.info("✅ БД закрита")


async def warmup_cache():
    from bot.schedulers.cache_updater import force_cache_update
    from bot.utils.language_cache import language_cache
    from bot.services.api_client import APIClient
    from bot.handlers.main_menu import generate_main_menu_content

    try:
        logger.info("🔥 Початок pre-warming кешу...")

        await force_cache_update()

        async def refresh_main_menu_for_lang(lang: str):
            api_client = APIClient()
            try:
                return await generate_main_menu_content(api_client, 0, lang)
            finally:
                await api_client.close()

        await language_cache.warmup_cache(
            key_prefix="main_menu",
            refresh_func=refresh_main_menu_for_lang,
            ttl=settings.MAIN_MENU_TTL,
        )

        logger.info("✅ Кеш попередньо розігрітий для всіх мов")
    except Exception as e:
        logger.error(f"⚠️ Помилка при pre-warming кешу: {e}", exc_info=True)


def create_dispatcher() -> Dispatcher:
    # FSM Storage (Redis)
    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
    )

    dp = Dispatcher(
        storage=storage,
        fsm_strategy=FSMStrategy.USER_IN_CHAT,
    )

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(TrackingMiddleware())

    dp.message.middleware(
        ThrottlingMiddleware(redis_url=settings.REDIS_URL, rate_limit=1, time_window=2)
    )

    dp.include_router(callback_handlers.router)
    dp.include_router(main_menu.router)
    dp.include_router(exchange_products.router)
    dp.include_router(filtered_products.router)
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(recommendations.router)
    dp.include_router(language.router)

    return dp


async def main() -> None:
    logger.info("🤖 Запуск EarnAggregator Telegram Bot...")

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = create_dispatcher()

    def signal_handler(signum, frame):
        logger.info(f"📡 Отримано сигнал {signum}. Завершення...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    async with lifespan_context():
        try:
            logger.info("✅ Бот запущено і готовий до роботи!")
            logger.info(
                "📋 Доступні команди: /main, /yield <SYMBOL>, /top, /help, /recommendations, /rec1-rec10, /exchanges"
            )

            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                close_bot_session=True,
                interval=0.5,
                timeout=20,
                request_timeout=15,
            )

        except Exception as e:
            logger.error(f"❌ Критична помилка в роботі бота: {e}", exc_info=True)
            raise
        finally:
            logger.info("👋 Бот завершив роботу")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"💥 Аварійне завершення роботи бота: {e}", exc_info=True)
        sys.exit(1)
