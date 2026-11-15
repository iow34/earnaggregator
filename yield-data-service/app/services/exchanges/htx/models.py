from pydantic import BaseModel, Field
from typing import Optional


class HTXFlexibleProduct(BaseModel):
    productId: str = Field(..., description="Productid")
    currency: str = Field(..., description="Currency")
    apr: str = Field(..., description="Apr")
    minPurchaseAmount: str = Field(..., description="Minpurchaseamount")
    maxPurchaseAmount: Optional[str] = Field(None, description="Maxpurchaseamount")
    status: str = Field(..., description="Status")
    type: str = Field(..., description="Type")
    term: str = Field(..., description="Term")
    redeemType: Optional[str] = Field(None, description="Redeemtype")


class HTXFixedProduct(BaseModel):
    productId: str = Field(..., description="Productid")
    currency: str = Field(..., description="Currency")
    apr: str = Field(..., description="Apr")
    minPurchaseAmount: str = Field(..., description="Minpurchaseamount")
    maxPurchaseAmount: Optional[str] = Field(None, description="Maxpurchaseamount")
    status: str = Field(..., description="Status")
    type: str = Field(..., description="Type")
    term: str = Field(..., description="Term")
    redeemType: Optional[str] = Field(None, description="Redeemtype")
