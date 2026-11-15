import asyncio
from typing import Optional
from aiogram.types import Message
from bot.utils.logger import logger


class LoadingIndicator:
    def __init__(self, message: Message, text: str = "🔄 Завантаження, зачекайте..."):
        self.message = message
        self.text = text
        self.loading_task: Optional[asyncio.Task] = None
        self.loading_message: Optional[Message] = None

    async def __aenter__(self):
        async def show_loading():
            try:
                await asyncio.sleep(1.0)

                return await self.message.answer(self.text)
            except asyncio.CancelledError:
                pass

        self.loading_task = asyncio.create_task(show_loading())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.loading_task and not self.loading_task.done():
                self.loading_task.cancel()
                try:
                    await self.loading_task
                except asyncio.CancelledError:
                    pass
            elif self.loading_task and self.loading_task.done():
                try:
                    self.loading_message = await self.loading_task
                    if self.loading_message:
                        await self.loading_message.delete()
                except Exception as del_error:
                    logger.debug(f"Не вдалось видалити індикатор: {del_error}")
        except Exception as e:
            logger.debug(f"Помилка в __aexit__ LoadingIndicator: {e}")

        return False


async def with_loading_indicator(
    message: Message, coro, text: str = "🔄 Завантаження, зачекайте..."
):
    async with LoadingIndicator(message, text):
        return await coro
