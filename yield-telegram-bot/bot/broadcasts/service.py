from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Any, Dict

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.broadcasts.queue import BroadcastQueue
from bot.broadcasts.schemas import (
    AdminSummary,
    BroadcastAudienceFilter,
    BroadcastContent,
    BroadcastCreatePayload,
    BroadcastDetailResponse,
    BroadcastEventsResponse,
    BroadcastListResponse,
    BroadcastPreviewPayload,
    BroadcastRecipientSchema,
    BroadcastRecipientsResponse,
    BroadcastSummary,
    BroadcastStats,
    DashboardMetricsResponse,
    BroadcastEventSchema,
)
from bot.broadcasts.sender import BroadcastSender
from bot.db import crud
from bot.db.models import Broadcast, BroadcastRecipient, AdminUser
from bot.config import settings
from bot.utils.logger import logger


class BroadcastService:
    def __init__(self, queue: Optional[BroadcastQueue] = None):
        self.queue = queue or BroadcastQueue()
        self._preview_sender: Optional[BroadcastSender] = None

    async def create_broadcast(
        self,
        session: AsyncSession,
        payload: BroadcastCreatePayload,
        admin: AdminUser,
    ) -> dict:
        recipients = await crud.filter_users_for_broadcast(
            session,
            filters=payload.filters.model_dump(exclude_none=True),
            limit=10_000,
        )

        needs_manual_approval = self._requires_secondary_confirmation(
            total=len(recipients),
            explicit_flag=payload.requires_approval,
            admin_role=admin.role,
        )
        status = "scheduled" if payload.scheduled_at else "queued"
        if needs_manual_approval:
            status = "pending_approval"

        broadcast = Broadcast(
            title=payload.title,
            content_type=payload.content_type,
            content_payload=payload.content.model_dump(exclude_none=True),
            filter_query=payload.filters.model_dump(exclude_none=True),
            status=status,
            author_admin_id=admin.id,
            channel=payload.channel,
            requires_approval=payload.requires_approval,
            scheduled_at=payload.scheduled_at,
            preview_chat_id=payload.preview_chat_id,
            metadata_payload={},
            total_recipients=len(recipients),
            batch_size=payload.batch_size,
        )

        session.add(broadcast)
        await session.flush()

        for user in recipients:
            session.add(
                BroadcastRecipient(
                    broadcast_id=broadcast.id,
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    language=user.language,
                )
            )

        await session.commit()
        await session.refresh(broadcast)

        await crud.record_broadcast_event(
            session,
            broadcast_id=broadcast.id,
            event_type="created",
            admin_id=admin.id,
            payload={
                "total_recipients": broadcast.total_recipients,
                "channel": broadcast.channel,
            },
        )

        if recipients and broadcast.status == "queued":
            await self.queue.enqueue_broadcast(broadcast.id)
            logger.info("Broadcast %s queued with %s recipients", broadcast.id, len(recipients))
        elif not recipients:
            logger.warning("Broadcast %s has no recipients", broadcast.id)

        return {
            "broadcast_id": broadcast.id,
            "status": broadcast.status,
            "total_recipients": broadcast.total_recipients,
        }

    async def list_broadcasts(
        self,
        session: AsyncSession,
        filters: dict,
        page: int,
        per_page: int,
        sort_by: str,
        sort_dir: str,
    ) -> BroadcastListResponse:
        rows, total = await crud.list_broadcasts(
            session=session,
            filters=filters,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        items: list[BroadcastSummary] = []
        for broadcast, admin, sent, failed, pending, skipped in rows:
            items.append(
                self._build_broadcast_summary(
                    broadcast=broadcast,
                    admin=admin,
                    stats={"sent": sent, "failed": failed, "pending": pending, "skipped": skipped},
                )
            )
        return BroadcastListResponse(items=items, page=page, per_page=per_page, total=total)

    async def get_broadcast_detail(
        self,
        session: AsyncSession,
        broadcast_id: int,
    ) -> Optional[BroadcastDetailResponse]:
        row = await crud.get_broadcast_with_stats(session, broadcast_id)
        if not row:
            return None
        broadcast, admin, sent, failed, pending, skipped = row
        summary = self._build_broadcast_summary(
            broadcast=broadcast,
            admin=admin,
            stats={"sent": sent, "failed": failed, "pending": pending, "skipped": skipped},
        )
        content = BroadcastContent(**broadcast.content_payload)
        filters = BroadcastAudienceFilter(**broadcast.filter_query)
        metadata = broadcast.metadata_payload or {}
        return BroadcastDetailResponse(
            broadcast=summary,
            content=content,
            filters=filters,
            metadata=metadata,
            preview_chat_id=broadcast.preview_chat_id,
            batch_size=broadcast.batch_size,
        )

    async def get_broadcast_events(
        self,
        session: AsyncSession,
        broadcast_id: int,
        page: int,
        per_page: int,
    ) -> BroadcastEventsResponse:
        rows, total = await crud.get_broadcast_events(session, broadcast_id, page, per_page)
        items: list[BroadcastEventSchema] = []
        for event, admin in rows:
            admin_payload = None
            if admin:
                admin_payload = AdminSummary(id=admin.id, email=admin.email, role=admin.role)
            items.append(
                BroadcastEventSchema(
                    id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    created_at=event.created_at,
                    admin=admin_payload,
                )
            )
        return BroadcastEventsResponse(items=items, page=page, per_page=per_page, total=total)

    async def get_broadcast_recipients(
        self,
        session: AsyncSession,
        broadcast_id: int,
        status: Optional[str],
        page: int,
        per_page: int,
        search: Optional[str],
    ) -> BroadcastRecipientsResponse:
        rows, total = await crud.get_broadcast_recipients(
            session=session,
            broadcast_id=broadcast_id,
            status=status,
            page=page,
            per_page=per_page,
            search=search,
        )
        items = [
            BroadcastRecipientSchema(
                id=recipient.id,
                telegram_id=recipient.telegram_id,
                language=recipient.language,
                status=recipient.status,
                attempts=recipient.attempts,
                message_id=recipient.message_id,
                error_code=recipient.error_code,
                last_attempt_at=recipient.last_attempt_at,
                created_at=recipient.created_at,
            )
            for recipient in rows
        ]
        return BroadcastRecipientsResponse(items=items, page=page, per_page=per_page, total=total)

    async def get_dashboard_metrics(self, session: AsyncSession) -> DashboardMetricsResponse:
        data = await crud.get_dashboard_metrics(session)
        return DashboardMetricsResponse(**data)

    async def get_status(
        self,
        session: AsyncSession,
        broadcast_id: int,
    ) -> Optional[dict]:
        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await session.execute(stmt)
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return None

        stats_stmt = (
            select(BroadcastRecipient.status, func.count(BroadcastRecipient.id))
            .where(BroadcastRecipient.broadcast_id == broadcast_id)
            .group_by(BroadcastRecipient.status)
        )
        stats_result = await session.execute(stats_stmt)
        status_map = {status: count for status, count in stats_result.all()}

        return {
            "broadcast_id": broadcast.id,
            "status": broadcast.status,
            "scheduled_at": broadcast.scheduled_at,
            "started_at": broadcast.started_at,
            "completed_at": broadcast.completed_at,
            "total_recipients": broadcast.total_recipients,
            "recipients": status_map,
        }

    async def cancel_broadcast(
        self,
        session: AsyncSession,
        broadcast_id: int,
        admin: AdminUser,
    ) -> Optional[dict]:
        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await session.execute(stmt)
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return None

        broadcast.status = "cancelled"
        broadcast.cancelled_at = datetime.now(UTC)
        await session.execute(
            update(BroadcastRecipient)
            .where(
                BroadcastRecipient.broadcast_id == broadcast_id,
                BroadcastRecipient.status.in_(["pending"]),
            )
            .values(status="skipped")
        )
        await session.commit()

        await crud.record_broadcast_event(
            session,
            broadcast_id=broadcast_id,
            event_type="cancelled",
            admin_id=admin.id,
            payload={},
        )

        return {"broadcast_id": broadcast_id, "status": "cancelled"}

    async def approve_broadcast(
        self,
        session: AsyncSession,
        broadcast_id: int,
        admin: AdminUser,
    ) -> Optional[dict]:
        if admin.role != "owner":
            raise PermissionError("Only owner can approve broadcasts")

        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await session.execute(stmt)
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return None

        if broadcast.status != "pending_approval":
            return {"broadcast_id": broadcast.id, "status": broadcast.status}

        broadcast.approved_at = datetime.now(UTC)
        broadcast.approved_by_admin_id = admin.id
        broadcast.status = "scheduled" if broadcast.scheduled_at else "queued"
        await session.commit()

        await crud.record_broadcast_event(
            session,
            broadcast_id=broadcast.id,
            event_type="approved",
            admin_id=admin.id,
            payload={
                "scheduled_at": broadcast.scheduled_at.isoformat()
                if broadcast.scheduled_at
                else None
            },
        )

        if broadcast.status == "queued" and broadcast.total_recipients:
            await self.queue.enqueue_broadcast(broadcast.id)

        return {"broadcast_id": broadcast.id, "status": broadcast.status}

    async def retry_broadcast(
        self,
        session: AsyncSession,
        broadcast_id: int,
        admin: AdminUser,
    ) -> Optional[dict]:
        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await session.execute(stmt)
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return None

        await session.execute(
            update(BroadcastRecipient)
            .where(
                BroadcastRecipient.broadcast_id == broadcast_id,
                BroadcastRecipient.status.in_(["failed", "skipped"]),
            )
            .values(status="pending", error_code=None)
        )
        broadcast.status = "queued"
        broadcast.started_at = None
        broadcast.completed_at = None
        await session.commit()

        await crud.record_broadcast_event(
            session,
            broadcast_id=broadcast_id,
            event_type="requeued",
            admin_id=admin.id,
            payload={},
        )

        await self.queue.enqueue_broadcast(broadcast_id)
        return {"broadcast_id": broadcast_id, "status": "queued"}

    async def send_preview(
        self,
        payload: BroadcastPreviewPayload,
        admin: AdminUser,
    ) -> dict:
        sender = await self._get_preview_sender()
        message = await sender.send_message(
            telegram_id=payload.preview_chat_id,
            content_payload=payload.content.model_dump(exclude_none=True),
            content_type=payload.content_type,
        )
        logger.info("Preview sent to %s by %s", payload.preview_chat_id, admin.email)
        return {
            "preview_chat_id": payload.preview_chat_id,
            "message_id": message.message_id,
            "status": "sent",
        }

    async def _get_preview_sender(self) -> BroadcastSender:
        if self._preview_sender:
            return self._preview_sender
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._preview_sender = BroadcastSender(bot)
        return self._preview_sender

    @staticmethod
    def _requires_secondary_confirmation(total: int, explicit_flag: bool, admin_role: str) -> bool:
        if explicit_flag:
            return True
        if admin_role == "owner":
            return False
        return total >= settings.BROADCAST_APPROVAL_THRESHOLD

    @staticmethod
    def _build_broadcast_summary(
        broadcast: Broadcast,
        admin: AdminUser,
        stats: Dict[str, Any],
    ) -> BroadcastSummary:
        return BroadcastSummary(
            id=broadcast.id,
            title=broadcast.title,
            status=broadcast.status,
            channel=broadcast.channel,
            total_recipients=broadcast.total_recipients,
            stats=BroadcastStats(
                sent=int(stats.get("sent", 0)),
                failed=int(stats.get("failed", 0)),
                pending=int(stats.get("pending", 0)),
                skipped=int(stats.get("skipped", 0)),
            ),
            requires_approval=broadcast.requires_approval,
            scheduled_at=broadcast.scheduled_at,
            started_at=broadcast.started_at,
            completed_at=broadcast.completed_at,
            created_at=broadcast.created_at,
            updated_at=broadcast.updated_at,
            author=AdminSummary(
                id=admin.id,
                email=admin.email,
                role=admin.role,
            ),
        )


broadcast_service = BroadcastService()
