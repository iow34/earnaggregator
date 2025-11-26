"""
Pydantic моделі для відповідей API.

Цей модуль визначає стандартизовані формати відповідей
для всіх API endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, UTC
from enum import Enum

from .yield_product import YieldProduct


class ResponseStatus(str, Enum):
    """Статуси відповідей API."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BaseResponse(BaseModel):
    """Базова модель відповіді API."""
    
    success: bool = Field(..., description="Чи успішний запит")
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Статус відповіді")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Час відповіді")
    message: Optional[str] = Field(default=None, description="Повідомлення")
    
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True
    )


class YieldResponse(BaseResponse):
    """Відповідь з даними про Yield продукти."""
    
    data: List[YieldProduct] = Field(default_factory=list, description="Список Yield продуктів")
    count: int = Field(default=0, description="Кількість продуктів")
    cached: bool = Field(default=False, description="Чи дані з кешу")
    source: Optional[str] = Field(default=None, description="Джерело даних")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Застосовані фільтри")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Автоматично встановлюємо count
        if 'count' not in data:
            self.count = len(self.data)
    
    def add_product(self, product: YieldProduct) -> None:
        """Додає продукт до відповіді."""
        self.data.append(product)
        self.count = len(self.data)
    
    def add_products(self, products: List[YieldProduct]) -> None:
        """Додає список продуктів до відповіді."""
        self.data.extend(products)
        self.count = len(self.data)
    
    def get_top_products(self, limit: int = 10) -> List[YieldProduct]:
        """Повертає топ продуктів за APY."""
        return sorted(self.data, key=lambda x: x.apy, reverse=True)[:limit]
    
    def get_products_by_provider(self, provider: str) -> List[YieldProduct]:
        """Повертає продукти конкретного провайдера."""
        return [p for p in self.data if p.provider.lower() == provider.lower()]
    
    def get_products_by_symbol(self, symbol: str) -> List[YieldProduct]:
        """Повертає продукти конкретного символу."""
        return [p for p in self.data if p.symbol.upper() == symbol.upper()]


class ErrorResponse(BaseResponse):
    """Відповідь з помилкою."""
    
    error: str = Field(..., description="Тип помилки")
    details: Optional[str] = Field(default=None, description="Деталі помилки")
    error_code: Optional[str] = Field(default=None, description="Код помилки")
    trace_id: Optional[str] = Field(default=None, description="ID трасировки")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = False
        data['status'] = ResponseStatus.ERROR
        super().__init__(**data)


class WarningResponse(BaseResponse):
    """Відповідь з попередженням."""
    
    warning: str = Field(..., description="Текст попередження")
    details: Optional[str] = Field(default=None, description="Деталі попередження")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.WARNING
        super().__init__(**data)


class InfoResponse(BaseResponse):
    """Відповідь з інформацією."""
    
    info: str = Field(..., description="Інформаційне повідомлення")
    details: Optional[str] = Field(default=None, description="Деталі")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.INFO
        super().__init__(**data)


class HealthResponse(BaseResponse):
    """Відповідь про стан сервісу."""
    
    service: str = Field(default="yield-data-service", description="Назва сервісу")
    version: str = Field(default="1.0.0", description="Версія сервісу")
    uptime: Optional[float] = Field(default=None, description="Час роботи в секундах")
    database_status: Optional[str] = Field(default=None, description="Статус бази даних")
    cache_status: Optional[str] = Field(default=None, description="Статус кешу")
    api_status: Optional[Dict[str, str]] = Field(default=None, description="Статус API бірж")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.SUCCESS
        super().__init__(**data)


class StatsResponse(BaseResponse):
    """Відповідь зі статистикою."""
    
    total_products: int = Field(default=0, description="Загальна кількість продуктів")
    active_products: int = Field(default=0, description="Кількість активних продуктів")
    providers_count: int = Field(default=0, description="Кількість провайдерів")
    symbols_count: int = Field(default=0, description="Кількість унікальних символів")
    avg_apy: Optional[float] = Field(default=None, description="Середній APY")
    max_apy: Optional[float] = Field(default=None, description="Максимальний APY")
    min_apy: Optional[float] = Field(default=None, description="Мінімальний APY")
    cache_hit_rate: Optional[float] = Field(default=None, description="Частота попадань в кеш")
    last_updated: Optional[datetime] = Field(default=None, description="Час останнього оновлення")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.SUCCESS
        super().__init__(**data)


