from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from typing import List, Dict

from bot.services.api_client import APIClient
from bot.keyboards.filters import (
    filter_keyboard,
    flexible_products_keyboard,
    locked_products_keyboard,
    all_products_keyboard,
)
from bot.keyboards.navigation import back_button_keyboard
from bot.utils.pagination import Paginator
from bot.utils.formatters import (
    format_flexible_products_table,
    format_locked_products_table,
    format_all_products_table,
)
from bot.utils.logger import logger
from bot.services.filter_state import FilterStateManager
from bot.utils.loading_indicator import LoadingIndicator
from bot.localization import localization

router = Router(name="filtered_products_handler")


@router.callback_query(F.data == "type_flexible")
async def show_flexible_products_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await callback.answer(localization.get_text("messages.loading_products", lang))

        try:
            loading_msg = await callback.message.answer(
                localization.get_text("messages.loading_products", lang)
            )
        except Exception as e:
            logger.error(f"Помилка відправки loading message: {e}")
            loading_msg = callback.message

        try:
            await _display_flexible_products(
                loading_msg, state, page=1, is_callback=True, lang=lang
            )

            if loading_msg.message_id != callback.message.message_id:
                try:
                    await callback.message.delete()
                except:
                    pass
        except Exception as e:
            logger.error(f"Помилка в _display_flexible_products: {e}", exc_info=True)
            try:
                await loading_msg.edit_text(
                    localization.get_error_text("error.data_unavailable", lang)
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Помилка в show_flexible_products_handler: {e}", exc_info=True)
        try:
            await callback.answer(
                localization.get_error_text("error.general", lang), show_alert=True
            )
        except:
            pass


@router.callback_query(F.data == "type_locked")
async def show_locked_products_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await callback.answer(localization.get_text("messages.loading_products", lang))

        try:
            loading_msg = await callback.message.answer(
                localization.get_text("messages.loading_products", lang)
            )
        except Exception as e:
            logger.error(f"Помилка відправки loading message: {e}")
            loading_msg = callback.message

        try:
            await _display_locked_products(loading_msg, state, page=1, is_callback=True, lang=lang)

            if loading_msg.message_id != callback.message.message_id:
                try:
                    await callback.message.delete()
                except:
                    pass
        except Exception as e:
            logger.error(f"Помилка в _display_locked_products: {e}", exc_info=True)
            try:
                await loading_msg.edit_text(
                    localization.get_error_text("error.data_unavailable", lang)
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Помилка в show_locked_products_handler: {e}", exc_info=True)
        try:
            await callback.answer(
                localization.get_error_text("error.general", lang), show_alert=True
            )
        except:
            pass


async def _display_flexible_products(
    message, state: FSMContext, page: int = 1, is_callback: bool = False, lang: str = "ua"
) -> None:
    try:
        api_client = APIClient()

        await FilterStateManager.reset_filters_on_page_change(state, "flexible_products")

        await state.update_data(
            current_page="flexible_products",
            page=page,
            type_filter="flexible",
            total_flexible_count=0,
        )

        await FilterStateManager.save_navigation_state(
            state, current_page="flexible_products", page=page
        )

        filters = await FilterStateManager.get_current_filters(state)

        await FilterStateManager.apply_filter(state, "type", "flexible", reset_page=False)
        filters["type"] = "flexible"

        symbol = filters.get("product")
        provider = filters.get("exchange")

        provider_mapping = {
            "binance": "Binance",
            "bybit": "Bybit",
            "bitmart": "BitMart",
            "okx": "OKX",
            "mexc": "MEXC",
            "kucoin": "KuCoin",
            "gate": "gate",
            "bitget": "bitget",
            "kraken": "Kraken",
            "htx": "HTX",
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())
            logger.info(f"🔍 Мапінг провайдера: {provider} -> {provider_api}")

        items_per_page = 50
        sort_by = filters.get("sort_by", "popularity")

        logger.info(
            f"🔄 Запит всіх доступних Flexible продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}"
        )

        try:
            if sort_by == "popularity" and not symbol and not provider_api:
                data = await api_client.get_products_popular(limit=5000, offset=0)
                logger.info(
                    "🔥 Використано спеціальний endpoint /products/popular для сортування за популярністю"
                )
            else:
                data = await api_client.get_all_products(
                    limit=5000,
                    offset=0,
                    symbol=symbol.upper() if symbol else None,
                    provider=provider_api,
                    sort_by=sort_by,
                    lock_period_days=0,
                )

            logger.info(
                f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}"
            )
        except Exception as api_error:
            logger.error(f"❌ Помилка запиту до API: {api_error}", exc_info=True)
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = flexible_products_keyboard(filters, page=page, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        if not data.get("success"):
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = flexible_products_keyboard(filters, page=page, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        flexible_products = data.get("data", [])
        logger.info(f"📊 Отримано {len(flexible_products)} Flexible продуктів з API")

        if sort_by == "popularity" and not symbol and not provider_api:
            flexible_products = [p for p in flexible_products if p.get("lock_period_days", 0) == 0]
            logger.info(
                f"🔍 Після фільтрації Flexible продуктів: {len(flexible_products)} продуктів"
            )

        flexible_products = _apply_local_filters(flexible_products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(flexible_products)} продуктів")

        if sort_by == "apy_desc":
            flexible_products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            flexible_products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")

        items_per_page = 50
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = flexible_products[start_idx:end_idx]
        logger.info(
            f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(flexible_products))} з {len(flexible_products)}"
        )

        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = flexible_products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        actual_flexible_count = len(flexible_products)
        table_text = format_flexible_products_table(
            page_products, page, items_per_page, actual_flexible_count, lang=lang
        )
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        total_pages = (actual_flexible_count + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1

        text = (
            f"⚡ <b>{localization.get_text('section.flexible_products_all_exchanges', lang)}</b>\n"
        )
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: ⚡ Flexible | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: ⚡ Flexible | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"

        if not flexible_products:
            text += localization.get_text("messages.nothing_found", lang)
            logger.warning("⚠️ Немає flexible продуктів для відображення")
        else:
            if not table_text or table_text.strip() == "":
                logger.error("❌ Таблиця порожня після форматування!")
                text += f"📊 {localization.get_text('table.summary.found', lang, count=actual_flexible_count)}"
            else:
                text += table_text
            logger.info(f"✅ Текст повідомлення готовий, довжина: {len(text)}")

        keyboard = flexible_products_keyboard(
            filters, page=page, total_pages=total_pages, show_pagination=total_pages > 1, lang=lang
        )

        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")

        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"⚡ <b>{localization.get_text('section.flexible_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"

        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )

            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення Flexible продуктів: {e}", exc_info=True)
        keyboard = flexible_products_keyboard(
            filters if "filters" in locals() else {}, page=1, total_pages=1, lang=lang
        )

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(error_msg, reply_markup=keyboard)
        else:
            await message.answer(error_msg, reply_markup=keyboard)


async def _display_locked_products(
    message, state: FSMContext, page: int = 1, is_callback: bool = False, lang: str = "ua"
) -> None:
    try:
        api_client = APIClient()

        await FilterStateManager.reset_filters_on_page_change(state, "locked_products")

        await state.update_data(current_page="locked_products", page=page, type_filter="locked")

        await FilterStateManager.save_navigation_state(
            state, current_page="locked_products", page=page
        )

        filters = await FilterStateManager.get_current_filters(state)

        await FilterStateManager.apply_filter(state, "type", "locked", reset_page=False)
        filters["type"] = "locked"

        symbol = filters.get("product")
        provider = filters.get("exchange")

        provider_mapping = {
            "binance": "Binance",
            "bybit": "Bybit",
            "bitmart": "BitMart",
            "okx": "OKX",
            "mexc": "MEXC",
            "kucoin": "KuCoin",
            "gate": "gate",
            "bitget": "bitget",
            "kraken": "Kraken",
            "htx": "HTX",
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())
            logger.info(f"🔍 Мапінг провайдера: {provider} -> {provider_api}")

        items_per_page = 50
        sort_by = filters.get("sort_by", "popularity")

        logger.info(
            f"🔄 Запит Locked продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}"
        )

        try:
            stats_data = await api_client.get_database_stats()
            total_all_products = (
                stats_data.get("total_products", 0) if stats_data.get("success") else 0
            )

            total_locked_products = int(
                total_all_products * 0.35
            )  # Conservative estimate for Locked
            logger.info(
                f"📊 Загальна кількість продуктів в БД: {total_all_products}, приблизно Locked: {total_locked_products}"
            )
        except Exception as stats_error:
            logger.warning(f"⚠️ Не вдалося отримати статистику: {stats_error}, використовую 0")
            total_locked_products = 0

        total_pages = (total_locked_products + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1

        api_limit = min(5000, items_per_page * 20)

        try:
            if sort_by == "popularity" and not symbol and not provider_api:
                data = await api_client.get_products_popular(limit=api_limit, offset=0)
                logger.info(
                    "🔥 Використано спеціальний endpoint /products/popular для сортування Locked продуктів за популярністю"
                )
            else:
                data = await api_client.get_all_products(
                    limit=api_limit,
                    offset=0,
                    symbol=symbol.upper() if symbol else None,
                    provider=provider_api,
                    sort_by=sort_by,
                    lock_period_days=None,
                )

            logger.info(
                f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}"
            )
        except Exception as api_error:
            logger.error(f"❌ Помилка запиту до API: {api_error}", exc_info=True)
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = locked_products_keyboard(filters, page=1, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        if not data.get("success"):
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = locked_products_keyboard(filters, page=1, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        products = data.get("data", [])
        logger.info(f"📊 Отримано {len(products)} продуктів з API")

        if sort_by == "popularity" and not symbol and not provider_api:
            products = [p for p in products if p.get("lock_period_days", 0) > 0]
            logger.info(f"🔒 Після фільтрації Locked продуктів: {len(products)} продуктів")

        products = _apply_local_filters(products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(products)} продуктів")

        if sort_by == "apy_desc":
            products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = products[start_idx:end_idx]
        logger.info(
            f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(products))} з {len(products)}"
        )

        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        table_text = format_locked_products_table(
            page_products, page, items_per_page, len(products), lang=lang
        )
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        total_products = len(products)
        total_pages = (total_products + items_per_page - 1) // items_per_page

        text = f"🔒 <b>{localization.get_text('section.locked_products_all_exchanges', lang)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: 🔒 Locked | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: 🔒 Locked | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"

        if not products:
            text += localization.get_text("messages.nothing_found", lang)
            logger.warning("⚠️ Немає locked продуктів для відображення")
        else:
            if not table_text or table_text.strip() == "":
                logger.error("❌ Таблиця порожня після форматування!")
                text += (
                    f"📊 {localization.get_text('table.summary.found', lang, count=total_products)}"
                )
            else:
                text += table_text
            logger.info(f"✅ Текст повідомлення готовий, довжина: {len(text)}")

        keyboard = locked_products_keyboard(
            filters, page=page, total_pages=total_pages, show_pagination=total_pages > 1, lang=lang
        )

        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")

        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"🔒 <b>{localization.get_text('section.locked_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"

        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )

            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення Locked продуктів: {e}", exc_info=True)
        keyboard = locked_products_keyboard(
            filters if "filters" in locals() else {}, page=1, total_pages=1, lang=lang
        )

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(error_msg, reply_markup=keyboard)
        else:
            await message.answer(error_msg, reply_markup=keyboard)


