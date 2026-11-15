import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.utils.logger import logger
from bot.db.database import db_manager
from bot.db.crud import update_user_language, get_or_create_user
from bot.localization import localization

router = Router(name="language_handler")


class LanguageSelection(StatesGroup):
    waiting_for_language = State()


def get_language_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    # Get translated language names or use hardcoded ones if preference is strictly local here
    # Using hardcoded for specific language names in their own script usually makes sense

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🇺🇦 Українська {'✅' if current_lang == 'ua' else ''}",
                callback_data="lang_ua",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🇷🇺 Русский {'✅' if current_lang == 'ru' else ''}",
                callback_data="lang_ru",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🇬🇧 English {'✅' if current_lang == 'en' else ''}",
                callback_data="lang_en",
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("language.back_to_main", current_lang),
                callback_data="language_back_to_main",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(
    F.text.in_(
        [
            "🌐 Language",  # English
            "🌐 Мова",  # Ukrainian
            "🌐 Язык",  # Russian
        ]
    )
)
async def language_handler(message: Message, state: FSMContext) -> None:
    try:
        user_id = message.from_user.id

        # Get current language from DB to mark selected
        async with db_manager.get_session() as session:
            user = await get_or_create_user(
                session,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            current_lang = user.language

        # Save current language to state if not set
        await state.update_data(language=current_lang)

        text = localization.get_text("language.select_prompt", current_lang)

        await message.answer(text=text, reply_markup=get_language_keyboard(current_lang))
        await state.set_state(LanguageSelection.waiting_for_language)

    except Exception as e:
        logger.error(f"Помилка в language_handler: {e}", exc_info=True)
        await message.answer(
            localization.get_error_text("error.general", "ua")  # Fallback to UA if unknown
        )


@router.message(Command("language"))
async def language_command_handler(message: Message, state: FSMContext) -> None:
    try:
        user_id = message.from_user.id

        # Get current language from DB to mark selected
        async with db_manager.get_session() as session:
            user = await get_or_create_user(
                session,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            current_lang = user.language

        # Save current language to state if not set
        await state.update_data(language=current_lang)

        text = localization.get_text("language.select_prompt", current_lang)

        await message.answer(text=text, reply_markup=get_language_keyboard(current_lang))
        await state.set_state(LanguageSelection.waiting_for_language)

    except Exception as e:
        logger.error(f"Помилка в language_command_handler: {e}", exc_info=True)
        await message.answer(
            localization.get_error_text("error.general", "ua")  # Fallback to UA if unknown
        )


@router.callback_query(F.data.startswith("lang_"))
async def language_callback(callback: CallbackQuery, state: FSMContext):
    try:
        lang_code = callback.data.split("_")[1]
        if lang_code not in ["ua", "ru", "en"]:
            await callback.answer("Invalid language", show_alert=True)
            return

        user_id = callback.from_user.id

        # Get old language before updating
        user_data = await state.get_data()
        old_lang = user_data.get("language") or user_data.get("lang") or "ua"

        logger.info(f"🌐 Користувач {user_id}: зміна мови {old_lang} → {lang_code}")

        # Update in DB
        async with db_manager.get_session() as session:
            await update_user_language(session, telegram_id=user_id, language=lang_code)

        await state.update_data(language=lang_code, lang=lang_code)

        from bot.utils.language_cache import language_cache

        await language_cache.handle_language_change(
            user_id=user_id, old_lang=old_lang, new_lang=lang_code, key_prefixes=["main_menu"]
        )

        # Confirm to user
        success_text = localization.get_text(
            "success.language_selected", lang_code, language=lang_code.upper()
        )

        # Update the message to show new selection state
        await callback.message.edit_text(
            text=localization.get_text("language.select_prompt", lang_code),
            reply_markup=get_language_keyboard(lang_code),
        )

        await callback.answer(localization.get_text("language.changed", lang_code))

        # Send confirmation message
        await callback.message.answer(success_text)

        # Re-send main menu to update button texts
        from bot.keyboards.reply import main_menu

        await callback.message.answer(
            localization.get_text("menu.main.placeholder", lang_code),
            reply_markup=main_menu(lang_code),
        )

    except Exception as e:
        logger.error(f"Помилка в language_callback: {e}", exc_info=True)
        await callback.answer("Error changing language", show_alert=True)


@router.callback_query(F.data == "language_back_to_main")
async def language_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        lang = data.get("language") or data.get("lang") or "ua"
        await state.clear()
        await callback.answer()

        loading_task = None

        async def show_loading_indicator():
            try:
                await asyncio.sleep(1.0)

                loading_text = localization.get_text("loading.main_menu", lang)
                logger.info(
                    f"🌐 language_back_to_main: Showing loading message in '{lang}': {loading_text}"
                )
                return await callback.message.answer(loading_text)
            except asyncio.CancelledError:
                pass

        loading_task = asyncio.create_task(show_loading_indicator())

        from bot.keyboards.reply import main_menu
        from bot.handlers.main_menu import show_main_page

        try:
            await callback.message.answer(
                localization.get_text("menu.main.placeholder", lang),
                reply_markup=main_menu(lang),
            )
            await show_main_page(callback.message, state, lang=lang)
        finally:
            if loading_task and not loading_task.done():
                loading_task.cancel()
                try:
                    await loading_task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"Помилка в language_back_to_main: {e}", exc_info=True)
        await callback.answer("Error", show_alert=True)
