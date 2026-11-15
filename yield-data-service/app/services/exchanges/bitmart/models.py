from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# === API Response Models ===


class TierRule(BaseModel):
    sequence: int = Field(..., description="Sequence")
    start: str = Field(..., description="Start")
    end: Optional[str] = Field(default=None, description="End")
    pec: str = Field(..., description="Pec")


class AddInfo(BaseModel):
    id: str = Field(..., description="Id")
    productType: str = Field(..., description="Producttype")
    earnType: str = Field(..., description="Earntype")
    productName: str = Field(..., description="Productname")
    productCnName: str = Field(..., description="Productcnname")
    coinId: int = Field(..., description="Coinid")
    coinName: str = Field(..., description="Coinname")
    lockDay: int = Field(..., description="Lockday")
    minSubcription: str = Field(..., description="Minsubcription")
    annualProfitPec: str = Field(..., description="Annualprofitpec")
    interestRate: Optional[str] = Field(default=None, description="Interestrate")
    sortWeight: int = Field(..., description="Sortweight")
    launchTime: Optional[int] = Field(default=None, description="Launchtime")
    saleState: int = Field(..., description="Salestate")
    productTags: str = Field(..., description="Producttags")
    rateType: int = Field(..., description="Ratetype")
    tierRules: List[TierRule] = Field(default_factory=list, description="Tierrules")
    additionalAnnualProfitPec: str = Field(default="", description="Additionalannualprofitpec")
    additionalDetailLink: str = Field(default="", description="Additionaldetaillink")
    additionalDescriptionList: List[Dict[str, Any]] = Field(
        default_factory=list, description="Additionaldescriptionlist"
    )
    priorityDisplay: bool = Field(default=False, description="Prioritydisplay")
    couponsProfitPec: Optional[str] = Field(default=None, description="Couponsprofitpec")
    orderPrecision: Optional[str] = Field(default=None, description="Orderprecision")
    profitBigDecimal: str = Field(..., description="Profitbigdecimal")
    coinPriority: int = Field(..., description="Coinpriority")
    tagPriority: int = Field(..., description="Tagpriority")
    earnProductWealth: Optional[Any] = Field(default=None, description="Earnproductwealth")
    groupId: int = Field(..., description="Groupid")


class WealthProduct(BaseModel):
    id: str = Field(..., description="Id")
    productName: str = Field(..., description="Productname")
    productCnName: str = Field(..., description="Productcnname")
    coinId: int = Field(..., description="Coinid")
    coinName: str = Field(..., description="Coinname")
    coinFullName: Optional[str] = Field(default=None, description="Coinfullname")
    coinIcon: Optional[str] = Field(default=None, description="Coinicon")
    lockDay: int = Field(..., description="Lockday")
    minSubcription: str = Field(..., description="Minsubcription")
    productType: str = Field(..., description="Producttype")
    annualProfitPec: str = Field(..., description="Annualprofitpec")
    orderPrecision: Optional[str] = Field(default=None, description="Orderprecision")
    launchTime: int = Field(..., description="Launchtime")
    saleState: int = Field(..., description="Salestate")
    startBuyTime: int = Field(..., description="Startbuytime")
    saleStopTime: int = Field(..., description="Salestoptime")
    interestStartTime: int = Field(..., description="Intereststarttime")
    interestEndTime: int = Field(..., description="Interestendtime")
    redeemTime: int = Field(..., description="Redeemtime")
    reinvestTime: Optional[int] = Field(default=None, description="Reinvesttime")
    availableBalance: Optional[str] = Field(default=None, description="Availablebalance")
    profitList: List[Any] = Field(default_factory=list, description="Profitlist")
    remainingSubscribeAmount: Optional[str] = Field(
        default=None, description="Remainingsubscribeamount"
    )
    sortWeight: int = Field(..., description="Sortweight")
    couponsProfitPec: Optional[str] = Field(default=None, description="Couponsprofitpec")
    existCouponsInterest: Optional[bool] = Field(default=None, description="Existcouponsinterest")
    couponsInterestList: Optional[List[Any]] = Field(
        default=None, description="Couponsinterestlist"
    )


class SummaryProductList(BaseModel):
    productId: Optional[str] = Field(default=None, description="Productid")
    productType: str = Field(..., description="Producttype")
    earnType: str = Field(..., description="Earntype")
    labelNameList: Optional[List[str]] = Field(default=None, description="Labelnamelist")
    addInfo: List[AddInfo] = Field(default_factory=list, description="Addinfo")
    wealthProduct: Optional[WealthProduct] = Field(default=None, description="Wealthproduct")
    duration: Optional[List[str]] = Field(default=None, description="Duration")
    annualProfitPecMin: Optional[str] = Field(default=None, description="Annualprofitpecmin")
    annualProfitPecMax: Optional[str] = Field(default=None, description="Annualprofitpecmax")


class EarnProduct(BaseModel):
    coinId: int = Field(..., description="Coinid")
    coinName: str = Field(..., description="Coinname")
    coinFullName: str = Field(..., description="Coinfullname")
    coinUrl: str = Field(..., description="Coinurl")
    labelNameList: Optional[List[str]] = Field(default=None, description="Labelnamelist")
    availableBalance: str = Field(..., description="Availablebalance")
    summaryProductList: List[SummaryProductList] = Field(..., description="Summaryproductlist")
    earnTypeList: List[str] = Field(..., description="Earntypelist")
    duration: List[str] = Field(..., description="Duration")
    annualProfitPecMin: str = Field(..., description="Annualprofitpecmin")
    annualProfitPecMax: str = Field(..., description="Annualprofitpecmax")
    plusInterestCoupon: bool = Field(..., description="Plusinterestcoupon")


class BitMartEarnAPIResponse(BaseModel):
    model_config = ConfigDict(strict=False)

    code: int = Field(..., description="Code")
    msg: str = Field(..., description="Msg")
    data: List[EarnProduct] = Field(..., description="Data")

    @property
    def is_success(self) -> bool:
        return self.code == 0

    @property
    def result(self) -> List[EarnProduct]:
        return self.data
