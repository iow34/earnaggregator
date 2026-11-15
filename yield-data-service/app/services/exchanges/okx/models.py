from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class OKXInvestData(BaseModel):
    ccy: str = Field(..., description="Ccy")
    bal: str = Field(default="", description="Bal")
    min_amt: str = Field(default="0", description="Min amt", alias="minAmt")
    max_amt: str = Field(default="", description="Max amt", alias="maxAmt")

    class Config:
        populate_by_name = True


class OKXOnChainProduct(BaseModel):
    product_id: str = Field(..., description="Product id", alias="productId")
    ccy: str = Field(..., description="Ccy")
    protocol: str = Field(..., description="Protocol")
    protocol_type: str = Field(..., description="Protocol type", alias="protocolType")
    term: str = Field(default="", description="Term")
    apy: str = Field(..., description="Apy")
    early_redeem: bool = Field(default=False, description="Early redeem", alias="earlyRedeem")
    state: str = Field(..., description="State")
    invest_data: Optional[List[OKXInvestData]] = Field(
        default=None, description="Invest data", alias="investData"
    )

    class Config:
        populate_by_name = True


class OKXSimpleEarnProduct(BaseModel):
    ccy: str = Field(..., description="Ccy")
    rate: str = Field(..., description="Rate")
    min_amt: str = Field(default="0", description="Min amt", alias="minAmt")
    max_amt: str = Field(default="", description="Max amt", alias="maxAmt")
    auto_renew: bool = Field(default=False, description="Auto renew", alias="autoRenew")
    status: str = Field(..., description="Status")

    class Config:
        populate_by_name = True


class OKXUnifiedProduct(BaseModel):
    id: str = Field(..., description="Id")
    symbol: str = Field(..., description="Symbol")
    name: str = Field(..., description="Name")
    provider: str = Field(default="OKX", description="Provider")
    apy: float = Field(..., description="Apy")
    min_amount: Optional[float] = Field(default=None, description="Min amount")
    max_amount: Optional[float] = Field(default=None, description="Max amount")
    lock_period_days: int = Field(default=0, description="Lock period days")
    product_type: str = Field(..., description="Product type")
    is_active: bool = Field(default=True, description="Is active")
    risk_level: str = Field(default="Low", description="Risk level")
    can_early_redeem: bool = Field(default=False, description="Can early redeem")
    protocol: Optional[str] = Field(default=None, description="Protocol")
    description: Optional[str] = Field(default=None, description="Description")
    website_url: Optional[str] = Field(default=None, description="Website url")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw data")

    class Config:
        populate_by_name = True


class OKXAPIResponse(BaseModel):
    code: str = Field(..., description="Code")
    msg: str = Field(default="", description="Msg")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Data")

    def is_success(self) -> bool:
        return self.code == "0"
