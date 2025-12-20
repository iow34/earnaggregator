"""
Головний файл Telegram бота.

Запуск: python -m bot.main
"""

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
    start, help, recommendations, language,
    main_menu, exchange_products,
    filtered_products, callback_handlers
)
from bot.broadcasts.scheduler import BroadcastScheduler
from bot.broadcasts.queue import BroadcastQueue

# Глобальні інстанси для scheduler
broadcast_queue = BroadcastQueue()
broadcast_scheduler = BroadcastScheduler(queue=broadcast_queue)


@asynccontextmanager
async def lifespan_context():
    """Контекст менеджер для lifecycle подій."""
    logger.info("🚀 Ініціалізація бота...")

    # Ініціалізація БД
    db_ok = await init_database()
    if not db_ok:
        logger.error("❌ Не вдалося ініціалізувати БД. Вихід.")
        sys.exit(1)

    # Створення таблиць (тільки якщо не існують - зберігає дані користувачів)
    await create_tables()
    logger.info("✅ БД ініціалізована та таблиці перевірені")

    # Запуск Prometheus метрик сервера
    metrics_collector.start_server(port=8001)
    logger.info("✅ Prometheus метрики запущені на порту 8001")

    # Запуск cache updater
    await start_cache_updater()
    logger.info("✅ Cache updater запущений")

    # Ініціалізація tracking системи
    try:
        await session_manager.initialize()
        await event_processor.initialize()
        await event_processor.start_processing()
        logger.info("✅ Tracking система ініціалізована")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося ініціалізувати tracking систему: {e}")

    # Запуск log cleaner
    try:
        await log_cleaner.start()
        logger.info("✅ Log cleaner запущений")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося запустити log cleaner: {e}")

    # Запуск broadcast scheduler
    try:
        await broadcast_scheduler.start()
        logger.info("✅ Broadcast scheduler запущений")
    except Exception as e:
        logger.error(f"⚠️ Не вдалося запустити broadcast scheduler: {e}")

    # Pre-warming кешу
    await warmup_cache()

    yield

    logger.info("🛑 Завершення роботи бота...")

    # Зупинка broadcast scheduler
    try:
        await broadcast_scheduler.stop()
        logger.info("✅ Broadcast scheduler зупинений")
    except Exception as e:
        logger.error(f"⚠️ Помилка зупинки broadcast scheduler: {e}")

    # Зупинка tracking системи
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

    # Зупинка cache updater
    await stop_cache_updater()
    logger.info("✅ Cache updater зупинений")

    # Закриття БД
    await shutdown_database()
    logger.info("✅ БД закрита")


async def warmup_cache():
    """Попереднє заповнення кешу при старті бота для всіх мов."""
    from bot.schedulers.cache_updater import force_cache_update
    from bot.utils.language_cache import language_cache
    from bot.services.api_client import APIClient
    from bot.handlers.main_menu import generate_main_menu_content

    try:
        logger.info("🔥 Початок pre-warming кешу...")
        
        # 1. Стандартне оновлення кешу
        await force_cache_update()
        
        # 2. 🔥 Warmup мультимовного кешу для головного меню
        async def refresh_main_menu_for_lang(lang: str):
            """Оновити дані головного меню для конкретної мови."""
            api_client = APIClient()
            try:
                return await generate_main_menu_content(api_client, 0, lang)
            finally:
                await api_client.close()
        
        # Розігріваємо кеш для всіх мов
        await language_cache.warmup_cache(
            key_prefix="main_menu",
            refresh_func=refresh_main_menu_for_lang,
            ttl=settings.MAIN_MENU_TTL
        )
        
        logger.info("✅ Кеш попередньо розігрітий для всіх мов")
    except Exception as e:
        logger.error(f"⚠️ Помилка при pre-warming кешу: {e}", exc_info=True)
        # Не критична помилка - продовжуємо роботу


def create_dispatcher() -> Dispatcher:
    """Створення та налаштування Dispatcher."""
    # FSM Storage (Redis)
    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
    )

    # Створення Dispatcher з FSM стратегією
    dp = Dispatcher(
        storage=storage,
        fsm_strategy=FSMStrategy.USER_IN_CHAT,  # Стан прив'язаний до користувача в чаті
    )

    # Реєстрація middleware (порядок важливий!)
    dp.update.middleware(LoggingMiddleware())  # Логування всіх апдейтів
    dp.update.middleware(TrackingMiddleware())  # Трекінг всіх апдейтів
    # FirstContactMiddleware видалено - welcome messages більше не відправляються,
    # оскільки disclaimer в /start містить всю необхідну інформацію
    dp.message.middleware(ThrottlingMiddleware(  # Антифлуд тільки для повідомлень
        redis_url=settings.REDIS_URL,
        rate_limit=1,  # 1 повідомлення за 2 секунди
        time_window=2
    ))

    # Реєстрація handlers (порядок важливий - від специфічних до загальних)
    dp.include_router(callback_handlers.router)  # Спочатку callback handlers
    dp.include_router(main_menu.router)
    dp.include_router(exchange_products.router)
    dp.include_router(filtered_products.router)
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(recommendations.router)
    dp.include_router(language.router)

    return dp


async def main() -> None:
    """Головна функція бота."""
    logger.info("🤖 Запуск EarnAggregator Telegram Bot...")

    # Створення бота з налаштуваннями
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Створення dispatcher
    dp = create_dispatcher()

    # Налаштування сигналів для graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"📡 Отримано сигнал {signum}. Завершення...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Запуск бота з lifecycle контекстом
    async with lifespan_context():
        try:
            logger.info("✅ Бот запущено і готовий до роботи!")
            logger.info("📋 Доступні команди: /main, /yield <SYMBOL>, /top, /help, /recommendations, /rec1-rec10, /exchanges")

            # Запуск polling
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                close_bot_session=True
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
