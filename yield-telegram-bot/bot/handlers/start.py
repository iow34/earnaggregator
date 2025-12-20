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
    Обробник команди /start з deep link підтримкою.
    
    Обробляє deep link payload для трекінгу джерел входу:
    - Формат: /start ad_platform_campaignID
    - Валідує payload
    - Реєструє користувача через tracking API
    - Зберігає acquisition_source
    """
    loading_message = None
    loading_task = None
    
    # Determine initial language from Telegram for loading message (fallback to 'ua')
    tg_lang = message.from_user.language_code if message.from_user else None
    temp_lang = "ua"  # default
    logger.info(f"🌐 /start: Telegram language_code='{tg_lang}', determining temp_lang for loading message")

    if tg_lang:
        tg_lang_lower = tg_lang.lower()
        if tg_lang_lower.startswith("ru") or tg_lang_lower == "be":  # Russian or Belarusian
            temp_lang = "ru"
        elif tg_lang_lower.startswith("en"):
            temp_lang = "en"
        elif tg_lang_lower.startswith("uk") or tg_lang_lower == "ua":  # Ukrainian
            temp_lang = "ua"
        else:
            logger.warning(f"🌐 /start: Unknown language_code='{tg_lang}', using default 'ua'")
    else:
        logger.info("🌐 /start: No language_code from Telegram, using default 'ua'")

    logger.info(f"🌐 /start: Determined temp_lang='{temp_lang}' for loading message, user {message.from_user.id}")
    
    try:
        start_time = time.time()

        # Очистити стан на початку /start щоб уникнути конфліктів з попередніми станами
        await state.clear()

        # Створюємо задачу для показу індикатора завантаження через 1.5 секунди
        # Збільшено час, щоб зменшити ймовірність показу loading message
        async def show_loading_indicator():
            """Показати індикатор завантаження якщо процес займає >1.5 сек."""
            try:
                await asyncio.sleep(1.5)
                # Якщо ми досі тут - значить завантаження триває
                # Використовуємо temp_lang для повідомлення завантаження (з Telegram)
                loading_text = localization.get_text("loading.main_menu", temp_lang)
                logger.info(f"🌐 /start: Showing loading message in '{temp_lang}' (from Telegram): {loading_text}")
                # Використовуємо parse_mode=None щоб уникнути проблем з HTML на desktop
                return await message.answer(loading_text, parse_mode=None)
            except asyncio.CancelledError:
                # Завантаження завершилось швидше 1.5 секунди
                pass
            except Exception as e:
                # Якщо не вдалося відправити loading message - не критично
                logger.debug(f"Не вдалося відправити loading message: {e}")
                return None
        
        # Запускаємо індикатор в фоні
        loading_task = asyncio.create_task(show_loading_indicator())
        
        # DEEP LINK: Отримати payload якщо є
        payload = None
        if command and command.args:
            payload = command.args.strip()
            logger.info(f"📊 Deep link payload отримано: {payload} від user {message.from_user.id}")
        
        # Реєстрація користувача через tracking API (з deep link)
        # Не блокуємо /start на помилках tracking
        try:
            tracking_result = await tracking_client.register_user(
                telegram_id=message.from_user.id,
                payload=payload,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            if tracking_result:
                source = tracking_result.get('acquisition_source', 'organic')
                is_new = tracking_result.get('is_new_user', False)
                campaign_id = tracking_result.get('campaign_id')
                
                logger.info(
                    f"✅ Tracking реєстрація: user={message.from_user.id}, "
                    f"source={source}, new={is_new}, campaign={campaign_id}"
                )
            elif not tracking_client.is_tracking_enabled():
                logger.debug(f"📊 Tracking вимкнений для user {message.from_user.id}")
            else:
                logger.debug(f"📊 Tracking реєстрація пропущена для user {message.from_user.id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Помилка tracking реєстрації (не блокує /start): {e}")
            # Продовжуємо роботу навіть якщо tracking failed
        
        # Перевірка чи користувач вже існує (для визначення чи показувати привітання)
        is_existing_user = False
        async with get_database_session() as check_session:
            stmt_check = select(TelegramUser).where(TelegramUser.telegram_id == message.from_user.id)
            result_check = await check_session.execute(stmt_check)
            is_existing_user = result_check.scalar_one_or_none() is not None
        
        # Реєстрація користувача в БД (існуюча логіка)
        async with get_database_session() as session:
            # Використовуємо temp_lang як дефолтну мову для нового користувача
            user = await get_or_create_user(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language=temp_lang
            )
            lang = user.language
            
        # Save language to state
        await state.update_data(language=lang)

        # Логування
        log_message = "Користувач розпочав роботу з ботом"
        if payload:
            log_message += f" (deep link: {payload})"
        if not is_existing_user:
            log_message += " (новий користувач)"
        
        logger.info(
            log_message,
            extra={
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "deep_link_payload": payload,
                "language": lang,
                "is_new_user": not is_existing_user
            }
        )

        # Скасувати задачу індикатора ПЕРЕД відправкою повідомлень
        # щоб уникнути конфліктів на desktop версії Telegram
        loading_message = None
        if loading_task and not loading_task.done():
            # Задача ще не виконалась - скасовуємо її
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
        elif loading_task and loading_task.done():
            # Індикатор був показаний - отримуємо повідомлення та видаляємо його
            try:
                loading_message = await loading_task
            except Exception as e:
                logger.debug(f"Не вдалось отримати loading message: {e}")
                loading_message = None
        
        # Видаляємо loading message якщо він був відправлений
        if loading_message:
            try:
                await loading_message.delete()
                # Затримка після видалення loading message
                # щоб desktop версія встигла обробити видалення перед відправкою disclaimer
                await asyncio.sleep(0.3)
            except Exception as del_error:
                logger.debug(f"Не вдалось видалити індикатор завантаження: {del_error}")
                # Навіть якщо не вдалося видалити - додаємо затримку
                # щоб уникнути конфлікту з наступним повідомленням
                await asyncio.sleep(0.3)

        # Встановити постійну клавіатуру (ReplyKeyboard)
        # Для нових користувачів НЕ показуємо коротке привітання
        # (disclaimer буде показано нижче з клавіатурою)
        # Для існуючих користувачів також показуємо disclaimer (без welcome)
        # щоб уникнути конфлікту між reply та inline клавіатурами на desktop
        # if is_existing_user:
        #     await message.answer(
        #         localization.get_text("menu.main.welcome", lang),
        #         reply_markup=main_menu(lang)
        #     )

        # Показати disclaimer сторінку замість головного меню
        # Для нових користувачів встановлюємо клавіатуру через disclaimer
        await show_disclaimer_page(message, state, lang=lang, is_new_user=not is_existing_user)
        
        duration = time.time() - start_time
        logger.info(f"⏱️ /start виконано за {duration:.2f}с")

    except Exception as e:
        logger.error(f"Помилка в start_handler: {e}", exc_info=True)
        
        # Скасувати індикатор при помилці
        if loading_task and not loading_task.done():
            loading_task.cancel()
        
        await message.answer(
            localization.get_error_text("error.general", temp_lang)
        )


async def show_disclaimer_page(message: Message, state: FSMContext, lang: str = "en", is_new_user: bool = False) -> None:
    """
    Показати disclaimer сторінку з кнопкою "Go to main".

    Args:
        message: Повідомлення від користувача
        state: Стан FSM
        lang: Мова користувача
        is_new_user: Чи це новий користувач (для встановлення клавіатури)
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

        text = f"🔍 <b>{title}</b>\n"
        text += f"<i>{subtitle}</i>\n\n"
        text += f"{description}\n\n"
        text += f"{bullet1}\n{bullet2}\n{bullet3}\n\n"
        text += f"<b>{cta}</b>"

        # Імпортуємо клавіатури
        from bot.keyboards.navigation import disclaimer_keyboard
        from bot.keyboards.reply import main_menu

        # Відправляємо disclaimer з inline keyboard
        # Для нових користувачів reply keyboard буде встановлено після натискання "Go to main"
        # щоб уникнути проблем з desktop версією Telegram при швидкій послідовності повідомлень
        try:
            await message.answer(
                text=text,
                reply_markup=disclaimer_keyboard(lang),
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


@router.callback_query(F.data == "go_to_main")
async def go_to_main_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обробник кнопки "Go to main" з disclaimer сторінки.
    Переводить користувача на головну сторінку з фінансовими даними.
    """
    try:
        await callback.answer()

        user_data = await state.get_data()
        lang = user_data.get("lang", "en")

        # Показуємо індикатор завантаження
        loading_text = localization.get_text("loading.main_page", lang)
        loading_message = await callback.message.answer(loading_text)

        # Імпортуємо та викликаємо функцію головної сторінки
        from bot.handlers.main_menu import show_main_page

        # Створюємо об'єкт Message для сумісності з show_main_page
        # Використовуємо message з callback
        await show_main_page(callback.message, state, lang)

        # Reply keyboard встановлюється через show_main_page
        # Не відправляємо окреме повідомлення з емодзі

        # Видаляємо індикатор завантаження
        try:
            await loading_message.delete()
        except Exception:
            pass  # Повідомлення вже могло бути видалено

    except Exception as e:
        logger.error(f"Помилка в go_to_main_handler: {e}", exc_info=True)
        # Fallback
        lang = "en"  # fallback
        fallback_text = localization.get_text("error.general", lang)
        await callback.message.answer(text=fallback_text)
