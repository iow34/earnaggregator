import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.services.filter_state import FilterStateManager, FilterStates


@pytest.mark.asyncio
async def test_get_current_filters():
    # Mock FSMContext
    state = AsyncMock()
    state.get_data.return_value = {
        "product_filter": "BTC",
        "exchange_filter": "binance",
        "type_filter": "flexible",
        "sort_by": "popularity",
        "page": 2,
    }

    filters = await FilterStateManager.get_current_filters(state)

    assert filters["product"] == "BTC"
    assert filters["exchange"] == "binance"
    assert filters["type"] == "flexible"
    assert filters["sort_by"] == "popularity"
    assert filters["page"] == 2


@pytest.mark.asyncio
async def test_apply_filter():
    state = AsyncMock()

    await FilterStateManager.apply_filter(state, "product", "ETH")

    state.update_data.assert_called_once()
    call_args = state.update_data.call_args[1]
    assert call_args["product_filter"] == "ETH"
    assert call_args["page"] == 1


@pytest.mark.asyncio
async def test_reset_filters():
    state = AsyncMock()
    state.get_data.return_value = {"exchange_filter": "binance", "product_filter": "BTC"}

    await FilterStateManager.reset_filters(state, keep_exchange=False)

    state.update_data.assert_called_once()
    call_args = state.update_data.call_args[1]
    assert call_args["product_filter"] is None
    assert call_args["exchange_filter"] is None
    assert call_args["page"] == 1


@pytest.mark.asyncio
async def test_reset_filters_keep_exchange():
    state = AsyncMock()
    state.get_data.return_value = {"exchange_filter": "binance", "product_filter": "BTC"}

    await FilterStateManager.reset_filters(state, keep_exchange=True)

    call_args = state.update_data.call_args[1]
    assert call_args["exchange_filter"] == "binance"
    assert call_args["product_filter"] is None


@pytest.mark.asyncio
async def test_get_active_filters_count():
    state = AsyncMock()
    state.get_data.return_value = {
        "product_filter": "BTC",
        "exchange_filter": "binance",
        "type_filter": None,
        "apy_min": 5.0,
    }

    count = await FilterStateManager.get_active_filters_count(state)

    # product + exchange + apy_min = 3
    assert count == 3


@pytest.mark.asyncio
async def test_get_filters_display():
    state = AsyncMock()
    state.get_data.return_value = {
        "product_filter": "BTC",
        "exchange_filter": "binance",
        "type_filter": "flexible",
        "apy_min": 5.0,
        "apy_max": 10.0,
        "sort_by": "popularity",
    }

    display = await FilterStateManager.get_filters_display(state, lang="ua")

    assert "🪙 BTC" in display
    assert "🏦 Binance" in display
    assert "Flexible" in display
    assert "від 5.0%" in display
    assert "до 10.0%" in display
    assert "⭐ Популярність" in display


@pytest.mark.asyncio
async def test_navigation_history():
    state = AsyncMock()
    state.get_data.return_value = {"navigation_history": []}

    await FilterStateManager.save_navigation_state(state, "exchange_products", provider="binance")

    call_args = state.update_data.call_args[1]
    assert call_args["current_page"] == "exchange_products"
    assert "provider" in call_args
    assert len(call_args["navigation_history"]) == 1


@pytest.mark.asyncio
async def test_get_previous_page():
    state = AsyncMock()
    state.get_data.return_value = {
        "navigation_history": [
            {"page": "main_menu"},
            {"page": "exchange_products", "provider": "binance"},
        ]
    }

    previous = await FilterStateManager.get_previous_page(state)

    assert previous["page"] == "main_menu"
    state.update_data.assert_called_once()
