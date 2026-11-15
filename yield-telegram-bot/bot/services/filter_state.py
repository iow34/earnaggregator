from typing import Optional, Any, Dict
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.utils.logger import logger
from bot.localization import localization


class FilterStates(StatesGroup):
    selecting_product = State()
    selecting_exchange = State()
    selecting_type = State()
    selecting_apy_range = State()
    selecting_sort = State()
    entering_product_manual = State()
    entering_exchange_manual = State()

    viewing_results = State()
    viewing_product_details = State()


class FilterStateManager:
    @staticmethod
    async def get_current_filters(state: FSMContext) -> Dict[str, Any]:
        data = await state.get_data()
        return {
            "product": data.get("product_filter"),
            "exchange": data.get("exchange_filter"),
            "type": data.get("type_filter"),
            "apy_min": data.get("apy_min"),
            "apy_max": data.get("apy_max"),
            "sort_by": data.get("sort_by", "popularity"),
            "page": data.get("page", 1),
        }

    @staticmethod
    async def apply_filter(
        state: FSMContext, filter_name: str, value: Any, reset_page: bool = True
    ) -> None:
        update_data = {f"{filter_name}_filter": value}
        if reset_page:
            update_data["page"] = 1

        await state.update_data(**update_data)

    @staticmethod
    async def reset_filters(state: FSMContext, keep_exchange: bool = False) -> None:
        data = await state.get_data()
        exchange_filter = data.get("exchange_filter") if keep_exchange else None

        await state.update_data(
            product_filter=None,
            exchange_filter=exchange_filter,
            type_filter=None,
            apy_min=None,
            apy_max=None,
            sort_by="popularity",
            page=1,
        )

    @staticmethod
    async def reset_filters_on_page_change(state: FSMContext, new_page_type: str) -> None:
        data = await state.get_data()
        current_page_type = data.get("current_page")

        should_reset = False

        page_categories = {
            "exchange_products": "single_exchange",
            "all_products": "general_products",
            "flexible_products": "general_products",
            "locked_products": "general_products",
            "advanced_search": "search",
            "main_menu": "menu",
            "all_exchanges": "exchanges_list",
        }

        current_category = page_categories.get(current_page_type)
        new_category = page_categories.get(new_page_type)

        if current_category and new_category and current_category != new_category:
            should_reset = True

        if new_page_type in ["exchange_products"] and current_page_type not in [
            "exchange_products"
        ]:
            should_reset = True
        elif (
            new_page_type in ["all_products", "flexible_products", "locked_products"]
            and current_page_type == "exchange_products"
        ):
            should_reset = True

        if should_reset:
            await FilterStateManager.reset_filters(state, keep_exchange=False)

            await state.update_data(navigation_history=[])
            logger.info(
                f"🔄 Скинуто фільтри та історію навігації при переході з {current_page_type} на {new_page_type}"
            )

    @staticmethod
    async def set_page(state: FSMContext, page: int) -> None:
        await state.update_data(page=page)

    @staticmethod
    async def get_page(state: FSMContext) -> int:
        data = await state.get_data()
        return data.get("page", 1)

    @staticmethod
    async def save_navigation_state(state: FSMContext, current_page: str, **kwargs) -> None:
        data = await state.get_data()
        navigation_history = data.get("navigation_history", [])

        navigation_history.append({"page": current_page, **kwargs})

        await state.update_data(
            current_page=current_page, navigation_history=navigation_history[-10:], **kwargs
        )

    @staticmethod
    async def get_previous_page(state: FSMContext) -> Optional[Dict[str, Any]]:
        data = await state.get_data()
        navigation_history = data.get("navigation_history", [])

        if len(navigation_history) > 1:
            navigation_history.pop()
            previous = navigation_history[-1]
            await state.update_data(navigation_history=navigation_history)
            return previous

        return None

    @staticmethod
    async def get_active_filters_count(state: FSMContext) -> int:
        filters = await FilterStateManager.get_current_filters(state)
        count = 0

        if filters["product"]:
            count += 1
        if filters["exchange"]:
            count += 1
        if filters["type"]:
            count += 1
        if filters["apy_min"] or filters["apy_max"]:
            count += 1

        return count

    @staticmethod
    async def get_filters_display(state: FSMContext, lang: str = "ua") -> str:
        filters = await FilterStateManager.get_current_filters(state)
        parts = []

        if filters["product"]:
            product_text = filters["product"].upper()
            parts.append(
                localization.get_text("search.filters.product", lang, product=product_text)
            )
        if filters["exchange"]:
            exchange_name = filters["exchange"].title()
            parts.append(
                localization.get_text("search.filters.exchange", lang, exchange=exchange_name)
            )
        if filters["type"]:
            type_key = f"search.type.{filters['type'].lower()}"
            type_value = localization.get_text(type_key, lang)
            parts.append(localization.get_text("search.filters.type", lang, type=type_value))
        if filters["apy_min"] or filters["apy_max"]:
            apy_min = filters.get("apy_min")
            apy_max = filters.get("apy_max")
            range_text = None
            if apy_min is not None and apy_max is not None:
                range_text = localization.get_text(
                    "search.filters.range.from_to", lang, min=apy_min, max=apy_max
                )
            elif apy_min is not None:
                range_text = localization.get_text("search.filters.range.from", lang, value=apy_min)
            elif apy_max is not None:
                range_text = localization.get_text("search.filters.range.to", lang, value=apy_max)
            if range_text:
                parts.append(
                    localization.get_text("search.filters.apy_range", lang, range=range_text)
                )

        sort_by = filters.get("sort_by", "popularity")
        sort_map = {
            "popularity": "search.filters.sort.popularity",
            "apy_desc": "search.filters.sort.apy_desc",
            "apy_asc": "search.filters.sort.apy_asc",
        }
        sort_key = sort_map.get(sort_by)
        if sort_key:
            parts.append(localization.get_text(sort_key, lang))

        if parts:
            prefix = localization.get_text("search.filters.prefix", lang)
            return f"{prefix} " + " | ".join(parts)
        return localization.get_text("search.filters.none", lang)
