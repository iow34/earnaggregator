from typing import Optional
from pydantic import BaseModel


class BybitProductConfig(BaseModel):
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
    product_id: str
    coin: str
    estimate_apr: str
    status: str
    min_stake_amount: Optional[float] = None
    max_stake_amount: Optional[float] = None
    duration: Optional[str] = None


class BybitOnChainProduct(BaseModel):
    product_id: str
    coin: str
    estimate_apr: str
    status: str
    min_stake_amount: Optional[float] = None
    max_stake_amount: Optional[float] = None
    duration: str
    term: Optional[int] = None
