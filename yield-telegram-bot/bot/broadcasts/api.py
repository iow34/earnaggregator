from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from bot.broadcasts.auth import admin_auth_service
from bot.broadcasts.schemas import (
    BroadcastCreatePayload,
    BroadcastDetailResponse,
    BroadcastEventsResponse,
    BroadcastListResponse,
    BroadcastPreviewPayload,
    BroadcastRecipientsResponse,
    DashboardMetricsResponse,
)
from bot.broadcasts.service import BroadcastService, broadcast_service
from bot.db.database import get_database_session

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


async def get_db_session():
    async with get_database_session() as session:
        yield session


def get_broadcast_service() -> BroadcastService:
    return broadcast_service


async def get_current_admin(
    x_admin_api_key: str = Header(default=None, convert_underscores=True),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_admin_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key required")

    admin = await admin_auth_service.authenticate_api_key(session, x_admin_api_key)
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return admin


@router.get("", response_model=BroadcastListResponse)
async def list_broadcasts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel: Optional[str] = None,
    author_id: Optional[int] = None,
    requires_approval: Optional[bool] = Query(None),
    scheduled_from: Optional[datetime] = None,
    scheduled_to: Optional[datetime] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    filters = {
        "status": status_filter,
        "channel": channel,
        "author_id": author_id,
        "requires_approval": requires_approval,
        "scheduled_from": scheduled_from,
        "scheduled_to": scheduled_to,
        "search": search,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    return await service.list_broadcasts(
        session=session,
        filters=filters,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_broadcast(
    payload: BroadcastCreatePayload,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.create_broadcast(session, payload, admin)


@router.get("/metrics/summary", response_model=DashboardMetricsResponse)
async def get_metrics_summary(
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.get_dashboard_metrics(session)


@router.get("/{broadcast_id}", response_model=BroadcastDetailResponse)
async def get_broadcast_detail(
    broadcast_id: int,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    data = await service.get_broadcast_detail(session, broadcast_id)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
    return data


@router.get("/{broadcast_id}/status")
async def get_broadcast_status(
    broadcast_id: int,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    data = await service.get_status(session, broadcast_id)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
    return data


@router.post("/{broadcast_id}/cancel")
async def cancel_broadcast(
    broadcast_id: int,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    data = await service.cancel_broadcast(session, broadcast_id, admin)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
    return data


@router.post("/{broadcast_id}/retry")
async def retry_broadcast(
    broadcast_id: int,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    data = await service.retry_broadcast(session, broadcast_id, admin)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
    return data


@router.post("/{broadcast_id}/approve")
async def approve_broadcast(
    broadcast_id: int,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    try:
        data = await service.approve_broadcast(session, broadcast_id, admin)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner role required")
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
    return data


@router.post("/preview")
async def preview_broadcast(
    payload: BroadcastPreviewPayload,
    admin=Depends(get_current_admin),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.send_preview(payload, admin)


@router.get("/{broadcast_id}/events", response_model=BroadcastEventsResponse)
async def list_broadcast_events(
    broadcast_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.get_broadcast_events(session, broadcast_id, page, per_page)


@router.get("/{broadcast_id}/recipients", response_model=BroadcastRecipientsResponse)
async def list_broadcast_recipients(
    broadcast_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
    service: BroadcastService = Depends(get_broadcast_service),
):
    return await service.get_broadcast_recipients(
        session=session,
        broadcast_id=broadcast_id,
        status=status_filter,
        page=page,
        per_page=per_page,
        search=search,
    )
