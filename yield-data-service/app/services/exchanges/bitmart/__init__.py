"""
BitMart Exchange Integration.

Модуль містить інтеграцію з BitMart для отримання Earn продуктів через публічний API.

BitMart надає публічний API для Savings/Earn продуктів:
- Дані отримуються автоматично через GET /gw-api/newearn/summary/earn/product/list
- Продукти зберігаються в PostgreSQL з автоматичною синхронізацією
- BitMartService працює з API та кешуванням
- BitMartAPI реалізує запити до BitMart API
"""

from .api import BitMartAPI
from .service import BitMartService
from .models import (
    # API моделі
    BitMartEarnAPIResponse,
    EarnProduct,
    SummaryProductList,
    AddInfo,
    WealthProduct,
    TierRule,
)

__all__ = [
    "BitMartAPI",
    "BitMartService",
    # API моделі
    "BitMartEarnAPIResponse",
    "EarnProduct",
    "SummaryProductList",
    "AddInfo",
    "WealthProduct",
    "TierRule",
]
