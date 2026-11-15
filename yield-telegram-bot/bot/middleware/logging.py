from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

from bot.utils.logger import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        user_id = self._extract_user_id(event)

        logger.info(
            "Отримано апдейт",
            extra={
                "user_id": user_id,
                "update_id": event.update_id,
                "update_type": type(event).__name__,
            },
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
                exc_info=True,
            )
            raise

    def _extract_user_id(self, event: Update) -> str:
        try:
            if event.message and event.message.from_user:
                return str(event.message.from_user.id)
            elif event.callback_query and event.callback_query.from_user:
                return str(event.callback_query.from_user.id)
            elif event.inline_query and event.inline_query.from_user:
                return str(event.inline_query.from_user.id)
            elif event.chosen_inline_result and event.chosen_inline_result.from_user:
                return str(event.chosen_inline_result.from_user.id)
            elif event.shipping_query and event.shipping_query.from_user:
                return str(event.shipping_query.from_user.id)
            elif event.pre_checkout_query and event.pre_checkout_query.from_user:
                return str(event.pre_checkout_query.from_user.id)
            elif event.poll_answer and event.poll_answer.user:
                return str(event.poll_answer.user.id)
            elif event.chat_member and event.chat_member.from_user:
                return str(event.chat_member.from_user.id)
            elif event.chat_join_request and event.chat_join_request.from_user:
                return str(event.chat_join_request.from_user.id)
            else:
                return "unknown"
        except (AttributeError, TypeError) as e:
            logger.debug(f"Не вдалося витягти user_id з події {type(event).__name__}: {e}")
            return "unknown"
