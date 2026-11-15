from pydantic import BaseModel, Field
from typing import Optional, List


class BitgetAPYTier(BaseModel):
    rateLevel: int = Field(..., description="Ratelevel")
    minStepVal: str = Field(..., description="Minstepval")
    maxStepVal: str = Field(..., description="Maxstepval")
    currentApy: str = Field(..., description="Currentapy")


class BitgetSavingsProduct(BaseModel):
    productId: str = Field(..., description="Productid")
    coin: str = Field(..., description="Coin")
    periodType: str = Field(..., description="Periodtype")
    period: str = Field(default="", description="Period")
    apyType: str = Field(..., description="Apytype")
    apyList: List[BitgetAPYTier] = Field(default_factory=list, description="Apylist")
    advanceRedeem: str = Field(default="", description="Advanceredeem")
    settleMethod: str = Field(default="", description="Settlemethod")
    status: str = Field(..., description="Status")
    productLevel: str = Field(default="normal", description="Productlevel")


class BitgetFlexibleProduct(BitgetSavingsProduct):
    periodType: str = Field(default="flexible", description="Periodtype")
    period: str = Field(default="", description="Period")


class BitgetFixedProduct(BitgetSavingsProduct):
    periodType: str = Field(default="fixed", description="Periodtype")
    period: str = Field(..., description="Period")
