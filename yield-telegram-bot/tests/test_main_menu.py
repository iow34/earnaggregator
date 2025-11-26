"""
Тести для головного меню бота.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.main_menu import (
    show_main_menu,
    _format_top_10_section,
    _format_exchanges_quick_view,
    _format_single_exchange_preview,
    _get_referral_url
)


def test_get_referral_url():
    """Тест отримання реферальних посилань."""
    # Відомі біржі
    assert _get_referral_url("binance") == "https://accounts.binance.com/register?ref=YOUR_REF"
    assert _get_referral_url("bybit") == "https://www.bybit.com/invite?ref=YOUR_REF"
    assert _get_referral_url("nexo") == "https://nexo.com/ref/YOUR_REF"

    # Невідома біржа
    assert _get_referral_url("unknown") == "#"

    # Case insensitive
    assert _get_referral_url("BINANCE") == "https://accounts.binance.com/register?ref=YOUR_REF"


@pytest.mark.asyncio
async def test_format_top_10_section_success():
    """Тест форматування топ 10 секції з успішними даними."""
    # Mock API client
    api_client = AsyncMock()
    api_client.get_top.return_value = {
        "success": True,
        "data": {
            "binance": [
                {
                    "symbol": "BTC",
                    "provider": "binance",
                    "apy": 5.2,
                    "lock_period_days": 0
                },
                {
                    "symbol": "ETH",
                    "provider": "binance",
                    "apy": 4.8,
                    "lock_period_days": 30
                }
            ],
            "bybit": [
                {
                    "symbol": "BTC",
                    "provider": "bybit",
                    "apy": 6.1,
                    "lock_period_days": 0
                }
            ]
        }
    }

    result = await _format_top_10_section(api_client)

    # Перевірити що API було викликано
    api_client.get_top.assert_called_once_with(limit=10)

    # Перевірити що результат містить очікувані елементи
    assert "🔥 <b>ТОП 10 за APY</b>" in result
    assert "BTC" in result
    assert "ETH" in result
    assert "binance" in result
    assert "bybit" in result
    assert "5.2%" in result
    assert "6.1%" in result
    assert "<pre>" in result
    assert "</pre>" in result


@pytest.mark.asyncio
async def test_format_top_10_section_error():
    """Тест форматування топ 10 секції з помилкою."""
    # Mock API client з помилкою
    api_client = AsyncMock()
    api_client.get_top.return_value = {"success": False}

    result = await _format_top_10_section(api_client)

    assert "📊 <b>Топ продукти недоступні</b>" in result


@pytest.mark.asyncio
async def test_format_exchanges_quick_view():
    """Тест форматування огляду по біржам."""
    # Mock API client з відповідями для обох бірж
    api_client = AsyncMock()

    # Mock для Binance
    api_client.get_exchanges.side_effect = [
        {  # Binance
            "success": True,
            "data": [
                {"symbol": "BTC", "apy": 5.2, "lock_period_days": 0},
                {"symbol": "ETH", "apy": 4.8, "lock_period_days": 30},
                {"symbol": "SOL", "apy": 6.1, "lock_period_days": 0},
                {"symbol": "USDT", "apy": 4.5, "lock_period_days": 15}
            ]
        },
        {  # Bybit
            "success": True,
            "data": [
                {"symbol": "BTC", "apy": 4.9, "lock_period_days": 0},
                {"symbol": "ETH", "apy": 5.1, "lock_period_days": 45},
                {"symbol": "SOL", "apy": 5.8, "lock_period_days": 0},
                {"symbol": "USDT", "apy": 4.2, "lock_period_days": 30}
            ]
        }
    ]

    text = await _format_exchanges_quick_view(api_client)

    assert "🏦 <b>Огляд по біржам</b>" in text
    assert "<b>Binance</b>" in text
    assert "<b>Bybit</b>" in text
    assert "BTC 5.2%" in text
    assert "ETH 4.8%" in text
    assert "SOL 6.1%" in text
    assert "USDT 4.5%" in text
    assert "<a href=" in text  # Перевірка HTML посилань
    assert "/all binance products" in text  # Перевірка команд

    # Перевірка викликів API
    assert api_client.get_exchanges.call_count == 2
    api_client.get_exchanges.assert_any_call(exchange="binance", limit=100)
    api_client.get_exchanges.assert_any_call(exchange="bybit", limit=100)


@pytest.mark.asyncio
async def test_show_main_menu():
    """Тест відображення головного меню."""
    # Mock message та state
    message = AsyncMock()
    state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()

    # Mock API client
    api_client_mock = AsyncMock()
    api_client_mock.get_top.return_value = {
        "success": True,
        "data": {
            "binance": [
                {
                    "symbol": "BTC",
                    "provider": "binance",
                    "apy": 5.2,
                    "lock_period_days": 0
                }
            ]
        }
    }
    api_client_mock.close = AsyncMock()

    # Mock імпорт для тестування
    import bot.handlers.main_menu as main_menu_module
    original_api_client = main_menu_module.APIClient

    # Замінити на mock
    main_menu_module.APIClient = lambda: api_client_mock

    try:
        await show_main_menu(message, state)

        # Перевірити що state було очищено
        state.clear.assert_called_once()

        # Перевірити що update_data було викликано
        state.update_data.assert_called_once_with(current_page="main_menu")

        # Перевірити що message.answer було викликано
        message.answer.assert_called_once()

        # Перевірити що API було викликано
        api_client_mock.get_top.assert_called_once_with(limit=10)
        api_client_mock.close.assert_called_once()

    finally:
        # Відновити оригінальний клас
        main_menu_module.APIClient = original_api_client


@pytest.mark.asyncio
async def test_show_main_menu_error():
    """Тест відображення головного меню з помилкою."""
    # Mock message та state
    message = AsyncMock()
    state = AsyncMock()

    # Mock API client з помилкою
    api_client_mock = AsyncMock()
    api_client_mock.close = AsyncMock()
    api_client_mock.get_top.side_effect = Exception("API Error")

    # Mock імпорт
    import bot.handlers.main_menu as main_menu_module
    original_api_client = main_menu_module.APIClient
    main_menu_module.APIClient = lambda: api_client_mock

    try:
        await show_main_menu(message, state)

        # Перевірити що було надіслано повідомлення про помилку
        message.answer.assert_called_once()
        call_args = message.answer.call_args[1]
        assert "❌ Помилка завантаження даних" in call_args["text"]

    finally:
        # Відновити оригінальний клас
        main_menu_module.APIClient = original_api_client


@pytest.mark.asyncio
async def test_format_single_exchange_preview_success():
    """Тест успішного форматування біржі з пріоритетними продуктами."""
    # Mock API client
    api_client_mock = AsyncMock()
    api_client_mock.get_exchanges.return_value = {
        "success": True,
        "data": [
            {"symbol": "BTC", "apy": 3.25, "lock_period_days": 0},
            {"symbol": "ETH", "apy": 5.85, "lock_period_days": 30},
            {"symbol": "SOL", "apy": 4.15, "lock_period_days": 0},
            {"symbol": "USDT", "apy": 4.25, "lock_period_days": 15},
            {"symbol": "ADA", "apy": 2.1, "lock_period_days": 0},  # Не пріоритетний
        ]
    }

    # Виклик функції
    text = await _format_single_exchange_preview(api_client_mock, "binance")

    # Перевірки тексту
    assert "Binance" in text
    assert "BTC 3.2%" in text
    assert "ETH 5.8%" in text
    assert "SOL 4.2%" in text
    assert "USDT 4.2%" in text
    assert "📊 BTC 3.2% • ETH 5.8% • SOL 4.2% • USDT 4.2%" in text
    assert "<a href=" in text  # Перевірка HTML посилання
    assert "/all binance products" in text  # Перевірка команди

    # Перевірити що API було викликано з правильними параметрами
    api_client_mock.get_exchanges.assert_called_once_with(exchange="binance", limit=100)


@pytest.mark.asyncio
async def test_format_single_exchange_preview_no_data():
    """Тест форматування біржі без даних."""
    # Mock API client з порожніми даними
    api_client_mock = AsyncMock()
    api_client_mock.get_exchanges.return_value = {
        "success": True,
        "data": []
    }

    text = await _format_single_exchange_preview(api_client_mock, "bybit")

    assert text == "<b>Bybit</b>: немає даних"


@pytest.mark.asyncio
async def test_format_single_exchange_preview_api_error():
    """Тест форматування біржі з помилкою API."""
    # Mock API client з помилкою
    api_client_mock = AsyncMock()
    api_client_mock.get_exchanges.return_value = {
        "success": False
    }

    text = await _format_single_exchange_preview(api_client_mock, "binance")

    assert text == "<b>Binance</b>: дані недоступні"


@pytest.mark.asyncio
async def test_format_single_exchange_preview_partial_data():
    """Тест форматування біржі з неповними даними (менше 4 продуктів)."""
    # Mock API client з неповними даними
    api_client_mock = AsyncMock()
    api_client_mock.get_exchanges.return_value = {
        "success": True,
        "data": [
            {"symbol": "BTC", "apy": 3.25, "lock_period_days": 0},
            {"symbol": "ETH", "apy": 5.85, "lock_period_days": 30},
            # SOL і USDT відсутні
        ]
    }

    text = await _format_single_exchange_preview(api_client_mock, "binance")

    assert "BTC 3.2%" in text
    assert "ETH 5.8%" in text
    assert "SOL" not in text  # SOL немає в даних
    assert "USDT" not in text  # USDT немає в даних
