from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# === API Response Models ===


class TieredSubsidyApr(BaseModel):
    startQuantity: str = Field(..., description="Startquantity")
    endQuantity: Optional[str] = Field(default=None, description="Endquantity")
    apr: str = Field(..., description="Apr")


class FinancialProduct(BaseModel):
    financialId: str = Field(..., description="Financialid")
    financialType: str = Field(..., description="Financialtype")
    investPeriodType: str = Field(..., description="Investperiodtype")
    fixedInvestPeriodType: Optional[int] = Field(default=None, description="Fixedinvestperiodtype")
    fixedInvestPeriodCount: Optional[int] = Field(
        default=None, description="Fixedinvestperiodcount"
    )
    currencyId: str = Field(..., description="Currencyid")
    currency: str = Field(..., description="Currency")
    currencyIcon: str = Field(..., description="Currencyicon")
    showApr: str = Field(..., description="Showapr")
    showAprMaxTip: bool = Field(default=False, description="Showaprmaxtip")
    subsidyTieredFlag: bool = Field(default=False, description="Subsidytieredflag")
    baseApr: str = Field(..., description="Baseapr")
    subsidyApr: str = Field(..., description="Subsidy APR")
    tieredSubsidyApr: Optional[List[TieredSubsidyApr]] = Field(
        default=None, description="Tieredsubsidyapr"
    )
    financialState: int = Field(..., description="Financialstate")
    startTime: Optional[int] = Field(default=None, description="Starttime")
    endTime: Optional[int] = Field(default=None, description="Endtime")
    soldOut: bool = Field(default=False, description="Soldout")
    sort: int = Field(..., description="Sort")
    memberType: str = Field(..., description="Membertype")
    profitCurrency: Optional[str] = Field(default=None, description="Profitcurrency")
    profitCurrencyId: Optional[str] = Field(default=None, description="Profitcurrencyid")
    profitCurrencyIcon: Optional[str] = Field(default=None, description="Profitcurrencyicon")


class CurrencyResult(BaseModel):
    currencyId: str = Field(..., description="Currencyid")
    currency: str = Field(..., description="Currency")
    currencyIcon: str = Field(..., description="Currencyicon")
    minApr: str = Field(..., description="Minapr")
    maxApr: str = Field(..., description="Maxapr")
    hasAprRange: bool = Field(default=False, description="Hasaprrange")
    investPeriodTypes: List[str] = Field(..., description="Investperiodtypes")
    financialProductList: List[FinancialProduct] = Field(..., description="Financialproductlist")
    sort: int = Field(..., description="Sort")


class MEXCEarnAPIResponse(BaseModel):
    model_config = ConfigDict(strict=False)

    code: int = Field(..., description="Code")
    msg: str = Field(..., description="Msg")
    timestamp: int = Field(..., description="Timestamp")
    data: Dict[str, Any] = Field(..., description="Data")

    @property
    def is_success(self) -> bool:
        return self.code == 0

    @property
    def result(self) -> List[CurrencyResult]:
        return [CurrencyResult(**item) for item in self.data.get("result", [])]

    @property
    def total(self) -> int:
        return self.data.get("total", 0)

    @property
    def page(self) -> int:
        return self.data.get("page", 1)

    @property
    def page_size(self) -> int:
        return self.data.get("pageSize", 100)

    @property
    def total_pages(self) -> int:
        return self.data.get("totalPage", 1)


# === Manual Import Models (Deprecated) ===


class MEXCManualProduct(BaseModel):
    product_type: str = Field(..., description="Product type")
    symbol: str = Field(..., description="Symbol")
    apy: float = Field(..., description="Apy")
    min_amount: Optional[float] = Field(default=None, description="Min amount")
    max_amount: Optional[float] = Field(default=None, description="Max amount")
    lock_period_days: int = Field(default=0, description="Lock period days")
    status: str = Field(..., description="Status")


class MEXCManualImport(BaseModel):
    exchange: str = Field(..., description="Exchange")
    updated_at: datetime = Field(..., description="Updated at")
    products: List[MEXCManualProduct] = Field(..., description="Products")
