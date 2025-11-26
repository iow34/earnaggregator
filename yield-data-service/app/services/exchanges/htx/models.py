"""
Pydantic моделі для HTX API відповідей.

Моделі для валідації та типізації даних, що повертаються HTX API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class HTXFlexibleProduct(BaseModel):
    """Модель для Flexible Savings продуктів HTX."""
    
    productId: str = Field(..., description="Унікальний ідентифікатор продукту")
    currency: str = Field(..., description="Символ криптовалюти")
    apr: str = Field(..., description="Річна відсоткова ставка (як string)")
    minPurchaseAmount: str = Field(..., description="Мінімальна сума для покупки")
    maxPurchaseAmount: Optional[str] = Field(None, description="Максимальна сума для покупки")
    status: str = Field(..., description="Статус продукту (ONLINE/OFFLINE)")
    type: str = Field(..., description="Тип продукту (FLEXIBLE)")
    term: str = Field(..., description="Термін блокування (0 для Flexible)")
    redeemType: Optional[str] = Field(None, description="Тип вилучення (IMMEDIATE/NEXT_DAY)")


class HTXFixedProduct(BaseModel):
    """Модель для Fixed Savings продуктів HTX."""
    
    productId: str = Field(..., description="Унікальний ідентифікатор продукту")
    currency: str = Field(..., description="Символ криптовалюти")
    apr: str = Field(..., description="Річна відсоткова ставка (як string)")
    minPurchaseAmount: str = Field(..., description="Мінімальна сума для покупки")
    maxPurchaseAmount: Optional[str] = Field(None, description="Максимальна сума для покупки")
    status: str = Field(..., description="Статус продукту (ONLINE/OFFLINE)")
    type: str = Field(..., description="Тип продукту (FIXED)")
    term: str = Field(..., description="Термін блокування в днях")
    redeemType: Optional[str] = Field(None, description="Тип вилучення")

