"""
Обробник фільтрованих результатів (Сторінки 3-9).

Відображає продукти за різними комбінаціями фільтрів:
- Сторінка 3: Flexible products з усіх бірж
- Сторінка 5: Продукт + всі біржі
- Сторінка 6: Продукт + конкретна біржа
- Сторінка 7-9: Інші комбінації фільтрів
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from typing import List, Dict

from bot.services.api_client import APIClient
from bot.keyboards.filters import filter_keyboard, flexible_products_keyboard, locked_products_keyboard, all_products_keyboard
from bot.keyboards.navigation import back_button_keyboard
from bot.utils.pagination import Paginator
from bot.utils.formatters import format_flexible_products_table, format_locked_products_table, format_all_products_table
from bot.utils.logger import logger
from bot.services.filter_state import FilterStateManager
from bot.utils.loading_indicator import LoadingIndicator
from bot.localization import localization

router = Router(name="filtered_products_handler")


@router.callback_query(F.data == "type_flexible")
async def show_flexible_products_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник кнопки Flexible - перехід на сторінку 3."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        await callback.answer(localization.get_text("messages.loading_products", lang))

        # Відправити повідомлення про завантаження
        try:
            loading_msg = await callback.message.answer(localization.get_text("messages.loading_products", lang))
        except Exception as e:
            logger.error(f"Помилка відправки loading message: {e}")
            loading_msg = callback.message  # Fallback на оригінальне повідомлення

        try:
            await _display_flexible_products(loading_msg, state, page=1, is_callback=True, lang=lang)
            # Видалити повідомлення про завантаження після успішного відображення (якщо це було нове повідомлення)
            if loading_msg.message_id != callback.message.message_id:
                try:
                    await callback.message.delete()
                except:
                    pass  # Ігноруємо помилки видалення
        except Exception as e:
            logger.error(f"Помилка в _display_flexible_products: {e}", exc_info=True)
            try:
                await loading_msg.edit_text(localization.get_error_text("error.data_unavailable", lang))
            except:
                pass
    except Exception as e:
        logger.error(f"Помилка в show_flexible_products_handler: {e}", exc_info=True)
        try:
            await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)
        except:
            pass


@router.callback_query(F.data == "type_locked")
async def show_locked_products_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник кнопки Locked - перехід на сторінку з Locked продуктами."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        await callback.answer(localization.get_text("messages.loading_products", lang))

        # Відправити повідомлення про завантаження
        try:
            loading_msg = await callback.message.answer(localization.get_text("messages.loading_products", lang))
        except Exception as e:
            logger.error(f"Помилка відправки loading message: {e}")
            loading_msg = callback.message  # Fallback на оригінальне повідомлення

        try:
            await _display_locked_products(loading_msg, state, page=1, is_callback=True, lang=lang)
            # Видалити повідомлення про завантаження після успішного відображення (якщо це було нове повідомлення)
            if loading_msg.message_id != callback.message.message_id:
                try:
                    await callback.message.delete()
                except:
                    pass  # Ігноруємо помилки видалення
        except Exception as e:
            logger.error(f"Помилка в _display_locked_products: {e}", exc_info=True)
            try:
                await loading_msg.edit_text(localization.get_error_text("error.data_unavailable", lang))
            except:
                pass
    except Exception as e:
        logger.error(f"Помилка в show_locked_products_handler: {e}", exc_info=True)
        try:
            await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)
        except:
            pass


async def _display_flexible_products(
    message,
    state: FSMContext,
    page: int = 1,
    is_callback: bool = False,
    lang: str = "ua"
) -> None:
    """
    Відобразити Flexible продукти з усіх бірж (Сторінка 3).
    
    Args:
        message: Повідомлення для редагування
        state: FSM контекст
        page: Номер сторінки
        is_callback: Чи це callback запит
        lang: Код мови
    """
    try:
        api_client = APIClient()

        # Скинути фільтри при переході на сторінку flexible продуктів
        await FilterStateManager.reset_filters_on_page_change(state, "flexible_products")

        # Зберегти стан сторінки
        await state.update_data(
            current_page="flexible_products",
            page=page,
            type_filter="flexible",
            total_flexible_count=0  # буде оновлено після фільтрації
        )

        # Зберегти навігаційний стан
        await FilterStateManager.save_navigation_state(
            state,
            current_page="flexible_products",
            page=page
        )
        
        # Отримати фільтри
        filters = await FilterStateManager.get_current_filters(state)
        
        # Встановити фільтр типу на Flexible
        await FilterStateManager.apply_filter(state, "type", "flexible", reset_page=False)
        filters["type"] = "flexible"
        
        # Отримати продукти з API
        symbol = filters.get("product")
        provider = filters.get("exchange")
        
        # Мапінг назв бірж для API (відповідність до назв в базі даних)
        provider_mapping = {
            'binance': 'Binance',
            'bybit': 'Bybit',
            'bitmart': 'BitMart',
            'okx': 'OKX',
            'mexc': 'MEXC',
            'kucoin': 'KuCoin',
            'gate': 'gate',
            'bitget': 'bitget',
            'kraken': 'Kraken',
            'htx': 'htx'
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())

        # Отримати всі продукти з фільтрами
        # Використовуємо оптимізований API endpoint з сортуванням за популярністю за замовчуванням
        sort_by = filters.get("sort_by", "popularity")
        
        # Для Flexible продуктів отримуємо всі доступні продукти (до 1000) і пагінуємо локально
        items_per_page = 50
        sort_by = filters.get("sort_by", "popularity")

        logger.info(f"🔄 Запит всіх доступних Flexible продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}")

        try:
            # Отримуємо максимальну кількість доступних Flexible продуктів
            data = await api_client.get_all_products(
                limit=5000,  # Максимально дозволений limit
                offset=0,
                symbol=symbol.upper() if symbol else None,
                provider=provider_api,
                sort_by=sort_by,
                lock_period_days=0  # Фільтр для Flexible продуктів
            )
            
            logger.info(f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}")
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

        # Застосувати локальні фільтри (якщо потрібно)
        flexible_products = _apply_local_filters(flexible_products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(flexible_products)} продуктів")

        # Продукти вже відсортовані через API (за популярністю за замовчуванням)
        # Локальне сортування тільки для інших типів сортування
        if sort_by == "apy_desc":
            flexible_products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            flexible_products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")
        elif sort_by == "popularity":
            # Продукти вже відсортовані за популярністю через API
            logger.info("📊 Продукти відсортовані за популярністю (через API JOIN)")

        # Вибираємо порцію для поточної сторінки після сортування
        items_per_page = 50
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = flexible_products[start_idx:end_idx]
        logger.info(f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(flexible_products))} з {len(flexible_products)}")

        # Якщо сторінка порожня і це не перша сторінка, повертаємося на попередню
        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = flexible_products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        # Форматування таблиці з реальною кількістю продуктів
        actual_flexible_count = len(flexible_products)
        table_text = format_flexible_products_table(page_products, page, items_per_page, actual_flexible_count, lang=lang)
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        # Підрахунок сторінок
        total_pages = (actual_flexible_count + items_per_page - 1) // items_per_page
        if total_pages == 0: total_pages = 1
        
        # Формування тексту повідомлення
        text = f"⚡ <b>{localization.get_text('section.flexible_products_all_exchanges', lang)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Активні фільтри
        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: ⚡ Flexible | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: ⚡ Flexible | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        
        # Таблиця
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
        
        # Створити клавіатуру
        keyboard = flexible_products_keyboard(
            filters,
            page=page,
            total_pages=total_pages,
            show_pagination=total_pages > 1,
            lang=lang
        )
        
        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")
        
        # Перевірка мінімальної довжини тексту
        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"⚡ <b>{localization.get_text('section.flexible_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"
        
        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            
            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise
        
        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення Flexible продуктів: {e}", exc_info=True)
        keyboard = flexible_products_keyboard(filters if 'filters' in locals() else {}, page=1, total_pages=1, lang=lang)

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(
                error_msg,
                reply_markup=keyboard
            )
        else:
            await message.answer(
                error_msg,
                reply_markup=keyboard
            )


async def _display_locked_products(
    message,
    state: FSMContext,
    page: int = 1,
    is_callback: bool = False,
    lang: str = "ua"
) -> None:
    """
    Відобразити Locked продукти з усіх бірж.

    Args:
        message: Повідомлення для редагування
        state: FSM контекст
        page: Номер сторінки
        is_callback: Чи це callback запит
        lang: Код мови
    """
    try:
        api_client = APIClient()

        # Скинути фільтри при переході на сторінку locked продуктів
        await FilterStateManager.reset_filters_on_page_change(state, "locked_products")

        # Зберегти стан сторінки
        await state.update_data(
            current_page="locked_products",
            page=page,
            type_filter="locked"
        )

        # Зберегти навігаційний стан
        await FilterStateManager.save_navigation_state(
            state,
            current_page="locked_products",
            page=page
        )

        # Отримати фільтри
        filters = await FilterStateManager.get_current_filters(state)

        # Встановити фільтр типу на Locked
        await FilterStateManager.apply_filter(state, "type", "locked", reset_page=False)
        filters["type"] = "locked"

        # Отримати продукти з API
        symbol = filters.get("product")
        provider = filters.get("exchange")

        # Мапінг назв бірж для API (відповідність до назв в базі даних)
        provider_mapping = {
            'binance': 'Binance',
            'bybit': 'Bybit',
            'bitmart': 'BitMart',
            'okx': 'OKX',
            'mexc': 'MEXC',
            'kucoin': 'KuCoin',
            'gate': 'gate',
            'bitget': 'bitget',
            'kraken': 'Kraken',
            'htx': 'htx'
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())

        # Отримати всі продукти з фільтрами
        # Використовуємо оптимізований API endpoint з сортуванням за популярністю за замовчуванням
        sort_by = filters.get("sort_by", "popularity")

        logger.info(f"🔄 Запит продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}")

        # Спочатку отримуємо статистику для підрахунку загальної кількості Locked продуктів
        try:
            stats_data = await api_client.get_database_stats()
            total_all_products = stats_data.get("total_products", 0) if stats_data.get("success") else 0
            # Приблизно оцінюємо кількість Locked продуктів (зазвичай менше ніж половина)
            total_locked_products = int(total_all_products * 0.35)  # Conservative estimate for Locked
            logger.info(f"📊 Загальна кількість продуктів в БД: {total_all_products}, приблизно Locked: {total_locked_products}")
        except Exception as stats_error:
            logger.warning(f"⚠️ Не вдалося отримати статистику: {stats_error}, використовую 0")
            total_locked_products = 0

        # Розрахувати загальну кількість сторінок
        items_per_page = 50
        total_pages = (total_locked_products + items_per_page - 1) // items_per_page
        if total_pages == 0:
            total_pages = 1

        # Отримуємо більше продуктів, щоб після фільтрації Locked залишилося достатньо
        # Використовуємо більший limit, щоб компенсувати фільтрацію
        api_limit = min(5000, items_per_page * 20)  # отримуємо в 20 разів більше, але не більше 5000
        offset = 0  # завжди починаємо з початку, бо фільтруємо локально

        try:
            data = await api_client.get_all_products(
                limit=api_limit,
                offset=offset,
                symbol=symbol.upper() if symbol else None,
                provider=provider_api,
                sort_by=sort_by,
                lock_period_days=None  # Отримуємо всі продукти, потім відфільтруємо локально
            )

            logger.info(f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}")
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

        # Фільтруємо тільки Locked продукти (lock_period_days > 0)
        products = [p for p in products if p.get("lock_period_days", 0) > 0]
        logger.info(f"🔒 Після фільтрації Locked продуктів: {len(products)} продуктів")

        # Застосувати локальні фільтри (якщо потрібно)
        products = _apply_local_filters(products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(products)} продуктів")

        # Продукти вже відсортовані через API (за популярністю за замовчуванням)
        # Локальне сортування тільки для інших типів сортування
        if sort_by == "apy_desc":
            products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")
        elif sort_by == "popularity":
            # Продукти вже відсортовані за популярністю через API JOIN
            logger.info("📊 Продукти відсортовані за популярністю (через API JOIN)")

        # Вибираємо порцію для поточної сторінки після всіх фільтрів і сортування
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = products[start_idx:end_idx]
        logger.info(f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(products))} з {len(products)}")

        # Якщо сторінка порожня і це не перша сторінка, повертаємося на попередню
        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        # Форматування таблиці
        table_text = format_locked_products_table(page_products, page, items_per_page, len(products), lang=lang)
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        # Підрахунок сторінок
        total_products = len(products)
        total_pages = (total_products + items_per_page - 1) // items_per_page

        # Формування тексту повідомлення
        text = f"🔒 <b>{localization.get_text('section.locked_products_all_exchanges', lang)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Активні фільтри
        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: 🔒 Locked | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: 🔒 Locked | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"

        # Таблиця
        if not products:
            text += localization.get_text("messages.nothing_found", lang)
            logger.warning("⚠️ Немає locked продуктів для відображення")
        else:
            if not table_text or table_text.strip() == "":
                logger.error("❌ Таблиця порожня після форматування!")
                text += f"📊 {localization.get_text('table.summary.found', lang, count=total_products)}"
            else:
                text += table_text
            logger.info(f"✅ Текст повідомлення готовий, довжина: {len(text)}")

        # Створити клавіатуру
        keyboard = locked_products_keyboard(
            filters,
            page=page,
            total_pages=total_pages,
            show_pagination=total_pages > 1,
            lang=lang
        )

        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")

        # Перевірка мінімальної довжини тексту
        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"🔒 <b>{localization.get_text('section.locked_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"

        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )

            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення Locked продуктів: {e}", exc_info=True)
        keyboard = locked_products_keyboard(filters if 'filters' in locals() else {}, page=1, total_pages=1, lang=lang)

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(
                error_msg,
                reply_markup=keyboard
            )
        else:
            await message.answer(
                error_msg,
                reply_markup=keyboard
            )


async def _display_all_products(
    message,
    state: FSMContext,
    page: int = 1,
    is_callback: bool = False,
    lang: str = "ua"
) -> None:
    """
    Відобразити всі продукти з усіх бірж (Flexible + Locked).

    Args:
        message: Повідомлення для редагування
        state: FSM контекст
        page: Номер сторінки
        is_callback: Чи це callback запит
        lang: Код мови
    """
    try:
        api_client = APIClient()

        # Скинути фільтри при переході на сторінку всіх продуктів
        await FilterStateManager.reset_filters_on_page_change(state, "all_products")

        # Зберегти стан сторінки
        await state.update_data(
            current_page="all_products",
            page=page,
            type_filter="all"
        )

        # Зберегти навігаційний стан
        await FilterStateManager.save_navigation_state(
            state,
            current_page="all_products",
            page=page
        )

        # Отримати фільтри
        filters = await FilterStateManager.get_current_filters(state)

        # Встановити фільтр типу на "all" (всі продукти)
        await FilterStateManager.apply_filter(state, "type", "all", reset_page=False)
        filters["type"] = "all"

        # Отримати продукти з API
        symbol = filters.get("product")
        provider = filters.get("exchange")

        # Мапінг назв бірж для API (відповідність до назв в базі даних)
        provider_mapping = {
            'binance': 'Binance',
            'bybit': 'Bybit',
            'bitmart': 'BitMart',
            'okx': 'OKX',
            'mexc': 'MEXC',
            'kucoin': 'KuCoin',
            'gate': 'gate',
            'bitget': 'bitget',
            'kraken': 'Kraken',
            'htx': 'htx'
        }
        provider_api = None
        if provider:
            provider_api = provider_mapping.get(provider.lower(), provider.title())

        # Для всіх продуктів отримуємо всі доступні відфільтровані продукти і пагінуємо локально
        items_per_page = 50
        sort_by = filters.get("sort_by", "popularity")

        logger.info(f"🔄 Запит всіх доступних продуктів: symbol={symbol}, provider={provider_api}, sort_by={sort_by}")

        try:
            # Отримуємо максимальну кількість доступних відфільтрованих продуктів
            data = await api_client.get_all_products(
                limit=5000,  # Максимально дозволений limit
                offset=0,
                symbol=symbol.upper() if symbol else None,
                provider=provider_api,
                sort_by=sort_by
            )

            logger.info(f"📦 Отримано відповідь: success={data.get('success')}, products_count={len(data.get('data', []))}")
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

        # Застосувати локальні фільтри (якщо потрібно)
        products = _apply_local_filters(products, filters)
        logger.info(f"🔍 Після локальних фільтрів: {len(products)} продуктів")

        # Продукти вже відсортовані через API (за популярністю за замовчуванням)
        # Локальне сортування тільки для інших типів сортування
        if sort_by == "apy_desc":
            products.sort(key=lambda x: x.get("apy", 0), reverse=True)
            logger.info("📊 Продукти відсортовані за APY (від більшого)")
        elif sort_by == "apy_asc":
            products.sort(key=lambda x: x.get("apy", 0))
            logger.info("📊 Продукти відсортовані за APY (від меншого)")
        elif sort_by == "popularity":
            # Продукти вже відсортовані за популярністю через API JOIN
            logger.info("📊 Продукти відсортовані за популярністю (через API JOIN)")

        # Вибираємо порцію для поточної сторінки після сортування
        items_per_page = 50
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_products = products[start_idx:end_idx]
        logger.info(f"📄 Сторінка {page}: показуємо продукти {start_idx}-{min(end_idx, len(products))} з {len(products)}")

        # Якщо сторінка порожня і це не перша сторінка, повертаємося на попередню
        if not page_products and page > 1:
            logger.warning(f"⚠️ Сторінка {page} порожня, повертаємося на попередню")
            new_page = page - 1
            await state.update_data(page=new_page)
            start_idx = (new_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_products = products[start_idx:end_idx]
            page = new_page
            logger.info(f"📄 Повернулися на сторінку {page}")

        # Форматування таблиці з реальною кількістю продуктів
        actual_filtered_count = len(products)
        table_text = format_all_products_table(page_products, page, items_per_page, actual_filtered_count, lang=lang)
        logger.info(f"📋 Таблиця сформована, довжина тексту: {len(table_text)}")

        # Підрахунок сторінок
        total_pages = (actual_filtered_count + items_per_page - 1) // items_per_page

        # Формування тексту повідомлення
        text = f"📊 <b>{localization.get_text('section.all_products_all_exchanges', lang)}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Активні фільтри
        try:
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            if filters_display:
                text += filters_display + "\n\n"
            else:
                text += f"🔍 {localization.get_text('menu.filter', lang)}: 📊 {localization.get_text('nav.all_products', lang)} | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"
        except Exception as e:
            logger.warning(f"⚠️ Помилка отримання filters_display: {e}")
            text += f"🔍 {localization.get_text('menu.filter', lang)}: 📊 {localization.get_text('nav.all_products', lang)} | ⭐ {localization.get_text('menu.sort_popularity', lang)}\n\n"

        # Таблиця
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

        # Створити клавіатуру
        keyboard = all_products_keyboard(
            filters,
            page=page,
            total_pages=total_pages,
            show_pagination=total_pages > 1,
            lang=lang
        )

        logger.info(f"⌨️ Клавіатура створена, сторінка {page}/{total_pages}")

        # Перевірка мінімальної довжини тексту
        if len(text.strip()) < 10:
            logger.error(f"❌ Текст повідомлення занадто короткий: {len(text)} символів")
            text = f"📊 <b>{localization.get_text('section.all_products_all_exchanges', lang)}</b>\n\n{localization.get_error_text('error.display_results_error', lang)}"

        try:
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )

            logger.info("✅ Повідомлення відправлено успішно")
        except Exception as send_error:
            logger.error(f"❌ Помилка відправки повідомлення: {send_error}", exc_info=True)
            logger.error(f"❌ Текст повідомлення (перші 200 символів): {text[:200]}")
            raise

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення всіх продуктів: {e}", exc_info=True)
        keyboard = all_products_keyboard(filters if 'filters' in locals() else {}, page=1, total_pages=1, lang=lang)

        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(
                error_msg,
                reply_markup=keyboard
            )
        else:
            await message.answer(
                error_msg,
                reply_markup=keyboard
            )


@router.callback_query(F.data.startswith("flexible_prev:"))
async def flexible_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник попередньої сторінки для Flexible products."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = max(1, current_page - 1)
        
        await state.update_data(page=new_page)
        await callback.answer()
        await _display_flexible_products(callback.message, state, new_page, is_callback=True, lang=lang)
        
    except Exception as e:
        logger.error(f"Помилка в flexible_prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("flexible_next:"))
async def flexible_next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник наступної сторінки для Flexible products."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_flexible_products(callback.message, state, new_page, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в flexible_next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("locked_prev:"))
async def locked_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник попередньої сторінки для Locked products."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = max(1, current_page - 1)

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_locked_products(callback.message, state, new_page, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в locked_prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("locked_next:"))
async def locked_next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник наступної сторінки для Locked products."""
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_locked_products(callback.message, state, new_page, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в locked_next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("all_prev:"))
async def all_prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник попередньої сторінки для всіх продуктів."""
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
    """Обробник наступної сторінки для всіх продуктів."""
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
    """
    Застосувати локальні фільтри до продуктів.
    
    Args:
        products: Список продуктів
        filters: Словник з фільтрами
        
    Returns:
        Відфільтрований список продуктів
    """
    filtered = products
    
    # Фільтр по продукту (символу)
    if filters.get("product"):
        filtered = [p for p in filtered if p.get("symbol", "").upper() == filters["product"].upper()]
    
    # Фільтр по біржі - не потрібен, оскільки API вже фільтрує по provider
    # if filters.get("exchange"):
    #     filtered = [p for p in filtered if p.get("provider", "").lower() == filters["exchange"].lower()]
    
    return filtered


async def show_product_all_exchanges(
    message_or_callback,
    state: FSMContext,
    symbol: str,
    lang: str = "ua"
) -> None:
    """
    Показати продукт по всіх біржах (Сторінка 5).
    
    Args:
        message_or_callback: Message або CallbackQuery
        state: FSM контекст
        symbol: Символ криптовалюти
        lang: Код мови
    """
    try:
        api_client = APIClient()
        
        # Встановити фільтр
        await FilterStateManager.apply_filter(state, "product", symbol)
        
        # Отримати дані
        data = await api_client.get_yield_by_symbol(symbol, limit=100)
        
        if not data.get("success"):
            text = f"❌ {localization.get_text('messages.loading_failed', lang)}: {symbol}"
        else:
            products = data.get("data", [])
            
            # Блок 1: Фільтри
            filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
            text = filters_display + "\n\n"
            
            # Блок 2: Заголовок
            text += f"💳 <b>{symbol} — {localization.get_text('nav.all_exchanges', lang)}</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # Блок 3: Таблиця
            text += f"📊 {localization.get_text('messages.offers_for_product', lang, product=symbol)}\n\n"
            text += _format_product_comparison_table(products, lang=lang)
            
            # Блок 4: Підсумок
            text += f"\n📈 {localization.get_text('table.summary.shown', lang, count=len(products))}\n"
        
        # Відправити або редагувати
        filters = await FilterStateManager.get_current_filters(state)
        keyboard = filter_keyboard(filters, lang=lang)
        
        if hasattr(message_or_callback, 'edit_text'):
            await message_or_callback.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
        await api_client.close()
        
    except Exception as e:
        logger.error(f"Помилка в show_product_all_exchanges: {e}", exc_info=True)


def _format_product_comparison_table(products: List[Dict], lang: str = "ua") -> str:
    """
    Форматувати порівняльну таблицю продуктів.
    
    Args:
        products: Список продуктів
        lang: Код мови
        
    Returns:
        Відформатований текст
    """
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
    
    for product in products[:20]:  # Макс 20 продуктів
        provider = product.get("provider", "???")[:10].ljust(10)
        lock_days = product.get("lock_period_days", 0)
        
        # Type labels
        type_str = ("Flex" if lock_days == 0 else "Lock").ljust(9) # Maybe localize "Flex"/"Lock"? Short space.
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