async def _display_all_products(
    message, state: FSMContext, page: int = 1, is_callback: bool = False, lang: str = "ua"
) -> None:
    try:
        api_client = APIClient()

        await FilterStateManager.reset_filters_on_page_change(state, "all_products")

        await state.update_data(current_page="all_products", page=page, type_filter="all")

        await FilterStateManager.save_navigation_state(
            state, current_page="all_products", page=page
        )

        filters = await FilterStateManager.get_current_filters(state)

        await FilterStateManager.apply_filter(state, "type", "all", reset_page=False)
        filters["type"] = "all"

        symbol = filters.get("product")
        provider = filters.get("exchange")

        provider_mapping = {
            "binance": "Binance",
            "bybit": "Bybit",
            "bitmart": "BitMart",
            "okx": "OKX",
            "mexc": "MEXC",
            "kucoin": "KuCoin",
            "gate": "gate",
            "bitget": "bitget",
            "kraken": "Kraken",
            "htx": "HTX",
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())
            logger.info(f"🔍 Мапінг провайдера: {provider} -> {provider_api}")

        items_per_page = 50
        sort_by = filters.get("sort_by", "popularity")

        logger.info(
            f"🔄 Запит всіх доступних продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}"
        )

        try:
            if sort_by == "popularity" and not symbol and not provider_api:
                data = await api_client.get_products_popular(limit=5000, offset=0)
                logger.info(
                    "🔥 Використано спеціальний endpoint /products/popular для сортування всіх продуктів за популярністю"
                )
            else:
                data = await api_client.get_all_products(
                    limit=5000,
                    offset=0,
                    symbol=symbol.upper() if symbol else None,
                    provider=provider_api,
                    sort_by=sort_by,
                )

            logger.info(
                f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}"
            )
        except Exception as api_error:
            logger.error(f"❌ Помилка запиту до API: {api_error}", exc_info=True)
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = all_products_keyboard(filters, page=page, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        if not data.get("success"):
            error_text = localization.get_error_text("error.data_unavailable", lang)
            keyboard = all_products_keyboard(filters, page=page, total_pages=1, lang=lang)

            if is_callback:
                await message.edit_text(error_text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=keyboard, parse_mode="HTML")

            await api_client.close()
            return

        products = data.get("data", [])
        logger.info(f"📊 Отримано {len(products)} продуктів з API")

        if len(products) == 0:
            logger.warning(
                f"⚠️ API повернув порожній список продуктів. Параметри запиту: limit=5000, offset=0, symbol={symbol}, provider={provider_api}, sort_by={sort_by}"
            )
            logger.warning(
                f"⚠️ Повна відповідь API: success={data.get('success')}, count={data.get('count')}, message={data.get('message')}"
            )

        products = _apply_local_filters(products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(products)} продуктів")

        if sort_by == "apy_desc":
            products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")

        items_per_page = 50
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = products[start_idx:end_idx]
        logger.info(
            f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(products))} з {len(products)}"
        )

        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        actual_filtered_count = len(products)
        table_text = format_all_products_table(
            page_products, page, items_per_page, actual_filtered_count, lang=lang
        )
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        total_pages = (actual_filtered_count + items_per_page - 1) // items_per_page

        text = f"📊 <b>{localization.get_text('section.all_products_all_exchanges', lang)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: 📊 {localization.get_text('nav.all_products', lang)} | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: 📊 {localization.get_text('nav.all_products', lang)} | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"

        if not page_products:
            text += localization.get_text("messages.nothing_found", lang)
            logger.warning("⚠️ Немає продуктів для відображення на цій сторінці")
        else:
            if not table_text or table_text.strip() == "":
                logger.error("❌ Таблиця порожня після форматування!")
                text += f"📊 {localization.get_text('table.summary.found', lang, count=actual_filtered_count)}"
            else:
                text += table_text
            logger.info(f"✅ Текст повідомлення готовий, довжина: {len(text)}")

        keyboard = all_products_keyboard(
            filters, page=page, total_pages=total_pages, show_pagination=total_pages > 1, lang=lang
        )

        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")

        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"📊 <b>{localization.get_text('section.all_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"

        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )

            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення всіх продуктів: {e}", exc_info=True)
        keyboard = all_products_keyboard(
            filters if "filters" in locals() else {}, page=1, total_pages=1, lang=lang
        )

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(error_msg, reply_markup=keyboard)
        else:
            await message.answer(error_msg, reply_markup=keyboard)


