"""
Утиліта для показу індикатора завантаження.

Автоматично показує "🔄 Завантаження..." якщо операція займає >1 сек.
"""

import asyncio
from typing import Optional
from aiogram.types import Message
from bot.utils.logger import logger


class LoadingIndicator:
    """Контекстний менеджер для автоматичного показу індикатора завантаження."""
    
    def __init__(self, message: Message, text: str = "🔄 Завантаження, зачекайте..."):
        """
        Ініціалізувати індикатор завантаження.
        
        Args:
            message: Повідомлення для відправки індикатора
            text: Текст індикатора завантаження
        """
        self.message = message
        self.text = text
        self.loading_task: Optional[asyncio.Task] = None
        self.loading_message: Optional[Message] = None
    
    async def __aenter__(self):
        """Запустити таймер для показу індикатора."""
        async def show_loading():
            """Показати індикатор через 1 секунду."""
            try:
                await asyncio.sleep(1.0)
                # Якщо дійшли до цього моменту - показуємо індикатор
                return await self.message.answer(self.text)
            except asyncio.CancelledError:
                # Операція завершилась швидко - нічого не робимо
                pass
        
        self.loading_task = asyncio.create_task(show_loading())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Приховати індикатор після завершення операції."""
        try:
            if self.loading_task and not self.loading_task.done():
                # Операція завершилась швидше 1 сек - скасовуємо показ індикатора
                self.loading_task.cancel()
                try:
                    await self.loading_task
                except asyncio.CancelledError:
                    pass
            elif self.loading_task and self.loading_task.done():
                # Індикатор був показаний - видаляємо його
                try:
                    self.loading_message = await self.loading_task
                    if self.loading_message:
                        await self.loading_message.delete()
                except Exception as del_error:
                    logger.debug(f"Не вдалось видалити індикатор: {del_error}")
        except Exception as e:
            logger.debug(f"Помилка в __aexit__ LoadingIndicator: {e}")
        
        # Не suppressing exception, просто очищаємо ресурси
        return False


async def with_loading_indicator(message: Message, coro, text: str = "🔄 Завантаження, зачекайте..."):
    """
    Виконати корутину з автоматичним індикатором завантаження.
    
    Args:
        message: Повідомлення для відправки індикатора
        coro: Корутина для виконання
        text: Текст індикатора
        
    Returns:
        Результат виконання корутини
    """
    async with LoadingIndicator(message, text):
        return await coro

