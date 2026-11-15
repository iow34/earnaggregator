import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions,
)
from aiogram.fsm.context import FSMContext

from bot.db.database import get_database_session
from bot.db.crud import add_user_query, get_or_create_user
from bot.content.recommendations import (
    load_recommendation,
    get_recommendations_menu,
)
from bot.utils.logger import logger
from bot.utils.metrics import BOT_UPDATES_TOTAL, BOT_ERRORS_TOTAL, BOT_HANDLER_DURATION_SECONDS
from bot.localization import localization

router = Router(name="recommendations_handler")


def create_recommendations_menu_keyboard(lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_recommendation_detail_keyboard(rec_id: str, lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back_to_list", lang),
                callback_data="back_to_recommendations",
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def show_recommendations_menu(message: Message, lang: str = "ua") -> None:
    try:
        recommendations = get_recommendations_menu(lang)

        text = f"🎯 <b>{localization.get_text('section.recommendations_title', lang)}</b>\n\n"
        text += f"📚 <b>{localization.get_text('section.available_recommendations', lang)}:</b>\n\n"

        def get_rec_number(rec_id: str) -> int:
            return int(rec_id.replace("rec", ""))

        sorted_rec_ids = sorted(recommendations.keys(), key=get_rec_number)

        for rec_id in sorted_rec_ids:
            metadata = recommendations[rec_id]

            title_data = metadata.get("title", {})
            if isinstance(title_data, dict):
                title = title_data.get(
                    lang,
                    title_data.get("ua", localization.get_text("section.recommendation", lang)),
                )
            else:
                title = title_data

            rec_number = rec_id.replace("rec", "")

            text += f"/rec{rec_number} - {title}\n"

        text += f"\n💡 <i>{localization.get_text('messages.click_for_details', lang)}</i>"

        keyboard = create_recommendations_menu_keyboard(lang)

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        logger.info("Показано меню рекомендацій", extra={"user_id": message.from_user.id})

    except Exception as e:
        logger.error(f"Помилка в show_recommendations_menu: {e}", exc_info=True)
        raise


async def show_recommendation_detail(message: Message, rec_id: str, lang: str = "ua") -> None:
    try:
        content = load_recommendation(rec_id, lang)

        if not content:
            await message.answer(localization.get_error_text("error.data_not_found", lang))
            return

        keyboard = create_recommendation_detail_keyboard(rec_id, lang)

        await message.answer(
            text=content,
            reply_markup=keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        logger.info(
            f"Показано рекомендацію {rec_id}",
            extra={"user_id": message.from_user.id, "rec_id": rec_id},
        )

    except Exception as e:
        logger.error(f"Помилка в show_recommendation_detail: {e}", exc_info=True)
        await message.answer(localization.get_error_text("error.general", lang))


async def _get_user_lang(
    user_id: int, username: str = None, first_name: str = None, last_name: str = None
) -> str:
    """Helper to get user language from DB."""
    async with get_database_session() as session:
        db_user = await get_or_create_user(
            session=session,
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        return db_user.language or "ua"


@router.message(Command("recommendations"))
async def recommendations_command_handler(message: Message, state: FSMContext) -> None:
    start_time = time.time()

    try:
        lang = await _get_user_lang(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )

        # Update state
        await state.update_data(lang=lang)

        async with get_database_session() as session:
            user = await get_or_create_user(
                session,
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )
            await add_user_query(
                session=session,
                user_id=user.id,
                query_type="recommendations",
            )

        await show_recommendations_menu(message, lang=lang)

        BOT_UPDATES_TOTAL.labels(update_type="command").inc()
        BOT_HANDLER_DURATION_SECONDS.labels(handler_name="recommendations_command").observe(
            time.time() - start_time
        )

    except Exception as e:
        BOT_ERRORS_TOTAL.labels(
            error_type="handler_error", handler_name="recommendations_command"
        ).inc()
        logger.error(f"Помилка в recommendations_command_handler: {e}", exc_info=True)
        # Try to get lang from state if possible, else default
        data = await state.get_data()
        lang = data.get("lang", "ua")
        await message.answer(localization.get_error_text("error.general", lang))


@router.message(
    F.text.in_(
        [
            "🎯 Recommendations",  # English
            "🎯 Рекомендації",  # Ukrainian
            "🎯 Рекомендации",  # Russian
        ]
    )
)
async def recommendations_button_handler(message: Message, state: FSMContext) -> None:
    await recommendations_command_handler(message, state)


async def _handle_rec_command(message: Message, rec_id: str, state: FSMContext):
    lang = await _get_user_lang(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
    )
    await state.update_data(lang=lang)
    await show_recommendation_detail(message, rec_id, lang=lang)


@router.message(Command("rec1"))
async def rec1_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec1", state)


@router.message(Command("rec2"))
async def rec2_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec2", state)


@router.message(Command("rec3"))
async def rec3_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec3", state)


@router.message(Command("rec4"))
async def rec4_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec4", state)


@router.message(Command("rec5"))
async def rec5_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec5", state)


@router.message(Command("rec6"))
async def rec6_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec6", state)


@router.message(Command("rec7"))
async def rec7_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec7", state)


@router.message(Command("rec8"))
async def rec8_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec8", state)


@router.message(Command("rec9"))
async def rec9_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec9", state)


@router.message(Command("rec10"))
async def rec10_handler(message: Message, state: FSMContext) -> None:
    await _handle_rec_command(message, "rec10", state)


@router.callback_query(F.data == "back_to_recommendations")
async def back_to_recommendations_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        recommendations = get_recommendations_menu(lang=lang)

        text = f"🎯 <b>{localization.get_text('section.recommendations_title', lang)}</b>\n\n"
        text += f"📚 <b>{localization.get_text('section.available_recommendations', lang)}:</b>\n\n"

        def get_rec_number(rec_id: str) -> int:
            return int(rec_id.replace("rec", ""))

        sorted_rec_ids = sorted(recommendations.keys(), key=get_rec_number)

        for rec_id in sorted_rec_ids:
            metadata = recommendations[rec_id]

            title_data = metadata.get("title", {})
            if isinstance(title_data, dict):
                title = title_data.get(
                    lang,
                    title_data.get("ua", localization.get_text("section.recommendation", lang)),
                )
            else:
                title = title_data
            rec_number = rec_id.replace("rec", "")
            text += f"/rec{rec_number} - {title}\n"

        text += f"\n💡 <i>{localization.get_text('messages.click_for_details', lang)}</i>"

        keyboard = create_recommendations_menu_keyboard(lang)

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

        await callback.answer()

        logger.info("Повернення до меню рекомендацій", extra={"user_id": callback.from_user.id})

    except Exception as e:
        logger.error(f"Помилка в back_to_recommendations_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)
