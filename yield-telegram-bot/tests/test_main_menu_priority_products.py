"""
Тести для priority products в головному меню телеграм бота.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.main_menu import _format_single_exchange_preview


@pytest.mark.asyncio
async def test_format_single_exchange_preview_with_priority_products():
    """Тест форматування біржі з використанням priority_products API."""
    api_client = AsyncMock()
    
    # Mock priority_products API
    api_client.get_priority_products.return_value = {
        "success": True,
        "data": [
            {"symbol": "BTC", "apy": 5.5, "is_active": True},
            {"symbol": "ETH", "apy": 4.8, "is_active": True},
            {"symbol": "SOL", "apy": 6.2, "is_active": True},
            {"symbol": "USDT", "apy": 3.6, "is_active": True}
        ]
    }
    
    # Mock referral link generator
    from unittest.mock import patch
    with patch('bot.handlers.main_menu.referral_link_generator') as mock_generator:
        mock_generator.generate_link = AsyncMock(return_value="https://test.com")
        
        result = await _format_single_exchange_preview(
            api_client, "binance", 12345, "ua"
        )
        
        # Перевіряємо що використано priority_products API
        api_client.get_priority_products.assert_called_once_with("binance")
        
        # Перевіряємо що всі 4 продукти виведені в правильному порядку
        assert "BTC 5.5%" in result
        assert "ETH 4.8%" in result
        assert "SOL 6.2%" in result
        assert "USDT 3.6%" in result
        
        # Перевіряємо порядок (BTC має бути перед ETH)
        btc_pos = result.find("BTC")
        eth_pos = result.find("ETH")
        sol_pos = result.find("SOL")
        usdt_pos = result.find("USDT")
        
        assert btc_pos < eth_pos < sol_pos < usdt_pos


@pytest.mark.asyncio
async def test_format_single_exchange_preview_with_zero_apy():
    """Тест форматування біржі з APY=0.0."""
    api_client = AsyncMock()
    
    # Mock priority_products API з APY=0.0
    api_client.get_priority_products.return_value = {
        "success": True,
        "data": [
            {"symbol": "BTC", "apy": 0.0, "is_active": False},
            {"symbol": "ETH", "apy": 0.0, "is_active": False},
            {"symbol": "SOL", "apy": 0.0, "is_active": False},
            {"symbol": "USDT", "apy": 0.0, "is_active": False}
        ]
    }
    
    from unittest.mock import patch
    with patch('bot.handlers.main_menu.referral_link_generator') as mock_generator:
        mock_generator.generate_link = AsyncMock(return_value="https://test.com")
        
        result = await _format_single_exchange_preview(
            api_client, "binance", 12345, "ua"
        )
        
        # Перевіряємо що всі продукти виведені з 0.0%
        assert "BTC 0.0%" in result
        assert "ETH 0.0%" in result
        assert "SOL 0.0%" in result
        assert "USDT 0.0%" in result


@pytest.mark.asyncio
async def test_format_single_exchange_preview_fallback():
    """Тест fallback на старий метод при помилці priority_products API."""
    api_client = AsyncMock()
    
    # Mock priority_products API з помилкою
    api_client.get_priority_products.return_value = {
        "success": False,
        "error": "API недоступний"
    }
    
    # Mock старого методу get_exchanges
    api_client.get_exchanges.return_value = {
        "success": True,
        "data": [
            {"symbol": "BTC", "apy": 5.5, "lock_period_days": 0},
            {"symbol": "ETH", "apy": 4.8, "lock_period_days": 0}
        ]
    }
    
    from unittest.mock import patch
    with patch('bot.handlers.main_menu.referral_link_generator') as mock_generator:
        mock_generator.generate_link = AsyncMock(return_value="https://test.com")
        
        result = await _format_single_exchange_preview(
            api_client, "binance", 12345, "ua"
        )
        
        # Перевіряємо що використано fallback метод
        api_client.get_exchanges.assert_called()
        
        # Перевіряємо що результат містить дані
        assert "Binance" in result or "binance" in result.lower()

