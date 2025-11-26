"""
Pydantic моделі для Bitget API відповідей.

Структури даних для валідації відповідей від Bitget Savings API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class BitgetAPYTier(BaseModel):
    """Модель для одного tier у ladder APY."""
    rateLevel: int = Field(..., description="Рівень ставки")
    minStepVal: str = Field(..., description="Мінімальна сума для цього tier")
    maxStepVal: str = Field(..., description="Максимальна сума для цього tier")
    currentApy: str = Field(..., description="APY для цього tier")


class BitgetSavingsProduct(BaseModel):
    """Базова модель для Savings продуктів Bitget."""
    productId: str = Field(..., description="ID продукту")
    coin: str = Field(..., description="Символ монети")
    periodType: str = Field(..., description="Тип періоду: flexible або fixed")
    period: str = Field(default="", description="Період блокування (порожнє для flexible)")
    apyType: str = Field(..., description="Тип APY: single або ladder")
    apyList: List[BitgetAPYTier] = Field(default_factory=list, description="Список APY tiers")
    advanceRedeem: str = Field(default="", description="Чи можна достроково вивести")
    settleMethod: str = Field(default="", description="Метод виплати: daily або maturity")
    status: str = Field(..., description="Статус продукту")
    productLevel: str = Field(default="normal", description="Рівень продукту: beginner, normal, VIP")


class BitgetFlexibleProduct(BitgetSavingsProduct):
    """Модель для Flexible продуктів Bitget."""
    periodType: str = Field(default="flexible", description="Завжди flexible")
    period: str = Field(default="", description="Завжди порожнє для flexible")


class BitgetFixedProduct(BitgetSavingsProduct):
    """Модель для Fixed продуктів Bitget."""
    periodType: str = Field(default="fixed", description="Завжди fixed")
    period: str = Field(..., description="Період блокування в днях")