@router.callback_query(F.data.startswith("flexible_prev:"))
async def flexible_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = max(1, current_page - 1)

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_flexible_products(
            callback.message, state, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в flexible_prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("flexible_next:"))
async def flexible_next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_flexible_products(
            callback.message, state, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в flexible_next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("locked_prev:"))
async def locked_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = max(1, current_page - 1)

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_locked_products(
            callback.message, state, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в locked_prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("locked_next:"))
async def locked_next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_locked_products(
            callback.message, state, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в locked_next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("all_prev:"))
async def all_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = max(1, current_page - 1)

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_all_products(callback.message, state, new_page, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в all_prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("all_next:"))
async def all_next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_all_products(callback.message, state, new_page, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в all_next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


def _apply_local_filters(products: List[Dict], filters: Dict) -> List[Dict]:
    filtered = products

    if filters.get("product"):
        filtered = [
            p for p in filtered if p.get("symbol", "").upper() == filters["product"].upper()
        ]

    # if filters.get("exchange"):
    #     filtered = [p for p in filtered if p.get("provider", "").lower() == filters["exchange"].lower()]

    return filtered


async def show_product_all_exchanges(
    message_or_callback, state: FSMContext, symbol: str, lang: str = "ua"
) -> None:
    try:
        api_client = APIClient()

        await FilterStateManager.apply_filter(state, "product", symbol)

        data = await api_client.get_yield_by_symbol(symbol, limit=100)

        if not data.get("success"):
            text = f"❌ {localization.get_text('messages.loading_failed', lang)}: {symbol}"
        else:
            products = data.get("data", [])

            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            text = filters_display + "\n\n"

            text += f"💳 <b>{symbol} — {localization.get_text('nav.all_exchanges', lang)}</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            text += f"📊 {localization.get_text('messages.offers_for_product', lang, product=symbol)}\n\n"
            text += _format_product_comparison_table(products, lang=lang)

            text += (
                f"\n📈 {localization.get_text('table.summary.shown', lang, count=len(products))}\n"
            )

        filters = await FilterStateManager.get_current_filters(state)
        keyboard = filter_keyboard(filters, lang=lang)

        if hasattr(message_or_callback, "edit_text"):
            await message_or_callback.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка в show_product_all_exchanges: {e}", exc_info=True)


def _format_product_comparison_table(products: List[Dict], lang: str = "ua") -> str:
    if not products:
        return localization.get_text("messages.nothing_found", lang)

    # Header: "Exchange Type APY Period"
    h_exchange = localization.get_text("table.header.exchange", lang)
    h_type = localization.get_text("table.header.type", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    h_period = localization.get_text("table.header.period", lang)

    # Construct header row manually to fit width constraints if needed or simple format
    # Using fixed width for consistency with other tables
    header = f"{h_exchange[:10].ljust(10)} {h_type[:9].ljust(9)} {h_apy[:6].rjust(6)} {h_period[:6].rjust(6)}"

    text = "<pre>"
    text += f"{header}\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for product in products[:20]:
        provider = product.get("provider", "???")[:10].ljust(10)
        lock_days = product.get("lock_period_days", 0)

        # Type labels
        type_str = ("Flex" if lock_days == 0 else "Lock").ljust(
            9
        )  # Maybe localize "Flex"/"Lock"? Short space.
        # If localized, keep it short.
        if lang == "ua":
            type_str = ("Гнуч" if lock_days == 0 else "Фікс").ljust(9)
        elif lang == "ru":
            type_str = ("Гибк" if lock_days == 0 else "Фикс").ljust(9)

        apy = product.get("apy", 0)
        if apy >= 1:
            apy_str = f"{apy:.1f}%".rjust(6)
        elif apy >= 0.01:
            apy_str = f"{apy:.2f}%".rjust(6)
        else:
            apy_str = f"{apy:.3f}%".rjust(6)

        period = "—" if lock_days == 0 else f"{lock_days}d"
        period = period.rjust(6)

        text += f"{provider} {type_str} {apy_str}  {period}\n"

    text += "</pre>"

    return text
