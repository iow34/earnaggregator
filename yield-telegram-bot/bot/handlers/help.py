"""
Обробник команди /help.

Виконує:
- Показ довідки та прикладів використання
- Відправка з кнопками для швидкого доступу

Команда: /help
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply import main_menu
from bot.db.database import get_database_session
from bot.db.crud import add_user_query, get_or_create_user
from bot.content.help import load_help_text
from bot.utils.logger import logger
from bot.utils.metrics import BOT_UPDATES_TOTAL, BOT_HANDLER_DURATION_SECONDS
from bot.localization import localization

router = Router(name="help_handler")


@router.message(Command("help"))
async def help_handler(message: Message, state: FSMContext) -> None:
    """Обробник команди /help."""
    import time
    start_time = time.time()

    try:
        # Отримати мову зі стану
        data = await state.get_data()
        lang = data.get("lang", "ua")

        # Збереження запиту в БД
        async with get_database_session() as session:
            db_user = await get_or_create_user(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            await add_user_query(
                session=session,
                user_id=db_user.id,
                query_type="help",
            )

        # Завантажуємо текст довідки з файлу
        help_text = load_help_text(lang=lang)
        
        if not help_text:
            # Fallback якщо файл не знайдено
            help_text = (
                f"🆘 <b>{localization.get_text('section.help_title', lang)}</b>\n\n"
                f"{localization.get_error_text('general_error', lang)}"
            )
            logger.error(f"Не вдалося завантажити текст довідки для {lang}")

        await message.answer(
            text=help_text,
            reply_markup=main_menu(lang=lang),
            parse_mode="HTML"
        )

        # Метрики
        BOT_UPDATES_TOTAL.labels(update_type="command").inc()
        BOT_HANDLER_DURATION_SECONDS.labels(handler_name="help_handler").observe(time.time() - start_time)

        logger.info(
            "Показана довідка",
            extra={
                "user_id": message.from_user.id,
                "duration": time.time() - start_time,
                "lang": lang
            }
        )

    except Exception as e:
        logger.error(f"Помилка в help_handler: {e}", exc_info=True)
        data = await state.get_data()
        lang = data.get("lang", "ua")
        await message.answer(
            localization.get_error_text("general_error", lang)
        )


# Обробник для кнопки "Help" з клавіатури
@router.message(F.text == localization.get_menu_text("menu.main.help", "ua"))
@router.message(F.text == localization.get_menu_text("menu.main.help", "ru"))
@router.message(F.text == localization.get_menu_text("menu.main.help", "en"))
async def help_button_handler(message: Message, state: FSMContext) -> None:
    """Обробник натискання кнопки 'Help'."""
    await help_handler(message, state)
