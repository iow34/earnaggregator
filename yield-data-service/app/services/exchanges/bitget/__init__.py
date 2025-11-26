"""
Модуль інтеграції з Bitget API для отримання Earn продуктів.

Bitget надає Savings продукти через endpoint /api/v2/earn/savings/product:
- Flexible Savings (гнучкі заощадження)
- Fixed Savings (фіксовані заощадження з блокуванням)

Особливості аутентифікації:
- API Key + Secret + Passphrase (обов'язково)
- HMAC-SHA256 підпис
- Rate limit: 10 запитів/секунду
"""

from .api import BitgetAPI
from .service import BitgetService

__all__ = [
    "BitgetAPI",
    "BitgetService"
]