class PaginatedResponse(BaseResponse):
    """Відповідь з пагінацією."""
    
    data: List[YieldProduct] = Field(default_factory=list, description="Дані")
    count: int = Field(default=0, description="Загальна кількість")
    page: int = Field(default=1, description="Поточна сторінка")
    per_page: int = Field(default=20, description="Елементів на сторінці")
    total_pages: int = Field(default=0, description="Загальна кількість сторінок")
    has_next: bool = Field(default=False, description="Чи є наступна сторінка")
    has_prev: bool = Field(default=False, description="Чи є попередня сторінка")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.SUCCESS
        super().__init__(**data)
        
        # Автоматично розраховуємо пагінацію
        if 'total_pages' not in data:
            self.total_pages = (self.count + self.per_page - 1) // self.per_page
        if 'has_next' not in data:
            self.has_next = self.page < self.total_pages
        if 'has_prev' not in data:
            self.has_prev = self.page > 1


class CacheResponse(BaseResponse):
    """Відповідь про стан кешу."""
    
    cache_key: str = Field(..., description="Ключ кешу")
    hit_count: int = Field(default=0, description="Кількість попадань")
    miss_count: int = Field(default=0, description="Кількість промахів")
    hit_rate: float = Field(default=0.0, description="Частота попадань")
    created_at: Optional[datetime] = Field(default=None, description="Час створення")
    expires_at: Optional[datetime] = Field(default=None, description="Час закінчення")
    data_size: Optional[int] = Field(default=None, description="Розмір даних в байтах")
    
    def __init__(self, **data):
        # Встановлюємо success перед викликом super()
        data['success'] = True
        data['status'] = ResponseStatus.SUCCESS
        super().__init__(**data)
        
        # Автоматично розраховуємо hit_rate
        if 'hit_rate' not in data and 'hit_count' in data and 'miss_count' in data:
            total = self.hit_count + self.miss_count
            self.hit_rate = (self.hit_count / total * 100) if total > 0 else 0.0


# Утилітарні функції для створення відповідей

def create_success_response(
    data: List[YieldProduct] = None,
    message: str = None,
    cached: bool = False,
    source: str = None
) -> YieldResponse:
    """Створює успішну відповідь з даними."""
    return YieldResponse(
        success=True,
        data=data or [],
        count=len(data) if data else 0,
        cached=cached,
        source=source,
        message=message
    )


def create_error_response(
    error: str,
    details: str = None,
    error_code: str = None,
    trace_id: str = None
) -> ErrorResponse:
    """Створює відповідь з помилкою."""
    return ErrorResponse(
        success=False,
        error=error,
        details=details,
        error_code=error_code,
        trace_id=trace_id
    )


def create_warning_response(
    warning: str,
    details: str = None,
    data: List[YieldProduct] = None
) -> Union[WarningResponse, YieldResponse]:
    """Створює відповідь з попередженням."""
    if data:
        return YieldResponse(
            success=True,
            data=data,
            count=len(data),
            message=warning,
            status=ResponseStatus.WARNING
        )
    else:
        return WarningResponse(
            success=True,
            warning=warning,
            details=details
        )


class TopByProviderResponse(BaseResponse):
    """Відповідь з топ продуктами згрупованими по provider'ам."""

    data: Dict[str, List[YieldProduct]] = Field(default_factory=dict, description="Топ продукти згруповані по provider'у")
    total_count: int = Field(default=0, description="Загальна кількість продуктів")
    providers_count: int = Field(default=0, description="Кількість provider'ів")
    cached: bool = Field(default=False, description="Чи дані з кешу")
    source: Optional[str] = Field(default=None, description="Джерело даних")

    def __init__(self, **data):
        super().__init__(**data)
        # Автоматично підраховуємо total_count та providers_count
        if 'total_count' not in data:
            self.total_count = sum(len(products) for products in self.data.values())
        if 'providers_count' not in data:
            self.providers_count = len(self.data)


def create_health_response(
    service: str = "yield-data-service",
    version: str = "1.0.0",
    uptime: float = None,
    database_status: str = None,
    cache_status: str = None,
    api_status: Dict[str, str] = None
) -> HealthResponse:
    """Створює відповідь про стан сервісу."""
    return HealthResponse(
        success=True,
        service=service,
        version=version,
        uptime=uptime,
        database_status=database_status,
        cache_status=cache_status,
        api_status=api_status
    )
