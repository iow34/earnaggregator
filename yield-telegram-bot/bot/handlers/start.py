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


def detect_user_language(message: Message) -> str:
    if not message.from_user or not hasattr(message.from_user, "language_code"):
        return "en"

    tg_lang = message.from_user.language_code
    if not tg_lang:
        return "en"

    if tg_lang.startswith("uk"):
        return "ua"
    elif tg_lang.startswith("ru"):
        return "ru"
    elif tg_lang.startswith("en"):
        return "en"
    else:
        return "en"


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, command: CommandObject = None) -> None:
    try:
        if not message.from_user:
            logger.error("❌ Критична помилка: повідомлення без from_user")
            await message.answer("❌ Error: Unable to identify user", parse_mode=None)
            return

        user_id = getattr(message.from_user, "id", None)
        if not user_id:
            logger.error("❌ Критична помилка: користувач без id")
            await message.answer("❌ Error: Invalid user data", parse_mode=None)
            return

        logger.info(f"👤 /start: користувач id={user_id}, має всі необхідні поля")

        try:
            await state.clear()
        except Exception as state_error:
            logger.warning(f"⚠️ Не вдалося очистити FSM стан: {state_error}")

        lang = detect_user_language(message)
        logger.info(
            f"🌐 /start: Detected language '{lang}' from Telegram, user_id={message.from_user.id}"
        )

        deep_link_param = None
        if command and command.args:
            deep_link_param = command.args.strip()
            logger.info(
                f"🔗 /start: Отриманий deep link параметр: '{deep_link_param}' для user_id={user_id}"
            )

            await state.update_data(deep_link_param=deep_link_param)
        else:
            logger.info(
                f"📱 /start: Deep link параметр не отримано (можливо Desktop client), user_id={user_id}"
            )
            await state.update_data(deferred_deep_link=True)

            await state.update_data(from_deep_link=True)

        await show_disclaimer_page(message, state, lang=lang, is_new_user=True, from_start=True)

        logger.info(f"🚀 /start: Користувач {message.from_user.id} отримав disclaimer")

    except Exception as e:
        logger.error(f"❌ Помилка в start_handler: {e}", exc_info=True)
        try:
            await message.answer("❌ An error occurred. Please try again.", parse_mode=None)
        except Exception as fallback_error:
            logger.error(f"❌ Критична помилка відправки fallback в /start: {fallback_error}")


async def show_disclaimer_page(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    is_new_user: bool = False,
    from_start: bool = False,
) -> None:
    try:
        from bot.utils.formatters import _escape_html

        title = _escape_html(localization.get_text("disclaimer.title", lang))
        subtitle = _escape_html(localization.get_text("disclaimer.subtitle", lang))
        description = _escape_html(localization.get_text("disclaimer.description", lang))
        bullet1 = _escape_html(localization.get_text("disclaimer.bullet1", lang))
        bullet2 = _escape_html(localization.get_text("disclaimer.bullet2", lang))
        bullet3 = _escape_html(localization.get_text("disclaimer.bullet3", lang))
        cta = _escape_html(localization.get_text("disclaimer.cta", lang))

        if not title or not description or not cta:
            logger.error(f"❌ Критична помилка: порожні тексти disclaimer для мови {lang}")
            raise ValueError("Empty disclaimer texts")

        text = f"🔍 <b>{title}</b>\n"
        text += f"<i>{subtitle}</i>\n\n"
        text += f"{description}\n\n"
        text += f"{bullet1}\n{bullet2}\n{bullet3}\n\n"
        text += f"<b>{cta}</b>"

        if len(text) > 4000:
            logger.warning(f"⚠️ Disclaimer текст занадто довгий ({len(text)} символів), скорочуємо")
            text = text[:4000] + "..."

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from bot.keyboards.reply import main_menu
        from bot.keyboards.navigation import disclaimer_keyboard

        if from_start:
            go_to_main_text = localization.get_text("nav.go_to_main", lang)
            start_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=go_to_main_text, callback_data="go_to_main_from_start"
                        )
                    ]
                ]
            )
            keyboard = start_keyboard
        else:
            keyboard = disclaimer_keyboard(lang)

        success = False
        try:
            await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
            success = True
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки disclaimer: {send_error}", exc_info=True)

            try:
                fallback_text = (
                    text.replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<i>", "")
                    .replace("</i>", "")
                )
                await message.answer(text=fallback_text, reply_markup=keyboard, parse_mode=None)
                success = True
            except Exception as fallback_error:
                logger.error(f"❌ Помилка fallback відправки disclaimer: {fallback_error}")

                try:
                    await message.answer(
                        text=localization.get_text("error.general", lang), parse_mode=None
                    )
                    success = True
                except Exception as final_error:
                    logger.error(
                        f"❌ Критична помилка: не вдалося відправити жодне повідомлення: {final_error}"
                    )

        if success:
            await state.update_data(current_page="disclaimer", lang=lang)

    except Exception as e:
        logger.error(f"Помилка в show_disclaimer_page: {e}", exc_info=True)
        # Fallback
        fallback_text = localization.get_text("error.general", lang)
        await message.answer(text=fallback_text)


