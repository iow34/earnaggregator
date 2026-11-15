from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, UTC
from enum import Enum

from .yield_product import YieldProduct
from app.__version__ import __version__ as app_version


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BaseResponse(BaseModel):
    success: bool = Field(..., description="Success")
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp")
    message: Optional[str] = Field(default=None, description="Message")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class YieldResponse(BaseResponse):
    data: List[YieldProduct] = Field(default_factory=list, description="Data")
    count: int = Field(default=0, description="Count")
    cached: bool = Field(default=False, description="Cached")
    source: Optional[str] = Field(default=None, description="Source")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters")

    def __init__(self, **data):
        super().__init__(**data)

        if "count" not in data:
            self.count = len(self.data)

    def add_product(self, product: YieldProduct) -> None:
        self.data.append(product)
        self.count = len(self.data)

    def add_products(self, products: List[YieldProduct]) -> None:
        self.data.extend(products)
        self.count = len(self.data)

    def get_top_products(self, limit: int = 10) -> List[YieldProduct]:
        return sorted(self.data, key=lambda x: x.apy, reverse=True)[:limit]

    def get_products_by_provider(self, provider: str) -> List[YieldProduct]:
        return [p for p in self.data if p.provider.lower() == provider.lower()]

    def get_products_by_symbol(self, symbol: str) -> List[YieldProduct]:
        return [p for p in self.data if p.symbol.upper() == symbol.upper()]


class ErrorResponse(BaseResponse):
    error: str = Field(..., description="Error")
    details: Optional[str] = Field(default=None, description="Details")
    error_code: Optional[str] = Field(default=None, description="Error code")
    trace_id: Optional[str] = Field(default=None, description="Trace id")

    def __init__(self, **data):

        data["success"] = False
        data["status"] = ResponseStatus.ERROR
        super().__init__(**data)


class WarningResponse(BaseResponse):
    warning: str = Field(..., description="Warning")
    details: Optional[str] = Field(default=None, description="Details")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.WARNING
        super().__init__(**data)


class InfoResponse(BaseResponse):
    info: str = Field(..., description="Info")
    details: Optional[str] = Field(default=None, description="Details")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.INFO
        super().__init__(**data)


class HealthResponse(BaseResponse):
    service: str = Field(default="yield-data-service", description="Service")
    version: str = Field(default=app_version, description="Version")
    uptime: Optional[float] = Field(default=None, description="Uptime")
    database_status: Optional[str] = Field(default=None, description="Database status")
    cache_status: Optional[str] = Field(default=None, description="Cache status")
    api_status: Optional[Dict[str, str]] = Field(default=None, description="Api status")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.SUCCESS
        super().__init__(**data)


class StatsResponse(BaseResponse):
    total_products: int = Field(default=0, description="Total products")
    active_products: int = Field(default=0, description="Active products")
    providers_count: int = Field(default=0, description="Providers count")
    symbols_count: int = Field(default=0, description="Symbols count")
    avg_apy: Optional[float] = Field(default=None, description="Avg apy")
    max_apy: Optional[float] = Field(default=None, description="Max apy")
    min_apy: Optional[float] = Field(default=None, description="Min apy")
    cache_hit_rate: Optional[float] = Field(default=None, description="Cache hit rate")
    last_updated: Optional[datetime] = Field(default=None, description="Last updated")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.SUCCESS
        super().__init__(**data)


class PaginatedResponse(BaseResponse):
    data: List[YieldProduct] = Field(default_factory=list, description="Data")
    count: int = Field(default=0, description="Count")
    page: int = Field(default=1, description="Page")
    per_page: int = Field(default=20, description="Per page")
    total_pages: int = Field(default=0, description="Total pages")
    has_next: bool = Field(default=False, description="Has next")
    has_prev: bool = Field(default=False, description="Has prev")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.SUCCESS
        super().__init__(**data)

        if "total_pages" not in data:
            self.total_pages = (self.count + self.per_page - 1) // self.per_page
        if "has_next" not in data:
            self.has_next = self.page < self.total_pages
        if "has_prev" not in data:
            self.has_prev = self.page > 1


class CacheResponse(BaseResponse):
    cache_key: str = Field(..., description="Cache key")
    hit_count: int = Field(default=0, description="Hit count")
    miss_count: int = Field(default=0, description="Miss count")
    hit_rate: float = Field(default=0.0, description="Hit rate")
    created_at: Optional[datetime] = Field(default=None, description="Created at")
    expires_at: Optional[datetime] = Field(default=None, description="Expires at")
    data_size: Optional[int] = Field(default=None, description="Data size")

    def __init__(self, **data):

        data["success"] = True
        data["status"] = ResponseStatus.SUCCESS
        super().__init__(**data)

        if "hit_rate" not in data and "hit_count" in data and "miss_count" in data:
            total = self.hit_count + self.miss_count
            self.hit_rate = (self.hit_count / total * 100) if total > 0 else 0.0


def create_success_response(
    data: List[YieldProduct] = None, message: str = None, cached: bool = False, source: str = None
) -> YieldResponse:
    return YieldResponse(
        success=True,
        data=data or [],
        count=len(data) if data else 0,
        cached=cached,
        source=source,
        message=message,
    )


def create_error_response(
    error: str, details: str = None, error_code: str = None, trace_id: str = None
) -> ErrorResponse:
    return ErrorResponse(
        success=False, error=error, details=details, error_code=error_code, trace_id=trace_id
    )


def create_warning_response(
    warning: str, details: str = None, data: List[YieldProduct] = None
) -> Union[WarningResponse, YieldResponse]:
    if data:
        return YieldResponse(
            success=True, data=data, count=len(data), message=warning, status=ResponseStatus.WARNING
        )
    else:
        return WarningResponse(success=True, warning=warning, details=details)


class TopByProviderResponse(BaseResponse):
    data: Dict[str, List[YieldProduct]] = Field(default_factory=dict, description="Data")
    total_count: int = Field(default=0, description="Total count")
    providers_count: int = Field(default=0, description="Providers count")
    cached: bool = Field(default=False, description="Cached")
    source: Optional[str] = Field(default=None, description="Source")

    def __init__(self, **data):
        super().__init__(**data)

        if "total_count" not in data:
            self.total_count = sum(len(products) for products in self.data.values())
        if "providers_count" not in data:
            self.providers_count = len(self.data)


def create_health_response(
    service: str = "yield-data-service",
    version: str = None,
    uptime: float = None,
    database_status: str = None,
    cache_status: str = None,
    api_status: Dict[str, str] = None,
) -> HealthResponse:
    if version is None:
        version = app_version
    return HealthResponse(
        success=True,
        service=service,
        version=version,
        uptime=uptime,
        database_status=database_status,
        cache_status=cache_status,
        api_status=api_status,
    )
