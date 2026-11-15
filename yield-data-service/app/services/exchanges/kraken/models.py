from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class KrakenStrategy(BaseModel):
    id: str = Field(..., description="Id")
    asset: str = Field(..., description="Asset")
    lock_type: str = Field(..., description="Lock type")
    rate: str = Field(..., description="Rate")
    rate_type: Optional[str] = Field(None, description="Rate type")
    duration: Optional[str] = Field(None, description="Duration")
    min_amount: str = Field(..., description="Min amount")
    max_amount: Optional[str] = Field(None, description="Max amount")
    can_allocate: bool = Field(..., description="Can allocate")
    allocation_restriction_info: Optional[Dict[str, Any]] = Field(
        None, description="Allocation restriction info"
    )

    class Config:
        extra = "allow"


class KrakenStrategiesResponse(BaseModel):
    strategies: List[KrakenStrategy] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(None, description="Next cursor")

    class Config:
        extra = "allow"


class KrakenAPIResponse(BaseModel):
    error: List[str] = Field(default_factory=list, description="Error")
    result: Optional[Dict[str, Any]] = Field(None, description="Result")

    class Config:
        extra = "allow"
