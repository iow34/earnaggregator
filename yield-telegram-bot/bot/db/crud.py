import hashlib

from datetime import datetime, timedelta, UTC
from typing import Optional

from sqlalchemy import select, update, func, desc, or_, case, and_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import (
    TelegramUser,
    UserQuery,
    ReferralClick,
    UserAction,
    AdminUser,
    Broadcast,
    BroadcastRecipient,
    BroadcastEvent,
)
from bot.utils.logger import logger


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language: str = "ua",
) -> TelegramUser:

    stmt = select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        update_data = {"last_seen": datetime.utcnow()}
        if username != user.username:
            update_data["username"] = username
        if first_name != user.first_name:
            update_data["first_name"] = first_name
        if last_name != user.last_name:
            update_data["last_name"] = last_name

        if len(update_data) > 1:
            stmt = update(TelegramUser).where(TelegramUser.id == user.id).values(**update_data)
            await session.execute(stmt)
            await session.commit()
            await session.refresh(user)

        logger.info(f"Існуючий користувач: {user}")
        return user

    new_user = TelegramUser(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language=language,
        is_active=True,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    logger.info(f"Новий користувач створений: {new_user}")
    return new_user


async def update_user_language(session: AsyncSession, telegram_id: int, language: str) -> bool:
    stmt = (
        update(TelegramUser)
        .where(TelegramUser.telegram_id == telegram_id)
        .values(language=language, updated_at=func.now())
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def add_user_query(
    session: AsyncSession,
    user_id: int,
    query_type: str,
    symbol: Optional[str] = None,
    limit: Optional[int] = None,
) -> UserQuery:
    query = UserQuery(
        user_id=user_id,
        query_type=query_type,
        symbol=symbol,
        limit=limit,
    )
    session.add(query)
    await session.commit()
    await session.refresh(query)

    logger.info(f"Запит користувача додано: {query}")
    return query


async def add_referral_click(
    session: AsyncSession,
    user_id: int,
    exchange: str,
    symbol: Optional[str] = None,
) -> ReferralClick:
    click = ReferralClick(
        user_id=user_id,
        exchange=exchange,
        symbol=symbol,
    )
    session.add(click)
    await session.commit()
    await session.refresh(click)

    logger.info(f"Реферальний клік додано: {click}")
    return click


async def update_user_subscription(
    session: AsyncSession,
    telegram_id: int,
    is_subscribed: bool,
) -> bool:
    stmt = (
        update(TelegramUser)
        .where(TelegramUser.telegram_id == telegram_id)
        .values(is_subscribed=is_subscribed, updated_at=func.now())
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def add_user_tags(
    session: AsyncSession,
    telegram_id: int,
    tags: list[str],
) -> Optional[TelegramUser]:
    stmt = select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return None

    existing = set(user.tags or [])
    existing.update(tag for tag in tags if tag)
    user.tags = sorted(existing)
    await session.commit()
    await session.refresh(user)
    return user


async def filter_users_for_broadcast(
    session: AsyncSession,
    filters: dict,
    limit: int = 500,
    offset: int = 0,
) -> list[TelegramUser]:
    stmt = select(TelegramUser).where(TelegramUser.is_active.is_(True))

    if (is_subscribed := filters.get("is_subscribed")) is not None:
        stmt = stmt.where(TelegramUser.is_subscribed.is_(bool(is_subscribed)))

    if languages := filters.get("languages"):
        stmt = stmt.where(TelegramUser.language.in_(languages))

    if tags_all := filters.get("tags_all"):
        stmt = stmt.where(TelegramUser.tags.contains(tags_all))

    if tags_any := filters.get("tags_any"):
        expressions = [TelegramUser.tags.contains([tag]) for tag in tags_any if tag]
        if expressions:
            stmt = stmt.where(or_(*expressions))

    if after := filters.get("last_active_after"):
        stmt = stmt.where(TelegramUser.last_active_at >= after)

    if telegram_ids := filters.get("telegram_ids"):
        stmt = stmt.where(TelegramUser.telegram_id.in_(telegram_ids))

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


def _recipient_stats_subquery():
    return (
        select(
            BroadcastRecipient.broadcast_id.label("broadcast_id"),
            func.count(BroadcastRecipient.id).label("total"),
            func.sum(case((BroadcastRecipient.status == "sent", 1), else_=0)).label("sent"),
            func.sum(case((BroadcastRecipient.status == "failed", 1), else_=0)).label("failed"),
            func.sum(case((BroadcastRecipient.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((BroadcastRecipient.status == "skipped", 1), else_=0)).label("skipped"),
        )
        .group_by(BroadcastRecipient.broadcast_id)
        .subquery()
    )


def _apply_broadcast_filters(stmt, filters: dict):
    if not filters:
        return stmt
    if status := filters.get("status"):
        stmt = stmt.where(Broadcast.status == status)
    if channel := filters.get("channel"):
        stmt = stmt.where(Broadcast.channel == channel)
    if author_id := filters.get("author_id"):
        stmt = stmt.where(Broadcast.author_admin_id == author_id)
    if (requires_approval := filters.get("requires_approval")) is not None:
        stmt = stmt.where(Broadcast.requires_approval.is_(requires_approval))
    if scheduled_from := filters.get("scheduled_from"):
        stmt = stmt.where(Broadcast.scheduled_at >= scheduled_from)
    if scheduled_to := filters.get("scheduled_to"):
        stmt = stmt.where(Broadcast.scheduled_at <= scheduled_to)
    if search := filters.get("search"):
        stmt = stmt.where(Broadcast.title.ilike(f"%{search}%"))
    return stmt


async def list_broadcasts(
    session: AsyncSession,
    filters: dict,
    page: int,
    per_page: int,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    offset = (page - 1) * per_page

    total_stmt = select(func.count(Broadcast.id))
    total_stmt = _apply_broadcast_filters(total_stmt, filters)
    total = (await session.execute(total_stmt)).scalar() or 0

    stats_subq = _recipient_stats_subquery()

    sort_map = {
        "created_at": Broadcast.created_at,
        "scheduled_at": Broadcast.scheduled_at,
        "title": Broadcast.title,
        "status": Broadcast.status,
    }
    sort_column = sort_map.get(sort_by, Broadcast.created_at)
    order_clause = sort_column.desc() if sort_dir.lower() == "desc" else sort_column.asc()

    stmt = (
        select(
            Broadcast,
            AdminUser,
            func.coalesce(stats_subq.c.sent, 0).label("sent"),
            func.coalesce(stats_subq.c.failed, 0).label("failed"),
            func.coalesce(stats_subq.c.pending, 0).label("pending"),
            func.coalesce(stats_subq.c.skipped, 0).label("skipped"),
        )
        .join(AdminUser, AdminUser.id == Broadcast.author_admin_id)
        .outerjoin(stats_subq, stats_subq.c.broadcast_id == Broadcast.id)
        .order_by(order_clause)
        .offset(offset)
        .limit(per_page)
    )
    stmt = _apply_broadcast_filters(stmt, filters)
    result = await session.execute(stmt)
    rows = result.all()
    return rows, total


async def get_broadcast_with_stats(session: AsyncSession, broadcast_id: int):
    stats_subq = _recipient_stats_subquery()
    stmt = (
        select(
            Broadcast,
            AdminUser,
            func.coalesce(stats_subq.c.sent, 0).label("sent"),
            func.coalesce(stats_subq.c.failed, 0).label("failed"),
            func.coalesce(stats_subq.c.pending, 0).label("pending"),
            func.coalesce(stats_subq.c.skipped, 0).label("skipped"),
        )
        .join(AdminUser, AdminUser.id == Broadcast.author_admin_id)
        .outerjoin(stats_subq, stats_subq.c.broadcast_id == Broadcast.id)
        .where(Broadcast.id == broadcast_id)
    )
    result = await session.execute(stmt)
    return result.first()


async def get_broadcast_events(
    session: AsyncSession,
    broadcast_id: int,
    page: int,
    per_page: int,
):
    offset = (page - 1) * per_page
    total_stmt = select(func.count(BroadcastEvent.id)).where(
        BroadcastEvent.broadcast_id == broadcast_id
    )
    total = (await session.execute(total_stmt)).scalar() or 0

    stmt = (
        select(BroadcastEvent, AdminUser)
        .outerjoin(AdminUser, AdminUser.id == BroadcastEvent.admin_id)
        .where(BroadcastEvent.broadcast_id == broadcast_id)
        .order_by(BroadcastEvent.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    rows = (await session.execute(stmt)).all()
    return rows, total


async def get_broadcast_recipients(
    session: AsyncSession,
    broadcast_id: int,
    status: Optional[str],
    page: int,
    per_page: int,
    search: Optional[str] = None,
):
    offset = (page - 1) * per_page
    base_stmt = select(BroadcastRecipient).where(BroadcastRecipient.broadcast_id == broadcast_id)
    if status:
        base_stmt = base_stmt.where(BroadcastRecipient.status == status)
    if search:
        base_stmt = base_stmt.where(
            or_(
                cast(BroadcastRecipient.telegram_id, String).ilike(f"%{search}%"),
                BroadcastRecipient.message_id.ilike(f"%{search}%"),
                BroadcastRecipient.error_code.ilike(f"%{search}%"),
            )
        )
    total = (
        await session.execute(select(func.count()).select_from(base_stmt.subquery()))
    ).scalar() or 0

    stmt = base_stmt.order_by(BroadcastRecipient.id).offset(offset).limit(per_page)
    rows = (await session.execute(stmt)).scalars().all()
    return rows, total


async def get_dashboard_metrics(session: AsyncSession):
    status_counts_stmt = select(Broadcast.status, func.count()).group_by(Broadcast.status)
    result = await session.execute(status_counts_stmt)
    status_counts = dict(result.all())

    total = sum(status_counts.values())
    active = sum(status_counts.get(status, 0) for status in ("running", "queued"))
    scheduled = status_counts.get("scheduled", 0)
    pending_approval = status_counts.get("pending_approval", 0)

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    sent_today_stmt = select(func.count()).where(
        BroadcastRecipient.status == "sent",
        BroadcastRecipient.last_attempt_at >= today_start,
    )
    failed_today_stmt = select(func.count()).where(
        BroadcastRecipient.status == "failed",
        BroadcastRecipient.last_attempt_at >= today_start,
    )

    sent_today = (await session.execute(sent_today_stmt)).scalar() or 0
    failed_today = (await session.execute(failed_today_stmt)).scalar() or 0

    return {
        "total_broadcasts": total,
        "active_broadcasts": active,
        "scheduled_broadcasts": scheduled,
        "pending_approval": pending_approval,
        "sent_today": sent_today,
        "failed_today": failed_today,
    }


async def get_user_stats(session: AsyncSession, user_id: int) -> dict:

    stmt = select(UserQuery).where(UserQuery.user_id == user_id)
    result = await session.execute(stmt)
    queries = result.scalars().all()

    stmt = select(ReferralClick).where(ReferralClick.user_id == user_id)
    result = await session.execute(stmt)
    clicks = result.scalars().all()

    return {
        "total_queries": len(queries),
        "total_clicks": len(clicks),
        "query_types": list(set(q.query_type for q in queries)),
        "click_exchanges": list(set(c.exchange for c in clicks)),
    }


async def get_user_action_stats(session: AsyncSession, user_id: int, days: int = 7) -> dict:
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    stmt = select(func.count(UserAction.id)).where(
        UserAction.user_id == user_id, UserAction.timestamp >= cutoff_date
    )
    result = await session.execute(stmt)
    total_actions = result.scalar()

    stmt = (
        select(UserAction.action_type, func.count(UserAction.id))
        .where(UserAction.user_id == user_id, UserAction.timestamp >= cutoff_date)
        .group_by(UserAction.action_type)
    )

    result = await session.execute(stmt)
    actions_by_type = dict(result.fetchall())

    stmt = select(func.avg(UserAction.latency_ms)).where(
        UserAction.user_id == user_id,
        UserAction.timestamp >= cutoff_date,
        UserAction.latency_ms.isnot(None),
    )
    result = await session.execute(stmt)
    avg_latency = result.scalar()

    return {
        "total_actions": total_actions,
        "actions_by_type": actions_by_type,
        "period_days": days,
        "avg_latency_ms": round(avg_latency, 2) if avg_latency else None,
    }


async def get_popular_actions(session: AsyncSession, days: int = 7, limit: int = 10) -> list:
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    stmt = (
        select(UserAction.action_type, func.count(UserAction.id).label("count"))
        .where(UserAction.timestamp >= cutoff_date)
        .group_by(UserAction.action_type)
        .order_by(desc("count"))
        .limit(limit)
    )

    result = await session.execute(stmt)
    return [{"action_type": row[0], "count": row[1]} for row in result.fetchall()]


async def get_referral_stats(
    session: AsyncSession, days: int = 30, exchange: Optional[str] = None
) -> dict:
    import json

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    base_query = select(UserAction).where(
        UserAction.action_type == "referral_click", UserAction.timestamp >= cutoff_date
    )

    if exchange:
        result = await session.execute(base_query)
        all_clicks = result.scalars().all()

        filtered_clicks = []
        for click in all_clicks:
            if click.context:
                try:
                    context = (
                        json.loads(click.context)
                        if isinstance(click.context, str)
                        else click.context
                    )
                    if context.get("exchange") == exchange:
                        filtered_clicks.append(click)
                except:
                    continue

        total_clicks = len(filtered_clicks)

        symbols_count = {}
        for click in filtered_clicks:
            try:
                context = (
                    json.loads(click.context) if isinstance(click.context, str) else click.context
                )
                symbol = context.get("symbol", "unknown")
                symbols_count[symbol] = symbols_count.get(symbol, 0) + 1
            except:
                continue
    else:
        result = await session.execute(base_query)
        all_clicks = result.scalars().all()
        total_clicks = len(all_clicks)

        exchanges_count = {}
        symbols_count = {}

        for click in all_clicks:
            if click.context:
                try:
                    context = (
                        json.loads(click.context)
                        if isinstance(click.context, str)
                        else click.context
                    )
                    exchange_name = context.get("exchange", "unknown")
                    symbol = context.get("symbol", "none")

                    exchanges_count[exchange_name] = exchanges_count.get(exchange_name, 0) + 1
                    symbols_count[symbol] = symbols_count.get(symbol, 0) + 1
                except:
                    continue

    unique_users = len(set(click.user_id for click in all_clicks))

    result_stats = {
        "total_clicks": total_clicks,
        "unique_users": unique_users,
        "period_days": days,
        "symbols": symbols_count,
    }

    if not exchange:
        result_stats["exchanges"] = exchanges_count

    return result_stats


async def get_top_referral_exchanges(
    session: AsyncSession, days: int = 30, limit: int = 10
) -> list:
    import json

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    stmt = select(UserAction).where(
        UserAction.action_type == "referral_click", UserAction.timestamp >= cutoff_date
    )

    result = await session.execute(stmt)
    all_clicks = result.scalars().all()

    exchanges_count = {}

    for click in all_clicks:
        if click.context:
            try:
                context = (
                    json.loads(click.context) if isinstance(click.context, str) else click.context
                )
                exchange = context.get("exchange", "unknown")
                exchanges_count[exchange] = exchanges_count.get(exchange, 0) + 1
            except:
                continue

    sorted_exchanges = sorted(exchanges_count.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [{"exchange": exchange, "count": count} for exchange, count in sorted_exchanges]


async def get_admin_by_email(session: AsyncSession, email: str) -> Optional[AdminUser]:
    stmt = select(AdminUser).where(AdminUser.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_admin_by_api_key(session: AsyncSession, api_key: str) -> Optional[AdminUser]:
    stmt = select(AdminUser).where(
        AdminUser.api_key == hashlib.sha256(api_key.encode()).hexdigest(),
        AdminUser.is_active.is_(True),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_admin_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    api_key: str,
    role: str,
) -> AdminUser:
    admin = AdminUser(
        email=email,
        password_hash=password_hash,
        api_key=hashlib.sha256(api_key.encode()).hexdigest(),
        role=role,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def record_admin_login(session: AsyncSession, admin_id: int) -> None:
    stmt = update(AdminUser).where(AdminUser.id == admin_id).values(last_login_at=func.now())
    await session.execute(stmt)
    await session.commit()


async def record_broadcast_event(
    session: AsyncSession,
    *,
    broadcast_id: int,
    event_type: str,
    admin_id: Optional[int],
    payload: dict,
) -> BroadcastEvent:
    event = BroadcastEvent(
        broadcast_id=broadcast_id,
        admin_id=admin_id,
        event_type=event_type,
        payload=payload,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event
