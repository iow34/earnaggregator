from typing import Optional, List
from pydantic import BaseModel, Field


class GateUniCurrency(BaseModel):
    currency: str = Field(..., description="Currency")
    min_lend_amount: str = Field(..., description="Min lend amount")
    max_lend_amount: str = Field(default="", description="Max lend amount")
    max_rate: str = Field(..., description="Max rate")
    min_rate: str = Field(..., description="Min rate")


class GateUniRate(BaseModel):
    currency: str = Field(..., description="Currency")
    est_rate: str = Field(..., description="Est rate")


class GateUniCurrencyDetail(BaseModel):
    currency: str
    min_amount: str
    max_amount: str
    rate: str
    rate_list: Optional[List[dict]] = Field(default=None, description="Rate list")
    status: str


class GateFlexibleProduct(BaseModel):
    id: str = Field(..., description="Id")
    symbol: str = Field(..., description="Symbol")
    name: str = Field(..., description="Name")
    provider: str = Field(default="gate", description="Provider")
    apy: float = Field(..., description="Apy")
    min_amount: Optional[float] = Field(default=None, description="Min amount")
    max_amount: Optional[float] = Field(default=None, description="Max amount")
    lock_period_days: int = Field(default=0, description="Lock period days")
    product_type: str = Field(default="Flexible", description="Product type")
    is_active: bool = Field(..., description="Is active")
    risk_level: str = Field(default="Low", description="Risk level")
    description: Optional[str] = Field(default=None, description="Description")
    website_url: Optional[str] = Field(default=None, description="Website url")
    raw_data: Optional[dict] = Field(default=None, description="Raw data")


class GateFixedProduct(BaseModel):
    exchange: str = Field(default="gate", description="Exchange")
    product_type: str = Field(default="Fixed", description="Product type")
    symbol: str = Field(..., description="Symbol")
    apy: float = Field(..., description="Apy")
    min_amount: Optional[float] = Field(default=None, description="Min amount")
    max_amount: Optional[float] = Field(default=None, description="Max amount")
    lock_period_days: int = Field(..., description="Lock period days")
    status: str = Field(default="active", description="Status")
    last_updated: Optional[str] = Field(default=None, description="Last updated")
