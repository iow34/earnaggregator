"""
Обробник команди /start.

Виконує:
- Привітання користувача
- Реєстрація в БД (якщо новий користувач)
- Показ інструкції
- Відправка головної клавіатури

Команда: /start
"""

import asyncio
import time
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy import select

from bot.keyboards.reply import main_menu
from bot.db.database import get_database_session
from bot.db.crud import get_or_create_user
from bot.db.models import TelegramUser
from bot.services.tracking_client import tracking_client
from bot.utils.logger import logger
from bot.localization import localization

router = Router(name="start_handler")


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, command: CommandObject = None) -> None:
    """
    Простий обробник команди /start.
    Показує disclaimer без middleware обробки.
    Middleware перенесені на /main для уникнення desktop помилок.
    """
    try:
        # Перевірка наявності користувача
        if not message.from_user:
            logger.error("❌ Критична помилка: повідомлення без from_user")
            await message.answer("❌ Error: Unable to identify user", parse_mode=None)
            return

        # Визначаємо мову з Telegram для disclaimer
        tg_lang = message.from_user.language_code
        lang = "ua"  # default
        if tg_lang:
            tg_lang_lower = tg_lang.lower()
            if tg_lang_lower.startswith("ru") or tg_lang_lower == "be":
                lang = "ru"
            elif tg_lang_lower.startswith("en"):
                lang = "en"
            elif tg_lang_lower.startswith("uk") or tg_lang_lower == "ua":
                lang = "ua"

        # Показуємо disclaimer одразу (як було раніше) з кнопкою для /start
        await show_disclaimer_page(message, state, lang=lang, is_new_user=True, from_start=True)

        # Логуємо простий /start
        logger.info(f"🚀 /start: Користувач {message.from_user.id} отримав disclaimer")

    except Exception as e:
        logger.error(f"❌ Помилка в start_handler: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred. Please try again.", parse_mode=None)
        except Exception as fallback_error:
            logger.error(f"❌ Критична помилка відправки fallback в /start: {fallback_error}")


