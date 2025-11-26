"""
Pydantic-схеми для API розсилок.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BroadcastContent(BaseModel):
    text: Optional[str] = None
    parse_mode: Literal["HTML", "Markdown", "MarkdownV2"] = "HTML"
    media_file_id: Optional[str] = None
    media_url: Optional[str] = None
    buttons: List[dict] = Field(default_factory=list)
    disable_link_preview: bool = False


class BroadcastAudienceFilter(BaseModel):
    is_subscribed: Optional[bool] = True
    languages: List[str] = Field(default_factory=list)
    tags_all: List[str] = Field(default_factory=list)
    tags_any: List[str] = Field(default_factory=list)
    telegram_ids: List[int] = Field(default_factory=list)
    last_active_after: Optional[datetime] = None

    @field_validator("languages", "tags_all", "tags_any", "telegram_ids", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        if isinstance(v, (list, tuple, set)):
            return list(v)
        return [v]


class BroadcastCreatePayload(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content_type: Literal["text", "markdown", "html", "photo", "document"] = "text"
    content: BroadcastContent
    filters: BroadcastAudienceFilter = Field(default_factory=BroadcastAudienceFilter)
    channel: Literal["web_ui", "cli", "admin_bot"] = "web_ui"
    requires_approval: bool = False
    scheduled_at: Optional[datetime] = None
    preview_chat_id: Optional[int] = None
    batch_size: int = Field(default=100, ge=10, le=500)

    @model_validator(mode="after")
    def validate_content_matches_type(self):
        if self.content_type in {"text", "markdown", "html"} and not self.content.text:
            raise ValueError("Text content is required for textual broadcasts")
        if self.content_type in {"photo", "document"} and not (
            self.content.media_file_id or self.content.media_url
        ):
            raise ValueError("Media broadcasts require file_id or URL")
        return self


class BroadcastPreviewPayload(BaseModel):
    content_type: Literal["text", "markdown", "html", "photo", "document"] = "text"
    content: BroadcastContent
    preview_chat_id: int


class AdminSummary(BaseModel):
    id: int
    email: str
    role: str


class BroadcastStats(BaseModel):
    sent: int = 0
    failed: int = 0
    pending: int = 0
    skipped: int = 0


class BroadcastSummary(BaseModel):
    id: int
    title: str
    status: str
    channel: str
    total_recipients: int
    stats: BroadcastStats
    requires_approval: bool
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    author: AdminSummary


class BroadcastListResponse(BaseModel):
    items: List[BroadcastSummary]
    page: int
    per_page: int
    total: int


class BroadcastDetailResponse(BaseModel):
    broadcast: BroadcastSummary
    content: BroadcastContent
    filters: BroadcastAudienceFilter
    metadata: dict[str, Any]
    preview_chat_id: Optional[int] = None
    batch_size: int


class BroadcastEventSchema(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    admin: Optional[AdminSummary] = None


class BroadcastEventsResponse(BaseModel):
    items: List[BroadcastEventSchema]
    page: int
    per_page: int
    total: int


class BroadcastRecipientSchema(BaseModel):
    id: int
    telegram_id: int
    language: str
    status: str
    attempts: int
    message_id: Optional[str] = None
    error_code: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    created_at: datetime


class BroadcastRecipientsResponse(BaseModel):
    items: List[BroadcastRecipientSchema]
    page: int
    per_page: int
    total: int


class DashboardMetricsResponse(BaseModel):
    total_broadcasts: int
    active_broadcasts: int
    scheduled_broadcasts: int
    pending_approval: int
    sent_today: int
    failed_today: int

