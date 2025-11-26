"""
First Contact Middleware - показує привітальне повідомлення новим користувачам.

Це middleware спрацьовує один раз для нового користувача при першому повідомленні,
включно з командою /start.
"""

from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.db.database import get_database_session
from bot.db.models import TelegramUser
from bot.utils.logger import logger
from sqlalchemy import select


class FirstContactMiddleware(BaseMiddleware):
    """
    Middleware для відправки привітального повідомлення новим користувачам.
    
    Логіка:
    1. Перевіряє чи користувач існує в БД ПЕРЕД обробкою повідомлення
    2. Якщо не існує - показує welcome message
    3. Потім передає обробку далі (handler створить користувача)
    4. Працює для всіх повідомлень, включно з командами
    
    ВАЖЛИВО: Цей middleware реєструється на рівні dp.message.middleware(),
    тому event це Message, а не Update.
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обробник middleware.
        
        Args:
            handler: Наступний handler в ланцюгу
            event: Message від Telegram (не Update!)
            data: Контекст даних
        
        Returns:
            Результат виконання handler
        """
        # event це вже Message об'єкт
        message: Message = event
        
        # Перевірка чи є from_user (на всякий випадок)
        if not message.from_user:
            return await handler(event, data)
        
        user_id = message.from_user.id
        
        try:
            # Перевіряємо чи користувач вже існує в БД
            async with get_database_session() as session:
                stmt = select(TelegramUser).where(TelegramUser.telegram_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                
                # Якщо користувача немає - це перший контакт
                # Відправляємо welcome message для будь-якого першого повідомлення
                if user is None:
                    await self._send_welcome_message(message)
                    logger.info(
                        f"📨 Відправлено привітальне повідомлення новому користувачу {user_id} "
                        f"(команда: {message.text[:20] if message.text else 'немає'})"
                    )
        
        except Exception as e:
            logger.error(f"❌ Помилка в FirstContactMiddleware: {e}", exc_info=True)
            # Продовжуємо виконання навіть при помилці
        
        # Викликаємо наступний handler
        return await handler(event, data)
    
    async def _send_welcome_message(self, message: Message) -> None:
        """
        Відправити привітальне повідомлення.
        
        Args:
            message: Вхідне повідомлення від користувача
        """
        from bot.content.welcome import get_welcome_message
        
        # Визначаємо мову користувача з Telegram
        tg_lang = message.from_user.language_code if message.from_user else "uk"
        lang = "en"  # default
        
        if tg_lang:
            if tg_lang.startswith("ru"):
                lang = "ru"
            elif tg_lang.startswith("uk"):
                lang = "ua"
            elif tg_lang.startswith("en"):
                lang = "en"
        
        # Отримуємо та відправляємо привітальне повідомлення
        welcome_text = get_welcome_message(lang)
        
        try:
            await message.answer(
                welcome_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"❌ Не вдалося відправити welcome message: {e}")

