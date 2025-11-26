"""
MEXC Exchange Integration (API Mode).

Модуль містить інтеграцію з MEXC для отримання Earn продуктів через публічний API.

MEXC надає публічний API для Savings/Earn продуктів:
- Дані отримуються автоматично через GET /api/financialactivity/financial/products/list
- Продукти зберігаються в PostgreSQL з автоматичною синхронізацією
- MEXCService працює з API та кешуванням
- MEXCAPI реалізує запити до MEXC API
"""

from .api import MEXCAPI
from .service import MEXCService
from .models import (
    # API моделі
    MEXCEarnAPIResponse,
    CurrencyResult,
    FinancialProduct,
    TieredSubsidyApr,
    # Manual моделі (deprecated)
    MEXCManualProduct,
    MEXCManualImport,
)

__all__ = [
    "MEXCAPI",
    "MEXCService",
    # API моделі
    "MEXCEarnAPIResponse",
    "CurrencyResult",
    "FinancialProduct",
    "TieredSubsidyApr",
    # Manual моделі (deprecated)
    "MEXCManualProduct",
    "MEXCManualImport",
]

