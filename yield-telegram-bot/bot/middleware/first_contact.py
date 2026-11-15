from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.db.database import get_database_session
from bot.db.models import TelegramUser
from bot.utils.logger import logger
from sqlalchemy import select


class FirstContactMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:

        message: Message = event

        if not message.from_user:
            return await handler(event, data)

        if message.text and message.text.strip().startswith("/"):
            return await handler(event, data)

        user_id = message.from_user.id

        try:
            async with get_database_session() as session:
                stmt = select(TelegramUser).where(TelegramUser.telegram_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    await self._send_welcome_message(message)
                    logger.info(
                        f"📨 Відправлено привітальне повідомлення новому користувачу {user_id} "
                        f"(команда: {message.text[:20] if message.text else 'немає'})"
                    )

        except Exception as e:
            logger.error(f"❌ Помилка в FirstContactMiddleware: {e}", exc_info=True)

        return await handler(event, data)

    async def _send_welcome_message(self, message: Message) -> None:
        from bot.content.welcome import get_welcome_message
        from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

        tg_lang = message.from_user.language_code if message.from_user else "uk"
        lang = "en"  # default

        if tg_lang:
            if tg_lang.startswith("ru"):
                lang = "ru"
            elif tg_lang.startswith("uk"):
                lang = "ua"
            elif tg_lang.startswith("en"):
                lang = "en"

        try:
            welcome_text = get_welcome_message(lang)

            if not welcome_text or not welcome_text.strip():
                logger.warning(f"⚠️ Welcome message порожній для мови {lang}")
                return

            await message.answer(welcome_text, parse_mode="HTML")
        except (TelegramAPIError, TelegramBadRequest) as e:
            logger.error(
                f"❌ Telegram API помилка при відправці welcome message: {e}", exc_info=True
            )

        except FileNotFoundError as e:
            logger.error(f"❌ Файл welcome.txt не знайдено для мови {lang}: {e}")
        except Exception as e:
            logger.error(f"❌ Не вдалося відправити welcome message: {e}", exc_info=True)
