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

        # Створюємо задачу для показу індикатора завантаження через 1 секунду
        async def show_loading_indicator():
            """Показати індикатор завантаження якщо процес займає >1 сек."""
            try:
                await asyncio.sleep(1.0)
                # Якщо ми досі тут - значить завантаження триває
                # Використовуємо temp_lang для повідомлення завантаження (з Telegram)
                loading_text = localization.get_text("loading.main_menu", temp_lang)
                logger.info(f"🌐 /start: Showing loading message in '{temp_lang}' (from Telegram): {loading_text}")
                return await message.answer(loading_text)
            except asyncio.CancelledError:
                # Завантаження завершилось швидше 1 секунди
                pass
        
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

        # Встановити постійну клавіатуру (ReplyKeyboard)
        # Для нових користувачів НЕ показуємо коротке привітання
        # (вони вже отримали детальне welcome message з middleware)
        if is_existing_user:
            await message.answer(
                localization.get_text("menu.main.welcome", lang),
                reply_markup=main_menu(lang)
            )
        else:
            # Для нових користувачів просто встановлюємо клавіатуру без тексту
            # або показуємо більш нейтральне повідомлення
            await message.answer(
                "📊",  # Просто емодзі щоб встановити клавіатуру
                reply_markup=main_menu(lang)
            )

        # Показати disclaimer сторінку замість головного меню
        await show_disclaimer_page(message, state, lang=lang)
        
        # Скасувати задачу індикатора якщо вона ще не виконалась
        if loading_task and not loading_task.done():
            loading_task.cancel()
            try:
                await loading_task
            except asyncio.CancelledError:
                pass
        elif loading_task and loading_task.done():
            # Індикатор був показаний - видаляємо його
            try:
                loading_message = await loading_task
                if loading_message:
                    await loading_message.delete()
            except Exception as del_error:
                logger.debug(f"Не вдалось видалити індикатор завантаження: {del_error}")
        
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


async def show_disclaimer_page(message: Message, state: FSMContext, lang: str = "en") -> None:
    """
    Показати disclaimer сторінку з кнопкою "Go to main".

    Args:
        message: Повідомлення від користувача
        state: Стан FSM
        lang: Мова користувача
    """
    try:
        # Формуємо текст disclaimer
        title = localization.get_text("disclaimer.title", lang)
        subtitle = localization.get_text("disclaimer.subtitle", lang)
        description = localization.get_text("disclaimer.description", lang)
        bullet1 = localization.get_text("disclaimer.bullet1", lang)
        bullet2 = localization.get_text("disclaimer.bullet2", lang)
        bullet3 = localization.get_text("disclaimer.bullet3", lang)
        cta = localization.get_text("disclaimer.cta", lang)

        text = f"🔍 <b>{title}</b>\n"
        text += f"<i>{subtitle}</i>\n\n"
        text += f"{description}\n\n"
        text += f"{bullet1}\n{bullet2}\n{bullet3}\n\n"
        text += f"<b>{cta}</b>"

        # Імпортуємо клавіатуру
        from bot.keyboards.navigation import disclaimer_keyboard

        # Відправляємо повідомлення з клавіатурою
        await message.answer(
            text=text,
            reply_markup=disclaimer_keyboard(lang),
            parse_mode="HTML"
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
