"""
Pydantic моделі для OKX API відповідей.

Моделі використовуються для валідації та типізації даних з OKX Financial Product API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class OKXInvestData(BaseModel):
    """Дані про інвестиційні параметри On-chain продукту."""
    ccy: str = Field(..., description="Валюта")
    bal: str = Field(default="", description="Баланс")
    min_amt: str = Field(default="0", description="Мінімальна сума", alias="minAmt")
    max_amt: str = Field(default="", description="Максимальна сума", alias="maxAmt")
    
    class Config:
        populate_by_name = True


class OKXOnChainProduct(BaseModel):
    """Модель для On-chain earn продуктів OKX."""
    product_id: str = Field(..., description="ID продукту", alias="productId")
    ccy: str = Field(..., description="Символ валюти")
    protocol: str = Field(..., description="Протокол (lido, rocket, тощо)")
    protocol_type: str = Field(..., description="Тип протоколу (staking, defi_lending)", alias="protocolType")
    term: str = Field(default="", description="Термін блокування (днів) або порожній для flexible")
    apy: str = Field(..., description="Річна відсоткова дохідність (формат: '0.0395')")
    early_redeem: bool = Field(default=False, description="Чи можна вивести достроково", alias="earlyRedeem")
    state: str = Field(..., description="Статус: 'purchasable', 'sold_out', 'suspend'")
    invest_data: Optional[List[OKXInvestData]] = Field(default=None, description="Інвестиційні дані", alias="investData")
    
    class Config:
        populate_by_name = True


class OKXSimpleEarnProduct(BaseModel):
    """Модель для Simple Earn Flexible продуктів OKX."""
    ccy: str = Field(..., description="Символ валюти")
    rate: str = Field(..., description="APY у string форматі")
    min_amt: str = Field(default="0", description="Мінімальна сума", alias="minAmt")
    max_amt: str = Field(default="", description="Максимальна сума", alias="maxAmt")
    auto_renew: bool = Field(default=False, description="Автоматичне поновлення", alias="autoRenew")
    status: str = Field(..., description="Статус: 'available', 'unavailable'")
    
    class Config:
        populate_by_name = True


class OKXUnifiedProduct(BaseModel):
    """
    Уніфікована модель для всіх типів OKX продуктів.
    
    Приводить дані з різних API до єдиного формату EarnAggregator.
    """
    id: str = Field(..., description="Унікальний ID продукту")
    symbol: str = Field(..., description="Символ криптовалюти")
    name: str = Field(..., description="Назва продукту")
    provider: str = Field(default="OKX", description="Назва біржі")
    apy: float = Field(..., description="Річна відсоткова дохідність (%)")
    min_amount: Optional[float] = Field(default=None, description="Мінімальна сума для участі")
    max_amount: Optional[float] = Field(default=None, description="Максимальна сума")
    lock_period_days: int = Field(default=0, description="Термін блокування (дні)")
    product_type: str = Field(..., description="Тип продукту: OnChain / SimpleFlexible")
    is_active: bool = Field(default=True, description="Чи активний продукт")
    risk_level: str = Field(default="Low", description="Рівень ризику")
    can_early_redeem: bool = Field(default=False, description="Чи можна вивести достроково")
    protocol: Optional[str] = Field(default=None, description="Протокол (для On-chain)")
    description: Optional[str] = Field(default=None, description="Опис продукту")
    website_url: Optional[str] = Field(default=None, description="Посилання на продукт")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Сирі дані з API")
    
    class Config:
        populate_by_name = True


class OKXAPIResponse(BaseModel):
    """Базова структура відповіді OKX API."""
    code: str = Field(..., description="Код відповіді: '0' = успіх")
    msg: str = Field(default="", description="Повідомлення про помилку (якщо є)")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Дані відповіді")
    
    def is_success(self) -> bool:
        """Перевіряє чи успішна відповідь."""
        return self.code == "0"

