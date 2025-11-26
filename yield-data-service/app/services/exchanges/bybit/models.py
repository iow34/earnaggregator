"""
Специфічні моделі для Bybit інтеграції.

Цей модуль містить моделі та типи даних,
специфічні для роботи з Bybit API.
"""

from typing import Optional
from pydantic import BaseModel


class BybitProductConfig(BaseModel):
    """
    Конфігурація продукту Bybit.
    """
    product_id: str
    coin: str
    estimate_apr: str
    status: str
    min_stake_amount: Optional[float] = None
    max_stake_amount: Optional[float] = None
    duration: Optional[str] = None
    term: Optional[int] = None
    category: str


class BybitFlexibleSavingProduct(BaseModel):
    """
    Модель для FlexibleSaving продуктів Bybit.
    """
    product_id: str
    coin: str
    estimate_apr: str
    status: str
    min_stake_amount: Optional[float] = None
    max_stake_amount: Optional[float] = None
    duration: Optional[str] = None  # Зазвичай пусте для FlexibleSaving


class BybitOnChainProduct(BaseModel):
    """
    Модель для OnChain продуктів Bybit.
    """
    product_id: str
    coin: str
    estimate_apr: str
    status: str
    min_stake_amount: Optional[float] = None
    max_stake_amount: Optional[float] = None
    duration: str  # "Flexible" або "Fixed"
    term: Optional[int] = None
