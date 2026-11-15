"""
Pydantic models for KuCoin responses (optional helper models).
"""

from typing import Optional
from pydantic import BaseModel, Field


class KuCoinSavingsProduct(BaseModel):
    productId: str = Field(...)
    currency: str = Field(...)
    apr: str = Field(..., description="APR as string, e.g. '0.05' for 5%")
    minAmount: Optional[str] = None
    maxAmount: Optional[str] = None
    remainingAmount: Optional[str] = None
    status: Optional[str] = None
    productType: Optional[str] = None  # FLEXIBLE | FIXED
    term: Optional[str] = None  # days; '0' for flexible
    redeemType: Optional[str] = None
    advanceRedeemSupport: Optional[bool] = None
