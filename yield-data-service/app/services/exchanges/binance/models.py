"""
Специфічні моделі для Binance інтеграції.

Цей модуль містить моделі та типи даних,
специфічні для роботи з Binance API.
"""

from typing import Optional
from pydantic import BaseModel


class BinanceProductConfig(BaseModel):
    """
    Конфігурація продукту Binance.
    """
    product_id: str
    asset: str
    can_purchase: bool
    min_purchase_amount: Optional[float] = None
    status: Optional[str] = None


class BinanceFlexibleProduct(BaseModel):
    """
    Модель для Flexible продуктів Binance.
    """
    product_id: str
    asset: str
    latest_annual_percentage_rate: float
    can_purchase: bool
    min_purchase_amount: Optional[float] = None
    asset_description: Optional[str] = None


class BinanceLockedProduct(BaseModel):
    """
    Модель для Locked продуктів Binance.
    """
    project_id: str
    asset: str
    apr: float
    duration: int
    status: str
    quota: Optional[dict] = None
