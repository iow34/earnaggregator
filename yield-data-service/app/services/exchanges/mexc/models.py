"""
Pydantic моделі для MEXC API та manual import.

Моделі включають:
- API відповіді від MEXC earn products endpoint
- Моделі для ручного імпорту (deprecated, для сумісності)
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# === API Response Models ===

class TieredSubsidyApr(BaseModel):
    """
    Модель для tiered APR (залежно від суми).
    """
    startQuantity: str = Field(..., description="Початкова кількість")
    endQuantity: Optional[str] = Field(default=None, description="Кінцева кількість (null для необмеженого)")
    apr: str = Field(..., description="APR для цього діапазону")


class FinancialProduct(BaseModel):
    """
    Модель для окремого фінансового продукту з API.
    """
    financialId: str = Field(..., description="Унікальний ID продукту")
    financialType: str = Field(..., description="Тип продукту (FIXED або FLEXIBLE)")
    investPeriodType: str = Field(..., description="Тип періоду інвестування")
    fixedInvestPeriodType: Optional[int] = Field(default=None, description="Тип фіксованого періоду")
    fixedInvestPeriodCount: Optional[int] = Field(default=None, description="Кількість днів для FIXED продукту")
    currencyId: str = Field(..., description="ID валюти")
    currency: str = Field(..., description="Символ валюти (USDT, BTC, etc.)")
    currencyIcon: str = Field(..., description="Іконка валюти")
    showApr: str = Field(..., description="APR для відображення")
    showAprMaxTip: bool = Field(default=False, description="Чи показувати max tip")
    subsidyTieredFlag: bool = Field(default=False, description="Чи є tiered subsidy")
    baseApr: str = Field(..., description="Базовий APR")
    subsidyApr: str = Field(..., description="Subsidy APR")
    tieredSubsidyApr: Optional[List[TieredSubsidyApr]] = Field(default=None, description="Масив tiered APR")
    financialState: int = Field(..., description="Стан продукту (2 = активний)")
    startTime: Optional[int] = Field(default=None, description="Час початку (timestamp)")
    endTime: Optional[int] = Field(default=None, description="Час закінчення (timestamp)")
    soldOut: bool = Field(default=False, description="Чи розпродано")
    sort: int = Field(..., description="Порядок сортування")
    memberType: str = Field(..., description="Тип учасника")
    profitCurrency: Optional[str] = Field(default=None, description="Валюта прибутку")
    profitCurrencyId: Optional[str] = Field(default=None, description="ID валюти прибутку")
    profitCurrencyIcon: Optional[str] = Field(default=None, description="Іконка валюти прибутку")


class CurrencyResult(BaseModel):
    """
    Модель для результатів по одній валюті.
    """
    currencyId: str = Field(..., description="ID валюти")
    currency: str = Field(..., description="Символ валюти")
    currencyIcon: str = Field(..., description="Іконка валюти")
    minApr: str = Field(..., description="Мінімальний APR")
    maxApr: str = Field(..., description="Максимальний APR")
    hasAprRange: bool = Field(default=False, description="Чи є діапазон APR")
    investPeriodTypes: List[str] = Field(..., description="Доступні типи періодів")
    financialProductList: List[FinancialProduct] = Field(..., description="Список фінансових продуктів")
    sort: int = Field(..., description="Порядок сортування")


class MEXCEarnAPIResponse(BaseModel):
    """
    Модель для повної відповіді MEXC Earn API.
    """
    model_config = ConfigDict(strict=False)

    code: int = Field(..., description="Код відповіді (0 = успіх)")
    msg: str = Field(..., description="Повідомлення")
    timestamp: int = Field(..., description="Timestamp відповіді")
    data: Dict[str, Any] = Field(..., description="Дані відповіді")

    @property
    def is_success(self) -> bool:
        """Перевіряє чи успішна відповідь."""
        return self.code == 0

    @property
    def result(self) -> List[CurrencyResult]:
        """Отримує список результатів по валютах."""
        return [CurrencyResult(**item) for item in self.data.get("result", [])]

    @property
    def total(self) -> int:
        """Загальна кількість."""
        return self.data.get("total", 0)

    @property
    def page(self) -> int:
        """Поточна сторінка."""
        return self.data.get("page", 1)

    @property
    def page_size(self) -> int:
        """Розмір сторінки."""
        return self.data.get("pageSize", 100)

    @property
    def total_pages(self) -> int:
        """Загальна кількість сторінок."""
        return self.data.get("totalPage", 1)


# === Manual Import Models (Deprecated) ===

class MEXCManualProduct(BaseModel):
    """
    Модель для одного продукту MEXC при ручному імпорті.

    DEPRECATED: Використовується тільки для сумісності.
    Нові імпорти повинні використовувати API.

    Attributes:
        product_type: Тип продукту (Flexible або Locked)
        symbol: Символ токену (BTC, ETH, USDT, etc.)
        apy: Річна відсоткова дохідність
        min_amount: Мінімальна сума для участі
        max_amount: Максимальна сума (null якщо без ліміту)
        lock_period_days: Період блокування (0 для Flexible)
        status: Статус продукту (active або inactive)
    """

    product_type: str = Field(..., description="Flexible або Locked")
    symbol: str = Field(..., description="Символ токену")
    apy: float = Field(..., description="Річна відсоткова дохідність")
    min_amount: Optional[float] = Field(default=None, description="Мінімальна сума")
    max_amount: Optional[float] = Field(default=None, description="Максимальна сума")
    lock_period_days: int = Field(default=0, description="0 для Flexible, >0 для Locked")
    status: str = Field(..., description="active або inactive")


class MEXCManualImport(BaseModel):
    """
    Модель для імпорту MEXC продуктів з JSON файлу.

    DEPRECATED: Використовується тільки для сумісності.
    Нові імпорти повинні використовувати API.

    Attributes:
        exchange: Назва біржі (має бути 'MEXC')
        updated_at: Timestamp останнього оновлення даних
        products: Список продуктів для імпорту
    """

    exchange: str = Field(..., description="Має бути 'MEXC'")
    updated_at: datetime = Field(..., description="Timestamp оновлення")
    products: List[MEXCManualProduct] = Field(..., description="Список продуктів")

