from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field

from app.db.database import get_database_session
from app.db.tracking_crud import (
    TrackingUserCRUD,
    TrackingClickCRUD,
    TrackingCampaignCRUD,
    TrackingSessionCRUD,
    TrackingLogCRUD,
)
from app.db.simple_click_crud import SimpleClickCRUD
from app.services.tracking.deep_link_validator import deep_link_validator
from app.services.tracking.analytics import tracking_analytics
from app.utils.logger import logger
from app.config import settings


router = APIRouter(tags=["tracking"])
redirect_router = APIRouter(tags=["redirect"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class UserRegisterRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram id")
    payload: Optional[str] = Field(None, description="Payload")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")


class UserRegisterResponse(BaseModel):
    success: bool
    user_uuid: str
    acquisition_source: str
    is_new_user: bool
    campaign_id: Optional[str] = None
    message: str


class TrackingClickRequest(BaseModel):
    user_uuid: str
    source: str
    page: str
    exchange: str
    ref_code: Optional[str] = None


# =============================================================================
# USER REGISTRATION ENDPOINT
# =============================================================================


@router.post("/user/register", response_model=UserRegisterResponse)
async def register_user(request: UserRegisterRequest) -> UserRegisterResponse:
    try:
        if not request.telegram_id or request.telegram_id <= 0:
            logger.warning(
                f"⚠️ Спроба реєстрації з невалідним telegram_id={request.telegram_id}. "
                f"Це може бути кеш або плейсхолдер. Блокуємо реєстрацію."
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid telegram_id: {request.telegram_id}. Must be positive integer.",
            )

        logger.info(
            f"📊 Реєстрація користувача: telegram_id={request.telegram_id}, payload={request.payload}"
        )

        is_valid, source, parsed_data = deep_link_validator.validate(request.payload)

        async with get_database_session() as session:
            if not is_valid:
                await TrackingLogCRUD.create(
                    session=session,
                    event_type="warning",
                    message=f"Invalid payload from user {request.telegram_id}: {request.payload}",
                    context={"payload": request.payload, "telegram_id": request.telegram_id},
                )

            existing_user = await TrackingUserCRUD.get_by_telegram_id(session, request.telegram_id)
            is_new_user = existing_user is None

            user = await TrackingUserCRUD.create_or_update(
                session=session, telegram_id=request.telegram_id, acquisition_source=source
            )

            campaign_id = None
            if parsed_data and parsed_data.get("campaign_id"):
                campaign_id = parsed_data["campaign_id"]
                platform = parsed_data.get("platform", "unknown")

                try:
                    await TrackingCampaignCRUD.create_or_update(
                        session=session,
                        campaign_id=campaign_id,
                        platform=platform,
                        description=f"Campaign {campaign_id} from {platform}",
                    )

                    if is_new_user and source != "organic":
                        await TrackingCampaignCRUD.increment_users(session, campaign_id)

                except Exception as e:
                    logger.error(f"❌ Помилка створення кампанії {campaign_id}: {e}")

            if campaign_id and not is_new_user:
                campaign = await TrackingCampaignCRUD.get_by_id(session, campaign_id)
                if campaign:
                    is_active, warning = deep_link_validator.validate_campaign_active(
                        campaign.end_date
                    )
                    if not is_active:
                        await TrackingLogCRUD.create(
                            session=session,
                            event_type="warning",
                            message=f"User from expired campaign: {campaign_id}",
                            user_uuid=user.user_uuid,
                            context={"campaign_id": campaign_id, "warning": warning},
                        )

            logger.info(
                f"✅ Користувач зареєстровано: uuid={user.user_uuid}, source={source}, new={is_new_user}"
            )

            return UserRegisterResponse(
                success=True,
                user_uuid=user.user_uuid,
                acquisition_source=source,
                is_new_user=is_new_user,
                campaign_id=campaign_id,
                message=f"User registered successfully ({'new' if is_new_user else 'existing'})",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка реєстрації користувача {request.telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/user/{telegram_id}")
async def get_user_info(telegram_id: int) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            user = await TrackingUserCRUD.get_by_telegram_id(session, telegram_id)

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True,
                "user_uuid": user.user_uuid,
                "acquisition_source": user.acquisition_source,
                "joined_at": user.joined_at.isoformat(),
                "last_activity": user.last_activity.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка отримання користувача {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# =============================================================================
# REDIRECT SERVER ENDPOINT
# =============================================================================


ALLOWED_EXCHANGES = [
    "binance",
    "bybit",
    "okx",
    "mexc",
    "bitmart",
    "gate",
    "bitget",
    "kraken",
    "kucoin",
    "htx",
    "nexo",
]


def get_exchange_referral_url(exchange: str) -> str:
    referral_map = {
        "binance": settings.referral_binance,
        "bybit": settings.referral_bybit,
        "okx": settings.referral_okx,
        "mexc": settings.referral_mexc,
        "bitmart": settings.referral_bitmart,
        "gate": settings.referral_gate,
        "bitget": settings.referral_bitget,
        "kraken": settings.referral_kraken,
        "kucoin": settings.referral_kucoin,
        "htx": settings.referral_htx,
        "nexo": settings.referral_nexo,
    }

    return referral_map.get(exchange.lower(), settings.referral_binance)


@redirect_router.get("")
async def redirect_with_tracking(
    request: Request,
    telegram_id: Optional[int] = Query(None, description="Last name"),
    user: Optional[str] = Query(None, description="Last name"),
    source: str = Query(default="organic", description="Last name"),
    page: str = Query(..., description="Last name"),
    exchange: str = Query(..., description="Last name"),
    ref_code: Optional[str] = Query(None, description="Last name"),
):
    try:
        effective_telegram_id = None

        if telegram_id and telegram_id > 0:
            effective_telegram_id = telegram_id
            logger.info(
                f"🔗 Redirect запит (новий формат): telegram_id={telegram_id}, exchange={exchange}, page={page}"
            )
        elif user:
            try:
                async with get_database_session() as session:
                    existing_user = await TrackingUserCRUD.get_by_uuid(session, user)
                    if existing_user:
                        effective_telegram_id = existing_user.telegram_id
                        logger.info(
                            f"🔗 Redirect запит (старий формат, знайдено): telegram_id={effective_telegram_id}, exchange={exchange}, page={page}"
                        )
                    else:
                        logger.warning(f"⚠️ UUID {user} не знайдено, клік не буде записано")
                        effective_telegram_id = None
            except Exception as e:
                logger.error(f"❌ Помилка пошуку користувача за UUID: {e}")
                effective_telegram_id = None
        else:
            logger.warning("⚠️ Відсутній telegram_id та user, клік не буде записано")

        if not all([page, exchange]):
            logger.warning("⚠️ Missing required parameters (page, exchange)")
            # Fallback redirect
            return RedirectResponse(
                url=get_exchange_referral_url(exchange.lower() if exchange else "binance"),
                status_code=302,
            )

        exchange_lower = exchange.lower()
        if exchange_lower not in ALLOWED_EXCHANGES:
            logger.warning(f"⚠️ Invalid exchange: {exchange}")
            # Fallback
            return RedirectResponse(url=settings.referral_binance, status_code=302)

        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        if effective_telegram_id and effective_telegram_id > 0:
            try:
                async with get_database_session() as session:
                    from app.db.simple_click_crud import SimpleClickCRUD

                    await SimpleClickCRUD.create(
                        session=session,
                        telegram_id=effective_telegram_id,
                        exchange=exchange_lower,
                        page=page,
                        source=source,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        ref_code=ref_code,
                    )
                    logger.info(
                        f"✅ Простий клік записано: telegram_id={effective_telegram_id}, "
                        f"exchange={exchange_lower}, page={page}"
                    )
            except Exception as e:
                logger.error(f"❌ Помилка запису простого кліку: {e}", exc_info=True)

        else:
            logger.warning(
                f"⚠️ Неможливо записати клік - відсутній валідний telegram_id. "
                f"telegram_id={telegram_id}, user={user}"
            )

        target_url = get_exchange_referral_url(exchange_lower)

        logger.info(f"✅ Redirect: {exchange_lower} -> {target_url}")

        return RedirectResponse(url=target_url, status_code=302)

    except Exception as e:
        logger.error(f"❌ Помилка redirect: {e}")
        # Fallback redirect
        return RedirectResponse(url=settings.referral_binance, status_code=302)


# =============================================================================

# =============================================================================


@router.get("/analytics/campaigns")
async def get_campaigns_analytics() -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            campaigns = await TrackingCampaignCRUD.get_all_active(session)

            campaigns_data = [
                {
                    "campaign_id": c.campaign_id,
                    "platform": c.platform,
                    "total_users": c.total_users,
                    "total_clicks": c.total_clicks,
                    "start_date": c.start_date.isoformat(),
                    "end_date": c.end_date.isoformat() if c.end_date else None,
                    "is_active": c.end_date is None
                    or c.end_date > datetime.now(UTC).replace(tzinfo=None),
                }
                for c in campaigns
            ]

            return {"success": True, "total_campaigns": len(campaigns), "campaigns": campaigns_data}

    except Exception as e:
        logger.error(f"❌ Помилка аналітики кампаній: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/user/{user_uuid}/clicks")
async def get_user_clicks(
    user_uuid: str, limit: int = Query(default=50, ge=1, le=500)
) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            clicks = await TrackingClickCRUD.get_by_user(session, user_uuid, limit)

            clicks_data = [
                {
                    "id": c.id,
                    "exchange": c.exchange,
                    "page": c.page,
                    "timestamp": c.timestamp.isoformat(),
                    "ref_code": c.ref_code,
                }
                for c in clicks
            ]

            return {
                "success": True,
                "user_uuid": user_uuid,
                "total_clicks": len(clicks),
                "clicks": clicks_data,
            }

    except Exception as e:
        logger.error(f"❌ Помилка отримання кліків: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/ctr")
async def get_ctr_analytics(
    start_date: Optional[str] = Query(None, description="Last name"),
    end_date: Optional[str] = Query(None, description="Last name"),
) -> Dict[str, Any]:
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        async with get_database_session() as session:
            ctr_data = await tracking_analytics.get_ctr_by_pages(
                session=session, start_date=start_dt, end_date=end_dt
            )

        return {"success": True, "total_pages": len(ctr_data), "data": ctr_data}
    except Exception as e:
        logger.error(f"❌ Помилка CTR аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/conversions")
async def get_conversions_analytics(
    source_pattern: Optional[str] = Query(None, description="Last name"),
) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            conversion_data = await tracking_analytics.get_conversion_rate(
                session=session, source_pattern=source_pattern
            )

        return {"success": True, "data": conversion_data}
    except Exception as e:
        logger.error(f"❌ Помилка conversions аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/popular-exchanges")
async def get_popular_exchanges(limit: int = Query(default=10, ge=1, le=50)) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            exchanges_data = await tracking_analytics.get_popular_exchanges(
                session=session, limit=limit
            )

        return {"success": True, "total_exchanges": len(exchanges_data), "data": exchanges_data}
    except Exception as e:
        logger.error(f"❌ Помилка popular exchanges аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/user-journey/{user_uuid}")
async def get_user_journey(user_uuid: str) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            journey_data = await tracking_analytics.get_user_journey(
                session=session, user_uuid=user_uuid
            )

        if "error" in journey_data:
            raise HTTPException(status_code=404, detail=journey_data["error"])

        return {"success": True, "data": journey_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка user journey аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/campaign-performance")
async def get_campaign_performance(
    campaign_id: Optional[str] = Query(None, description="Last name"),
) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            campaigns_data = await tracking_analytics.get_campaign_performance(
                session=session, campaign_id=campaign_id
            )

        return {"success": True, "total_campaigns": len(campaigns_data), "data": campaigns_data}
    except Exception as e:
        logger.error(f"❌ Помилка campaign performance аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/time-based")
async def get_time_based_analytics(
    period_hours: int = Query(default=24, ge=1, le=168),
) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            time_data = await tracking_analytics.get_time_based_analytics(
                session=session, period_hours=period_hours
            )

        return {"success": True, "data": time_data}
    except Exception as e:
        logger.error(f"❌ Помилка time-based аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/sources")
async def get_source_breakdown(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            sources_data = await tracking_analytics.get_source_breakdown(
                session=session, limit=limit
            )

        return {"success": True, "total_sources": len(sources_data), "data": sources_data}
    except Exception as e:
        logger.error(f"❌ Помилка sources аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/page-flow")
async def get_page_flow() -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            flow_data = await tracking_analytics.get_page_to_exchange_flow(session=session)

        return {"success": True, "data": flow_data}
    except Exception as e:
        logger.error(f"❌ Помилка page flow аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/analytics/recent-activity")
async def get_recent_activity(
    hours: int = Query(default=1, ge=1, le=24), limit: int = Query(default=50, ge=1, le=500)
) -> Dict[str, Any]:
    try:
        async with get_database_session() as session:
            activity_data = await tracking_analytics.get_recent_activity(
                session=session, hours=hours, limit=limit
            )

        return {
            "success": True,
            "total_clicks": len(activity_data),
            "period_hours": hours,
            "data": activity_data,
        }
    except Exception as e:
        logger.error(f"❌ Помилка recent activity аналітики: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


__all__ = ["router", "redirect_router"]
