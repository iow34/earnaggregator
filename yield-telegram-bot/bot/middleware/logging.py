"""
Middleware для логування апдейтів та помилок бота.
"""

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

from bot.utils.logger import logger


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логування всіх апдейтів."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        user_id = getattr(event, 'from_user', None)
        user_id = user_id.id if user_id else "unknown"

        logger.info(
            "Отримано апдейт",
            extra={
                "user_id": user_id,
                "update_id": event.update_id,
                "update_type": type(event).__name__,
            }
        )

        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                "Помилка в обробці апдейту",
                extra={
                    "user_id": user_id,
                    "update_id": event.update_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise
