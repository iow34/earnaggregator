"""
Pydantic моделі для Yield продуктів.

Цей модуль визначає структуру даних для Yield продуктів
з валідацією та серіалізацією.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from app.utils.logger import logger


class RiskLevel(str, Enum):
    """Рівні ризику для Yield продуктів."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class YieldProduct(BaseModel):
    """
    Основна модель Yield продукту.
    
    Визначає структуру даних для Yield продуктів з валідацією.
    """
    
    # Основні поля
    id: str = Field(..., description="Унікальний ідентифікатор продукту")
    symbol: str = Field(..., min_length=2, max_length=10, description="Символ токену (BTC, ETH)")
    name: str = Field(..., min_length=1, max_length=200, description="Назва продукту")
    provider: str = Field(..., min_length=1, max_length=50, description="Провайдер (Binance, Bybit)")
    apy: float = Field(..., ge=0, le=1000, description="APY у відсотках")
    is_cefi: bool = Field(default=True, description="CeFi чи DeFi")
    
    # Фінансові параметри
    min_amount: float = Field(default=0.0, ge=0, description="Мінімальна сума")
    max_amount: Optional[float] = Field(default=None, ge=0, description="Максимальна сума")
    lock_period_days: int = Field(default=0, ge=0, description="Період блокування в днях")
    
    # Додаткові поля
    max_apy: Optional[float] = Field(default=None, ge=0, le=1000, description="Максимальний APY")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Рівень ризику")
    is_active: bool = Field(default=True, description="Активний продукт")
    website_url: Optional[str] = Field(default=None, max_length=500, description="Посилання на платформу")
    description: Optional[str] = Field(default=None, description="Опис продукту")
    product_type: Optional[str] = Field(default=None, description="Тип продукту (Flexible, Fixed, Bonded)")
    
    # Метадані
    created_at: Optional[datetime] = Field(default=None, description="Час створення")
    updated_at: Optional[datetime] = Field(default=None, description="Час оновлення")
    last_checked: Optional[datetime] = Field(default=None, description="Час останньої перевірки")
    
    # Сирі дані
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Сирі дані з API")
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Валідація символу токену."""
        if not isinstance(v, str):
            raise ValueError('Символ має бути строкою')

        original_v = v
        if not v.isupper():
            v = v.upper()

        # Дозволяємо літери, цифри, дефіси, підкреслення та двокрапки
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:')
        if not all(c in allowed_chars for c in v):
            # Замість падіння, очищуємо символ від недозволених символів
            cleaned = ''.join(c for c in v if c in allowed_chars)
            if not cleaned:
                raise ValueError(f'Символ "{original_v}" не містить валідних символів')
            logger.warning(f"⚠️ Очищено символ '{original_v}' -> '{cleaned}'")
            v = cleaned

        result = v.strip()
        if not result:
            raise ValueError(f'Символ "{original_v}" став порожнім після очищення')

        return result
    
    @field_validator('apy')
    @classmethod
    def validate_apy(cls, v):
        """Валідація APY."""
        if v > 1000:
            raise ValueError('APY не може перевищувати 1000%')
        if v < 0:
            raise ValueError('APY не може бути від\'ємним')
        # Зберігаємо точність до 4 знаків після коми, але не округлюємо агресивно
        return round(v, 4)
    
    @field_validator('max_apy')
    @classmethod
    def validate_max_apy(cls, v, info):
        """Валідація максимального APY з автоматичним виправленням."""
        if v is not None:
            if v > 1000:
                raise ValueError('Максимальний APY не може перевищувати 1000%')
            # Якщо max_apy менше за apy - автоматично виправляємо
            if hasattr(info, 'data') and 'apy' in info.data and v < info.data['apy']:
                logger.warning(f"⚠️ Виправлено max_apy {v} -> {info.data['apy']} для продукту {info.data.get('name', 'unknown')}")
                return info.data['apy']
        return v
    
    @field_validator('min_amount')
    @classmethod
    def validate_min_amount(cls, v):
        """Валідація мінімальної суми."""
        if v < 0:
            raise ValueError('Мінімальна сума не може бути від\'ємною')
        return round(v, 8)  # 8 знаків після коми для криптовалют
    
    @field_validator('max_amount')
    @classmethod
    def validate_max_amount(cls, v, info):
        """Валідація максимальної суми."""
        if v is not None:
            if v < 0:
                raise ValueError('Максимальна сума не може бути від\'ємною')
            if hasattr(info, 'data') and 'min_amount' in info.data and v < info.data['min_amount']:
                raise ValueError('Максимальна сума не може бути меншою за мінімальну')
        return v
    
    @field_validator('lock_period_days')
    @classmethod
    def validate_lock_period(cls, v):
        """Валідація періоду блокування."""
        if v < 0:
            raise ValueError('Період блокування не може бути від\'ємним')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертує модель в словник."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'YieldProduct':
        """Створює модель зі словника."""
        return cls(**data)
    
    def is_flexible(self) -> bool:
        """Перевіряє чи продукт гнучкий (без блокування)."""
        return self.lock_period_days == 0
    
    def is_high_yield(self, threshold: float = 10.0) -> bool:
        """Перевіряє чи продукт має високий APY."""
        return self.apy >= threshold
    
    def get_effective_apy(self) -> float:
        """Повертає ефективний APY (максимальний або поточний)."""
        return self.max_apy if self.max_apy else self.apy


class YieldProductCreate(BaseModel):
    """Модель для створення нового Yield продукту."""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    provider: str = Field(..., min_length=1, max_length=50)
    apy: float = Field(..., ge=0, le=1000)
    is_cefi: bool = Field(default=True)
    min_amount: float = Field(default=0.0, ge=0)
    max_amount: Optional[float] = Field(default=None, ge=0)
    lock_period_days: int = Field(default=0, ge=0)
    max_apy: Optional[float] = Field(default=None, ge=0, le=1000)
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    is_active: bool = Field(default=True)
    website_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class YieldProductUpdate(BaseModel):
    """Модель для оновлення Yield продукту."""
    
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    apy: Optional[float] = Field(default=None, ge=0, le=1000)
    is_cefi: Optional[bool] = Field(default=None)
    min_amount: Optional[float] = Field(default=None, ge=0)
    max_amount: Optional[float] = Field(default=None, ge=0)
    lock_period_days: Optional[int] = Field(default=None, ge=0)
    max_apy: Optional[float] = Field(default=None, ge=0, le=1000)
    risk_level: Optional[RiskLevel] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    website_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None)
    product_type: Optional[str] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class YieldProductFilter(BaseModel):
    """Модель для фільтрації Yield продуктів."""
    
    symbol: Optional[str] = Field(default=None, description="Фільтр по символу")
    provider: Optional[str] = Field(default=None, description="Фільтр по провайдеру")
    min_apy: Optional[float] = Field(default=None, ge=0, description="Мінімальний APY")
    max_apy: Optional[float] = Field(default=None, ge=0, description="Максимальний APY")
    is_cefi: Optional[bool] = Field(default=None, description="Фільтр CeFi/DeFi")
    is_active: Optional[bool] = Field(default=True, description="Тільки активні")
    risk_level: Optional[RiskLevel] = Field(default=None, description="Рівень ризику")
    min_amount: Optional[float] = Field(default=None, ge=0, description="Мінімальна сума")
    max_amount: Optional[float] = Field(default=None, ge=0, description="Максимальна сума")
    lock_period_days: Optional[int] = Field(default=None, ge=0, description="Період блокування")
    
    def to_sql_filters(self) -> Dict[str, Any]:
        """Конвертує фільтри в SQL умови."""
        filters = {}
        
        if self.symbol:
            filters['symbol'] = self.symbol.upper()
        if self.provider:
            filters['provider'] = self.provider
        if self.min_apy is not None:
            filters['apy__gte'] = self.min_apy
        if self.max_apy is not None:
            filters['apy__lte'] = self.max_apy
        if self.is_cefi is not None:
            filters['is_cefi'] = self.is_cefi
        if self.is_active is not None:
            filters['is_active'] = self.is_active
        if self.risk_level:
            filters['risk_level'] = self.risk_level
        if self.min_amount is not None:
            filters['min_amount__gte'] = self.min_amount
        if self.max_amount is not None:
            filters['max_amount__lte'] = self.max_amount
        if self.lock_period_days is not None:
            filters['lock_period_days'] = self.lock_period_days
            
        return filters
