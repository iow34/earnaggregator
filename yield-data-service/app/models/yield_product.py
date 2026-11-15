from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from app.utils.logger import logger


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


class YieldProduct(BaseModel):
    id: str = Field(..., description="Id")
    symbol: str = Field(..., min_length=1, max_length=10, description="Symbol")
    name: str = Field(..., min_length=1, max_length=200, description="Name")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider")
    apy: float = Field(..., ge=0, le=1000, description="Apy")
    is_cefi: bool = Field(default=True, description="Is cefi")

    min_amount: float = Field(default=0.0, ge=0, description="Min amount")
    max_amount: Optional[float] = Field(default=None, ge=0, description="Max amount")
    lock_period_days: int = Field(default=0, ge=0, description="Lock period days")

    max_apy: Optional[float] = Field(default=None, ge=0, le=1000, description="Max apy")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM, description="Risk level")
    is_active: bool = Field(default=True, description="Is active")
    website_url: Optional[str] = Field(default=None, max_length=500, description="Website url")
    description: Optional[str] = Field(default=None, description="Description")
    product_type: Optional[str] = Field(default=None, description="Product type")

    created_at: Optional[datetime] = Field(default=None, description="Created at")
    updated_at: Optional[datetime] = Field(default=None, description="Updated at")
    last_checked: Optional[datetime] = Field(default=None, description="Last checked")

    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw data")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        if not isinstance(v, str):
            raise ValueError("Символ має бути строкою")

        original_v = v
        if not v.isupper():
            v = v.upper()

        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:")
        if not all(c in allowed_chars for c in v):
            cleaned = "".join(c for c in v if c in allowed_chars)
            if not cleaned:
                fallback_symbol = f"HTX_{hash(original_v) % 10000}"
                logger.warning(
                    f"⚠️ Символ '{original_v}' не містить валідних символів, використано fallback: '{fallback_symbol}'"
                )
                return fallback_symbol
            logger.warning(f"⚠️ Очищено символ '{original_v}' -> '{cleaned}'")
            v = cleaned

        result = v.strip()
        if not result:
            fallback_symbol = f"HTX_{hash(original_v) % 10000}"
            logger.warning(
                f"⚠️ Символ '{original_v}' став порожнім, використано fallback: '{fallback_symbol}'"
            )
            return fallback_symbol

        return result

    @field_validator("apy")
    @classmethod
    def validate_apy(cls, v):
        if v > 1000:
            raise ValueError("APY не може перевищувати 1000%")
        if v < 0:
            raise ValueError("APY не може бути від'ємним")

        return round(v, 4)

    @field_validator("max_apy")
    @classmethod
    def validate_max_apy(cls, v, info):
        if v is not None:
            if v > 1000:
                raise ValueError("Максимальний APY не може перевищувати 1000%")

            if hasattr(info, "data") and "apy" in info.data and v < info.data["apy"]:
                logger.warning(
                    f"⚠️ Виправлено max_apy {v} -> {info.data['apy']} для продукту {info.data.get('name', 'unknown')}"
                )
                return info.data["apy"]
        return v

    @field_validator("min_amount")
    @classmethod
    def validate_min_amount(cls, v):
        if v < 0:
            raise ValueError("Мінімальна сума не може бути від'ємною")
        return round(v, 8)

    @field_validator("max_amount")
    @classmethod
    def validate_max_amount(cls, v, info):
        if v is not None:
            if v < 0:
                raise ValueError("Максимальна сума не може бути від'ємною")
            if hasattr(info, "data") and "min_amount" in info.data and v < info.data["min_amount"]:
                raise ValueError("Максимальна сума не може бути меншою за мінімальну")
        return v

    @field_validator("lock_period_days")
    @classmethod
    def validate_lock_period(cls, v):
        if v < 0:
            raise ValueError("Період блокування не може бути від'ємним")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YieldProduct":
        return cls(**data)

    def is_flexible(self) -> bool:
        return self.lock_period_days == 0

    def is_high_yield(self, threshold: float = 10.0) -> bool:
        return self.apy >= threshold

    def get_effective_apy(self) -> float:
        return self.max_apy if self.max_apy else self.apy


class YieldProductCreate(BaseModel):
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
    symbol: Optional[str] = Field(default=None, description="Symbol")
    provider: Optional[str] = Field(default=None, description="Provider")
    min_apy: Optional[float] = Field(default=None, ge=0, description="Min apy")
    max_apy: Optional[float] = Field(default=None, ge=0, description="Max apy")
    is_cefi: Optional[bool] = Field(default=None, description="Is cefi")
    is_active: Optional[bool] = Field(default=True, description="Is active")
    risk_level: Optional[RiskLevel] = Field(default=None, description="Risk level")
    min_amount: Optional[float] = Field(default=None, ge=0, description="Min amount")
    max_amount: Optional[float] = Field(default=None, ge=0, description="Max amount")
    lock_period_days: Optional[int] = Field(default=None, ge=0, description="Lock period days")

    def to_sql_filters(self) -> Dict[str, Any]:
        filters = {}

        if self.symbol:
            filters["symbol"] = self.symbol.upper()
        if self.provider:
            filters["provider"] = self.provider
        if self.min_apy is not None:
            filters["apy__gte"] = self.min_apy
        if self.max_apy is not None:
            filters["apy__lte"] = self.max_apy
        if self.is_cefi is not None:
            filters["is_cefi"] = self.is_cefi
        if self.is_active is not None:
            filters["is_active"] = self.is_active
        if self.risk_level:
            filters["risk_level"] = self.risk_level
        if self.min_amount is not None:
            filters["min_amount__gte"] = self.min_amount
        if self.max_amount is not None:
            filters["max_amount__lte"] = self.max_amount
        if self.lock_period_days is not None:
            filters["lock_period_days"] = self.lock_period_days

        return filters
