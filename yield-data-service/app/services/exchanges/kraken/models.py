"""
Pydantic моделі для Kraken API відповідей.

Моделі для валідації структури даних, що повертаються з Kraken API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class KrakenStrategy(BaseModel):
    """Модель для Kraken Earn стратегії (flexible або bonded)."""
    
    id: str = Field(..., description="ID стратегії")
    asset: str = Field(..., description="Символ активу (ETH, BTC, тощо)")
    lock_type: str = Field(..., description="Тип блокування: flexible або bonded")
    rate: str = Field(..., description="APY як string (наприклад '0.04' для 4%)")
    rate_type: Optional[str] = Field(None, description="fixed або variable")
    duration: Optional[str] = Field(None, description="Тривалість для bonded (днів)")
    min_amount: str = Field(..., description="Мінімальна сума як string")
    max_amount: Optional[str] = Field(None, description="Максимальна сума або 'unlimited'")
    can_allocate: bool = Field(..., description="Чи доступна стратегія для алокації")
    allocation_restriction_info: Optional[Dict[str, Any]] = Field(None, description="Інформація про обмеження")
    
    class Config:
        extra = "allow"  # Дозволяємо додаткові поля


class KrakenStrategiesResponse(BaseModel):
    """Модель для відповіді з списком стратегій."""
    
    strategies: List[KrakenStrategy] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(None, description="Cursor для наступної сторінки")
    
    class Config:
        extra = "allow"


class KrakenAPIResponse(BaseModel):
    """Базова модель для API відповіді Kraken."""
    
    error: List[str] = Field(default_factory=list, description="Помилки API")
    result: Optional[Dict[str, Any]] = Field(None, description="Результат запиту")
    
    class Config:
        extra = "allow"

