from __future__ import annotations

import asyncio
import signal

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.broadcasts.queue import BroadcastQueue
from bot.broadcasts.scheduler import BroadcastScheduler
from bot.broadcasts.sender import BroadcastSender
from bot.broadcasts.worker import BroadcastWorker
from bot.config import settings
from bot.db.database import init_database, shutdown_database
from bot.utils.logger import logger


async def run_worker() -> None:
    await init_database()
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    queue = BroadcastQueue()
    sender = BroadcastSender(bot)
    worker = BroadcastWorker(queue=queue, sender=sender)
    scheduler = BroadcastScheduler(queue=queue)
    await worker.start()
    await scheduler.start()

    stop_event = asyncio.Event()

    def _handle_signal(*_):
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        logger.info("Broadcast worker is running")
        await stop_event.wait()
    finally:
        await scheduler.stop()
        await worker.stop()
        await shutdown_database()
        await bot.session.close()
        logger.info("Broadcast worker stopped gracefully")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
