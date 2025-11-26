"""
Pydantic моделі для Gate.io API відповідей.

Цей модуль містить моделі для валідації даних,
отриманих з Gate.io API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class GateUniCurrency(BaseModel):
    """
    Модель для Uni Lend currency з Gate.io API.

    Endpoint: GET /api/v4/earn/uni/currencies
    Цей endpoint НЕ потребує аутентифікації
    """
    currency: str = Field(..., description="Назва криптовалюти")
    min_lend_amount: str = Field(..., description="Мінімальна сума для lending")
    max_lend_amount: str = Field(default="", description="Максимальна сума (порожня = необмежено)")
    max_rate: str = Field(..., description="Максимальна річна відсоткова ставка (десятковий формат)")
    min_rate: str = Field(..., description="Мінімальна річна відсоткова ставка (десятковий формат)")


class GateUniRate(BaseModel):
    """
    Модель для estimated rate з Gate.io API.
    Endpoint: GET /api/v4/earn/uni/rate
    Цей endpoint НЕ потребує аутентифікації
    """
    currency: str = Field(..., description="Назва криптовалюти")
    est_rate: str = Field(..., description="Estimated річна відсоткова ставка (десятковий формат)")


class GateUniCurrencyDetail(BaseModel):
    """
    Детальна модель для конкретної Uni Lend currency.
    
    Endpoint: GET /api/v4/earn/uni/currencies/{currency}
    """
    currency: str
    min_amount: str
    max_amount: str
    rate: str
    rate_list: Optional[List[dict]] = Field(default=None, description="Список ставок по термінам")
    status: str


class GateFlexibleProduct(BaseModel):
    """
    Модель для Flexible продуктів Gate.io після нормалізації.
    """
    id: str = Field(..., description="Унікальний ID продукту")
    symbol: str = Field(..., description="Символ криптовалюти")
    name: str = Field(..., description="Назва продукту")
    provider: str = Field(default="gate", description="Назва біржі")
    apy: float = Field(..., description="Річна відсоткова дохідність")
    min_amount: Optional[float] = Field(default=None, description="Мінімальна сума")
    max_amount: Optional[float] = Field(default=None, description="Максимальна сума")
    lock_period_days: int = Field(default=0, description="Термін блокування (0 для Flexible)")
    product_type: str = Field(default="Flexible", description="Тип продукту")
    is_active: bool = Field(..., description="Чи активний продукт")
    risk_level: str = Field(default="Low", description="Рівень ризику")
    description: Optional[str] = Field(default=None, description="Опис продукту")
    website_url: Optional[str] = Field(default=None, description="Посилання на продукт")
    raw_data: Optional[dict] = Field(default=None, description="Сирі дані з API")


class GateFixedProduct(BaseModel):
    """
    Модель для Fixed продуктів Gate.io (manual import з JSON).
    """
    exchange: str = Field(default="gate", description="Назва біржі")
    product_type: str = Field(default="Fixed", description="Тип продукту")
    symbol: str = Field(..., description="Символ криптовалюти")
    apy: float = Field(..., description="Річна відсоткова дохідність")
    min_amount: Optional[float] = Field(default=None, description="Мінімальна сума")
    max_amount: Optional[float] = Field(default=None, description="Максимальна сума")
    lock_period_days: int = Field(..., description="Термін блокування в днях")
    status: str = Field(default="active", description="Статус продукту")
    last_updated: Optional[str] = Field(default=None, description="Дата останнього оновлення")

