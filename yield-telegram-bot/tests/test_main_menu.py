from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from bot.handlers import main_menu as menu


def test_referral_lookup_uses_configuration():
    assert menu._get_referral_url("BINANCE") == menu.settings.referral_urls["binance"]
    assert menu._get_referral_url("unknown") == "#"


@pytest.mark.asyncio
async def test_trending_section_uses_aggregated_top_products():
    api = AsyncMock()
    api.get_trending_coins.return_value = {
        "success": True,
        "data": {"trending_coins": [{"symbol": "BTC"}]},
    }
    api.get_top_products.return_value = {
        "success": True,
        "data": [{"symbol": "BTC", "best_exchange": "Binance", "best_apy": 4.5, "rank": 1}],
    }
    text = await menu._format_top_10_section(api, "en")
    assert "BTC" in text and "Binance" in text and "4.5" in text
    api.get_top_products.assert_awaited_once_with(limit=10)


@pytest.mark.asyncio
async def test_trending_failure_has_localized_fallback():
    api = AsyncMock()
    api.get_trending_coins.side_effect = RuntimeError("Unavailable")
    text = await menu._format_top_10_section(api, "en")
    assert menu.localization.get_text("error.data_unavailable", "en") in text


@pytest.mark.asyncio
async def test_main_command_cleans_up_loading_indicator():
    message = MagicMock()
    loading = MagicMock(delete=AsyncMock())
    message.answer = AsyncMock(return_value=loading)
    state = AsyncMock()
    state.get_data.return_value = {"lang": "en"}
    with patch.object(menu, "show_main_page", AsyncMock()) as show:
        await menu.main_command_handler(message, state)
        show.assert_awaited_once_with(message, state, "en")
    loading.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_command_handles_render_failure():
    message = MagicMock(answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {"lang": "en"}
    with patch.object(menu, "show_main_page", AsyncMock(side_effect=RuntimeError("Unavailable"))):
        await menu.main_command_handler(message, state)
    assert message.answer.await_count == 2
