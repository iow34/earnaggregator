from typing import Optional
from pydantic import BaseModel


class BinanceProductConfig(BaseModel):
    product_id: str
    asset: str
    can_purchase: bool
    min_purchase_amount: Optional[float] = None
    status: Optional[str] = None


class BinanceFlexibleProduct(BaseModel):
    product_id: str
    asset: str
    latest_annual_percentage_rate: float
    can_purchase: bool
    min_purchase_amount: Optional[float] = None
    asset_description: Optional[str] = None


class BinanceLockedProduct(BaseModel):
    project_id: str
    asset: str
    apr: float
    duration: int
    status: str
    quota: Optional[dict] = None
