"""
Pydantic моделі для BitMart API та Earn продуктів.

Моделі включають:
- API відповіді від BitMart earn products endpoint
- Моделі для Tiered APR (залежно від суми)
- Моделі для окремих продуктів
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


# === API Response Models ===

class TierRule(BaseModel):
    """
    Модель для tiered APR (залежно від суми).
    """
    sequence: int = Field(..., description="Порядок тира")
    start: str = Field(..., description="Початкова сума")
    end: Optional[str] = Field(default=None, description="Кінцева сума (null для необмеженого)")
    pec: str = Field(..., description="APR для цього діапазону")


class AddInfo(BaseModel):
    """
    Модель для детальної інформації продукту.
    """
    id: str = Field(..., description="Унікальний ID продукту")
    productType: str = Field(..., description="Тип продукту (flexible/fixed/stable)")
    earnType: str = Field(..., description="Тип заробітку (saving/wealth)")
    productName: str = Field(..., description="Назва продукту")
    productCnName: str = Field(..., description="Китайська назва продукту")
    coinId: int = Field(..., description="ID валюти")
    coinName: str = Field(..., description="Символ валюти")
    lockDay: int = Field(..., description="Дні блокування (0 для flexible)")
    minSubcription: str = Field(..., description="Мінімальна підписка")
    annualProfitPec: str = Field(..., description="Річний прибуток у відсотках")
    interestRate: Optional[str] = Field(default=None, description="Процентна ставка")
    sortWeight: int = Field(..., description="Вага сортування")
    launchTime: Optional[int] = Field(default=None, description="Час запуску")
    saleState: int = Field(..., description="Стан продажу (1 = активний)")
    productTags: str = Field(..., description="Теги продукту")
    rateType: int = Field(..., description="Тип ставки (0 = фіксований, 1 = tiered)")
    tierRules: List[TierRule] = Field(default_factory=list, description="Правила tiered ставок")
    additionalAnnualProfitPec: str = Field(default="", description="Додатковий річний прибуток")
    additionalDetailLink: str = Field(default="", description="Посилання на деталі")
    additionalDescriptionList: List[Dict[str, Any]] = Field(default_factory=list, description="Додаткові описи")
    priorityDisplay: bool = Field(default=False, description="Пріоритет відображення")
    couponsProfitPec: Optional[str] = Field(default=None, description="Купонний прибуток")
    orderPrecision: Optional[str] = Field(default=None, description="Точність замовлення")
    profitBigDecimal: str = Field(..., description="Прибуток у вигляді десяткового числа")
    coinPriority: int = Field(..., description="Пріоритет валюти")
    tagPriority: int = Field(..., description="Пріоритет тегу")
    earnProductWealth: Optional[Any] = Field(default=None, description="Продукт wealth")
    groupId: int = Field(..., description="ID групи")


class WealthProduct(BaseModel):
    """
    Модель для wealth продуктів (якщо є).
    """
    id: str = Field(..., description="ID wealth продукту")
    productName: str = Field(..., description="Назва wealth продукту")
    productCnName: str = Field(..., description="Китайська назва")
    coinId: int = Field(..., description="ID валюти")
    coinName: str = Field(..., description="Символ валюти")
    coinFullName: Optional[str] = Field(default=None, description="Повна назва валюти")
    coinIcon: Optional[str] = Field(default=None, description="Іконка валюти")
    lockDay: int = Field(..., description="Дні блокування")
    minSubcription: str = Field(..., description="Мінімальна підписка")
    productType: str = Field(..., description="Тип продукту")
    annualProfitPec: str = Field(..., description="Річний прибуток")
    orderPrecision: Optional[str] = Field(default=None, description="Точність замовлення")
    launchTime: int = Field(..., description="Час запуску")
    saleState: int = Field(..., description="Стан продажу")
    startBuyTime: int = Field(..., description="Час початку покупки")
    saleStopTime: int = Field(..., description="Час закінчення продажу")
    interestStartTime: int = Field(..., description="Час початку відсотків")
    interestEndTime: int = Field(..., description="Час закінчення відсотків")
    redeemTime: int = Field(..., description="Час викупу")
    reinvestTime: Optional[int] = Field(default=None, description="Час реінвестування")
    availableBalance: Optional[str] = Field(default=None, description="Доступний баланс")
    profitList: List[Any] = Field(default_factory=list, description="Список прибутків")
    remainingSubscribeAmount: Optional[str] = Field(default=None, description="Залишкова сума підписки")
    sortWeight: int = Field(..., description="Вага сортування")
    couponsProfitPec: Optional[str] = Field(default=None, description="Купонний прибуток")
    existCouponsInterest: Optional[bool] = Field(default=None, description="Існує купонний відсоток")
    couponsInterestList: Optional[List[Any]] = Field(default=None, description="Список купонних відсотків")


class SummaryProductList(BaseModel):
    """
    Модель для списку продуктів по типам.
    """
    productId: Optional[str] = Field(default=None, description="ID продукту")
    productType: str = Field(..., description="Тип продукту")
    earnType: str = Field(..., description="Тип заробітку")
    labelNameList: Optional[List[str]] = Field(default=None, description="Список міток")
    addInfo: List[AddInfo] = Field(default_factory=list, description="Додаткова інформація")
    wealthProduct: Optional[WealthProduct] = Field(default=None, description="Wealth продукт")
    duration: Optional[List[str]] = Field(default=None, description="Тривалість")
    annualProfitPecMin: Optional[str] = Field(default=None, description="Мін. річний прибуток")
    annualProfitPecMax: Optional[str] = Field(default=None, description="Макс. річний прибуток")


class EarnProduct(BaseModel):
    """
    Модель для продукту earn (повний об'єкт з API).
    """
    coinId: int = Field(..., description="ID валюти")
    coinName: str = Field(..., description="Символ валюти")
    coinFullName: str = Field(..., description="Повна назва валюти")
    coinUrl: str = Field(..., description="URL іконки валюти")
    labelNameList: Optional[List[str]] = Field(default=None, description="Список міток")
    availableBalance: str = Field(..., description="Доступний баланс")
    summaryProductList: List[SummaryProductList] = Field(..., description="Список продуктів")
    earnTypeList: List[str] = Field(..., description="Список типів заробітку")
    duration: List[str] = Field(..., description="Доступні тривалості")
    annualProfitPecMin: str = Field(..., description="Мінімальний річний прибуток")
    annualProfitPecMax: str = Field(..., description="Максимальний річний прибуток")
    plusInterestCoupon: bool = Field(..., description="Плюс купон відсотків")


class BitMartEarnAPIResponse(BaseModel):
    """
    Модель для повної відповіді BitMart Earn API.
    """
    model_config = ConfigDict(strict=False)

    code: int = Field(..., description="Код відповіді (0 = успіх)")
    msg: str = Field(..., description="Повідомлення")
    data: List[EarnProduct] = Field(..., description="Дані продуктів")

    @property
    def is_success(self) -> bool:
        """Перевіряє чи успішна відповідь."""
        return self.code == 0

    @property
    def result(self) -> List[EarnProduct]:
        """Отримує список продуктів."""
        return self.data