async def show_disclaimer_page(message: Message, state: FSMContext, lang: str = "en", is_new_user: bool = False, from_start: bool = False) -> None:
    """
    Показати disclaimer сторінку з кнопкою "Go to main".

    Args:
        message: Повідомлення від користувача
        state: Стан FSM
        lang: Мова користувача
        is_new_user: Чи це новий користувач (для встановлення клавіатури)
        from_start: Чи викликано з команди /start (для вибору правильної кнопки)
    """
    try:
        # Імпортуємо функцію екранування HTML
        from bot.utils.formatters import _escape_html

        # Формуємо текст disclaimer з екрануванням HTML
        title = _escape_html(localization.get_text("disclaimer.title", lang))
        subtitle = _escape_html(localization.get_text("disclaimer.subtitle", lang))
        description = _escape_html(localization.get_text("disclaimer.description", lang))
        bullet1 = _escape_html(localization.get_text("disclaimer.bullet1", lang))
        bullet2 = _escape_html(localization.get_text("disclaimer.bullet2", lang))
        bullet3 = _escape_html(localization.get_text("disclaimer.bullet3", lang))
        cta = _escape_html(localization.get_text("disclaimer.cta", lang))

        # Перевірка на порожні тексти після екранування
        if not title or not description or not cta:
            logger.error(f"❌ Критична помилка: порожні тексти disclaimer для мови {lang}")
            raise ValueError("Empty disclaimer texts")

        text = f"🔍 <b>{title}</b>\n"
        text += f"<i>{subtitle}</i>\n\n"
        text += f"{description}\n\n"
        text += f"{bullet1}\n{bullet2}\n{bullet3}\n\n"
        text += f"<b>{cta}</b>"

        # Перевірка довжини повідомлення (Telegram ліміт ~4096 символів)
        if len(text) > 4000:
            logger.warning(f"⚠️ Disclaimer текст занадто довгий ({len(text)} символів), скорочуємо")
            text = text[:4000] + "..."

        # Створюємо клавіатуру залежно від того, звідки викликано
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from bot.keyboards.reply import main_menu

        if from_start:
            # Для /start використовуємо кнопку з callback_data="go_to_main_from_start"
            go_to_main_text = localization.get_text("nav.go_to_main", lang)
            start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=go_to_main_text, callback_data="go_to_main_from_start")]
            ])
            keyboard = start_keyboard
        else:
            # Для інших випадків використовуємо звичайну disclaimer клавіатуру
            from bot.keyboards.navigation import disclaimer_keyboard
            keyboard = disclaimer_keyboard(lang)

        # Відправляємо disclaimer з inline keyboard
        # Для нових користувачів reply keyboard буде встановлено після натискання "Go to main"
        # щоб уникнути проблем з desktop версією Telegram при швидкій послідовності повідомлень
        try:
            await message.answer(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки disclaimer: {send_error}", exc_info=True)
            # Fallback: спробувати відправити без HTML форматування
            try:
                # Видаляємо HTML теги для fallback
                fallback_text = text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                await message.answer(
                    text=fallback_text,
                    reply_markup=disclaimer_keyboard(lang),
                    parse_mode=None
                )
            except Exception as fallback_error:
                logger.error(f"❌ Помилка fallback відправки disclaimer: {fallback_error}")
                # Останній fallback - просто текст
                await message.answer(
                    text=localization.get_text("error.general", lang)
                )

        # Оновлюємо стан
        await state.update_data(current_page="disclaimer", lang=lang)

    except Exception as e:
        logger.error(f"Помилка в show_disclaimer_page: {e}", exc_info=True)
        # Fallback
        fallback_text = localization.get_text("error.general", lang)
        await message.answer(text=fallback_text)


@router.callback_query(F.data == "go_to_main_from_start")
async def go_to_main_from_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обробник кнопки "Go to main" з disclaimer сторінки.
    Виконує всю складну логіку: deep links, реєстрацію, показ головного меню.
    Middleware обробка відбувається тут (Logging, Tracking, FirstContact, Throttling).
    """
    loading_message = None
    loading_task = None
    
    try:
        await callback.answer()

        # Перевірка наявності користувача
        if not callback.from_user:
            logger.error("❌ Критична помилка: callback без from_user")
            await callback.message.answer("❌ Error: Unable to identify user", parse_mode=None)
            return

        start_time = time.time()

        # Очистити стан на початку щоб уникнути конфліктів з попередніми станами
        try:
            await state.clear()
        except Exception as state_error:
            logger.warning(f"⚠️ Не вдалося очистити FSM стан: {state_error}")

        # Determine initial language from Telegram for loading message (fallback to 'ua')
        tg_lang = callback.from_user.language_code
        temp_lang = "ua"  # default
        logger.info(f"🌐 /main (from start): Telegram language_code='{tg_lang}', determining temp_lang for loading message")

        if tg_lang:
            tg_lang_lower = tg_lang.lower()
            if tg_lang_lower.startswith("ru") or tg_lang_lower == "be":  # Russian or Belarusian
                temp_lang = "ru"
            elif tg_lang_lower.startswith("en"):
                temp_lang = "en"
            elif tg_lang_lower.startswith("uk") or tg_lang_lower == "ua":  # Ukrainian
                temp_lang = "ua"
            else:
                logger.warning(f"🌐 /main (from start): Unknown language_code='{tg_lang}', using default 'ua'")
        else:
            logger.info("🌐 /main (from start): No language_code from Telegram, using default 'ua'")

        logger.info(f"🌐 /main (from start): Determined temp_lang='{temp_lang}' for loading message, user {callback.from_user.id}")

        # Створюємо задачу для показу індикатора завантаження через 1.5 секунди
        async def show_loading_indicator():
            """Показати індикатор завантаження якщо процес займає >1.5 сек."""
            try:
                await asyncio.sleep(1.5)
                loading_text = localization.get_text("loading.main_menu", temp_lang)
                if not loading_text or not loading_text.strip():
                    logger.warning(f"⚠️ Loading message порожній для мови {temp_lang}")
                    return None
                logger.info(f"🌐 /main (from start): Showing loading message in '{temp_lang}'")
                return await callback.message.answer(loading_text, parse_mode=None)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Не вдалося відправити loading message: {e}")
                return None
        
        # Запускаємо індикатор в фоні
        loading_task = asyncio.create_task(show_loading_indicator())
        
        # DEEP LINK: Тут немає deep link, бо ми прийшли з /start
        # Але можна додати підтримку deep link через стан, якщо потрібно

        # Реєстрація користувача через tracking API
        try:
            tracking_result = await tracking_client.register_user(
                telegram_id=callback.from_user.id,
                payload=None,  # немає deep link
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name
            )
            
            if tracking_result:
                source = tracking_result.get('acquisition_source', 'organic')
                is_new = tracking_result.get('is_new_user', False)
                campaign_id = tracking_result.get('campaign_id')
                
                logger.info(
                    f"✅ Tracking реєстрація з /main: user={callback.from_user.id}, "
                    f"source={source}, new={is_new}, campaign={campaign_id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Помилка tracking реєстрації в /main: {e}")
        
        # Перевірка чи користувач вже існує
        is_existing_user = False
        try:
            async with get_database_session() as check_session:
                stmt_check = select(TelegramUser).where(TelegramUser.telegram_id == callback.from_user.id)
                result_check = await check_session.execute(stmt_check)
                is_existing_user = result_check.scalar_one_or_none() is not None
        except Exception as db_error:
            logger.error(f"❌ Помилка перевірки існування користувача в БД: {db_error}", exc_info=True)
            is_existing_user = False

        # Реєстрація користувача в БД
        try:
            async with get_database_session() as session:
                user = await get_or_create_user(
                    session=session,
                    telegram_id=callback.from_user.id,
                    username=callback.from_user.username,
                    first_name=callback.from_user.first_name,
                    last_name=callback.from_user.last_name,
                    language=temp_lang
                )
                lang = user.language
        except Exception as db_create_error:
            logger.error(f"❌ Помилка створення користувача в БД: {db_create_error}", exc_info=True)
            lang = temp_lang
            
        # Save language to state
        await state.update_data(language=lang)

        # Логування
        log_message = f"Користувач перейшов до головного меню з /start"
        if not is_existing_user:
            log_message += " (новий користувач)"
        
        logger.info(
            log_message,
            extra={
                "user_id": callback.from_user.id,
                "username": callback.from_user.username,
                "first_name": callback.from_user.first_name,
                "language": lang,
                "is_new_user": not is_existing_user
            }
        )

        # Скасувати loading task
        loading_message = None
        if loading_task and not loading_task.done():
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
        elif loading_task and loading_task.done():
            try:
                loading_message = await loading_task
            except Exception as e:
                logger.debug(f"Не вдалось отримати loading message: {e}")
                loading_message = None

        # Видаляємо loading message якщо він був відправлений
        if loading_message:
            try:
                await loading_message.delete()
                await asyncio.sleep(0.3)
            except Exception as del_error:
                logger.debug(f"Не вдалось видалити індикатор завантаження: {del_error}")
                await asyncio.sleep(0.3)

        # Показати головну сторінку замість disclaimer (бо disclaimer вже був показаний в /start)
        from bot.handlers.main_menu import show_main_page
        await show_main_page(callback.message, state, lang)

        # Встановлюємо reply keyboard після успішного показу головного меню
        await asyncio.sleep(0.5)
        try:
            await callback.message.answer(
                "📊",  # Емодзі для встановлення клавіатури
                reply_markup=main_menu(lang)
            )
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося встановити reply keyboard: {e}")
        
        duration = time.time() - start_time
        logger.info(f"⏱️ /main (from start) виконано за {duration:.2f}с")

    except Exception as e:
        logger.error(f"Помилка в go_to_main_from_start_handler: {e}", exc_info=True)
        
        # Скасувати індикатор при помилці
        if loading_task and not loading_task.done():
            loading_task.cancel()
        
        # Надіслати fallback повідомлення
        try:
            fallback_text = localization.get_error_text("error.general", "en")
            if not fallback_text or not fallback_text.strip():
                fallback_text = "❌ An error occurred. Please try again."
            await callback.message.answer(fallback_text, parse_mode=None)
        except Exception as fallback_error:
            logger.error(f"❌ Критична помилка відправки fallback в /main: {fallback_error}")


# Видалено: звичайний go_to_main handler більше не потрібен,
# оскільки show_disclaimer_page використовує умовну клавіатуру