@router.callback_query(F.data == "go_to_main_from_start")
async def go_to_main_from_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    loading_message = None
    loading_task = None

    try:
        logger.info(
            f"🔘 Початок обробки кнопки 'Go to main' для користувача {callback.from_user.id if callback.from_user else 'unknown'}"
        )

        current_state = await state.get_state()
        if current_state == "processing_main":
            logger.warning(
                f"⚠️ Дублювання обробки для користувача {callback.from_user.id} - ігноруємо"
            )
            await callback.answer("Обробка вже виконується...", show_alert=False)
            return

        await state.set_state("processing_main")
        await callback.answer()

        if not callback.from_user:
            logger.error("❌ Критична помилка: callback без from_user")
            await callback.message.answer("❌ Error: Unable to identify user", parse_mode=None)
            return

        user_id = getattr(callback.from_user, "id", None)
        if not user_id:
            logger.error("❌ Критична помилка: callback користувач без id")
            await callback.message.answer("❌ Error: Invalid user data", parse_mode=None)
            return

        logger.info(f"👤 Go to main: користувач id={user_id}, має всі необхідні поля")

        start_time = time.time()

        try:
            await state.clear()
        except Exception as state_error:
            logger.warning(f"⚠️ Не вдалося очистити FSM стан: {state_error}")

        temp_lang = detect_user_language(callback.message)
        logger.info(
            f"🌐 /main (from start): Detected language '{temp_lang}' from Telegram for loading, user_id={callback.from_user.id}"
        )

        logger.info(
            f"🌐 /main (from start): Determined temp_lang='{temp_lang}' for loading message, user {callback.from_user.id}"
        )

        async def show_loading_indicator():
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

        loading_task = asyncio.create_task(show_loading_indicator())

        deep_link_param = None

        state_data = await state.get_data()
        if state_data.get("deep_link_param"):
            deep_link_param = state_data["deep_link_param"]
            logger.info(
                f"🔗 /main: Знайдений збережений deep link параметр: '{deep_link_param}' для user_id={user_id}"
            )
        elif state_data.get("deferred_deep_link"):
            logger.info(
                f"📱 /main: Deferred deep link обробка для Desktop client, user_id={user_id}"
            )

        if deep_link_param:
            logger.info(
                f"🎯 /main: Обробляємо deep link: '{deep_link_param}' для user_id={user_id}"
            )

        try:
            user_id = callback.from_user.id
            username = getattr(callback.from_user, "username", None)
            first_name = getattr(callback.from_user, "first_name", None)
            last_name = getattr(callback.from_user, "last_name", None)

            logger.info(
                f"👤 Дані користувача для tracking: id={user_id}, username={username}, first_name={first_name}, last_name={last_name}"
            )

            tracking_result = await tracking_client.register_user(
                telegram_id=user_id,
                payload=deep_link_param,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )

            if tracking_result:
                source = tracking_result.get("acquisition_source", "organic")
                is_new = tracking_result.get("is_new_user", False)
                campaign_id = tracking_result.get("campaign_id")

                logger.info(
                    f"✅ Tracking реєстрація з /main: user={callback.from_user.id}, "
                    f"source={source}, new={is_new}, campaign={campaign_id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Помилка tracking реєстрації в /main: {e}")

        is_existing_user = False
        try:
            user_id = callback.from_user.id
            username = getattr(callback.from_user, "username", None)
            first_name = getattr(callback.from_user, "first_name", None)
            last_name = getattr(callback.from_user, "last_name", None)

            logger.info(
                f"🗄️ Реєстрація користувача в БД: id={user_id}, username={username}, first_name={first_name}, last_name={last_name}, lang={temp_lang}"
            )

            async with get_database_session() as session:
                user = await get_or_create_user(
                    session=session,
                    telegram_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language=temp_lang,
                )
                lang = user.language
                logger.info(f"✅ Користувач зареєстрований в БД: id={user_id}, final_lang={lang}")

                is_existing_user = (
                    hasattr(user, "created_at")
                    and hasattr(user, "updated_at")
                    and user.created_at != user.updated_at
                )
        except Exception as db_create_error:
            logger.error(f"❌ Помилка створення користувача в БД: {db_create_error}", exc_info=True)
            lang = temp_lang
            is_existing_user = False

        # Save language to state
        await state.update_data(language=lang)

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
                "is_new_user": not is_existing_user,
            },
        )

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

        if loading_message:
            try:
                await loading_message.delete()
                await asyncio.sleep(0.5)
            except Exception as del_error:
                logger.debug(f"Не вдалось видалити індикатор завантаження: {del_error}")
                await asyncio.sleep(0.5)

        await asyncio.sleep(0.3)

        logger.info(f"🏠 Викликаємо show_main_page для користувача {callback.from_user.id}")

        await asyncio.sleep(0.2)

        from bot.handlers.main_menu import show_main_page

        await show_main_page(callback.message, state, lang)
        logger.info(f"✅ show_main_page успішно виконано для користувача {callback.from_user.id}")

        from bot.keyboards.reply import main_menu

        await callback.message.answer(
            text=localization.get_text("menu.main.placeholder", lang), reply_markup=main_menu(lang)
        )
        logger.info(f"✅ Reply keyboard встановлено для користувача {callback.from_user.id}")

        await state.set_state(None)

        duration = time.time() - start_time
        logger.info(f"⏱️ /main (from start) виконано за {duration:.2f}с")

    except Exception as e:
        logger.error(
            f"❌ ПОМИЛКА в go_to_main_from_start_handler для користувача {callback.from_user.id if callback.from_user else 'unknown'}: {e}",
            exc_info=True,
        )

        try:
            await state.set_state(None)
        except:
            pass

        if loading_task and not loading_task.done():
            loading_task.cancel()

        try:
            logger.info(
                f"📤 Надсилаємо fallback повідомлення для користувача {callback.from_user.id if callback.from_user else 'unknown'}"
            )
            fallback_text = localization.get_error_text("error.general", "en")
            if not fallback_text or not fallback_text.strip():
                fallback_text = "❌ An error occurred. Please try again."
            await callback.message.answer(fallback_text, parse_mode=None)
            logger.info(f"✅ Fallback повідомлення надіслано успішно")
        except Exception as fallback_error:
            logger.error(
                f"❌ Критична помилка відправки fallback в /main для користувача {callback.from_user.id if callback.from_user else 'unknown'}: {fallback_error}"
            )
