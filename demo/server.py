"""Run the catalogue and broadcast UI without exchange or Telegram credentials.

State belongs to this application instance and resets on restart. No sender,
worker, database, scheduler or exchange adapter is imported here.
"""

from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

PRODUCTS = [
    {
        "id": f"sample-{i}",
        "symbol": symbol,
        "name": f"{symbol} {kind}",
        "provider": provider,
        "apy": apy,
        "lock_period_days": days,
        "product_type": kind,
        "min_amount": 0.01,
        "is_active": True,
    }
    for i, (symbol, provider, apy, days, kind) in enumerate(
        [
            ("USDT", "Binance", 4.2, 0, "Flexible"),
            ("USDT", "Bybit", 5.1, 30, "Fixed"),
            ("BTC", "Binance", 1.2, 0, "Flexible"),
            ("ETH", "OKX", 2.8, 14, "Fixed"),
            ("SOL", "Bitget", 3.5, 7, "Fixed"),
            ("USDC", "Gate", 4.0, 0, "Flexible"),
            ("BTC", "Kraken", 1.8, 30, "Fixed"),
            ("ETH", "Bybit", 2.5, 0, "Flexible"),
        ],
        1,
    )
]


class Content(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    parse_mode: str = "HTML"


class BroadcastInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: Content
    filters: dict = Field(default_factory=dict)
    requires_approval: bool = False
    scheduled_at: datetime | None = None
    channel: str = "web_ui"
    batch_size: int = Field(default=100, ge=1, le=1000)


def create_app() -> FastAPI:
    app = FastAPI(title="EarnAggregator interactive preview", version="1.1.0")
    lock = Lock()
    records: dict[int, dict] = {}

    def summary(identifier: int, payload: BroadcastInput) -> dict:
        now = datetime.now(UTC).isoformat()
        return {
            "id": identifier,
            "title": payload.title,
            "status": "draft",
            "channel": payload.channel,
            "total_recipients": 0,
            "stats": {"sent": 0, "failed": 0, "pending": 0, "skipped": 0},
            "requires_approval": payload.requires_approval,
            "scheduled_at": payload.scheduled_at.isoformat() if payload.scheduled_at else None,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
            "updated_at": now,
            "author": {"id": 1, "email": "preview@example.com", "role": "owner"},
        }

    seed = BroadcastInput(
        title="Weekly Earn digest",
        content=Content(text="Compare flexible and fixed Earn products across exchanges."),
    )
    records[1] = {
        "broadcast": summary(1, seed),
        "content": seed.content.model_dump(),
        "filters": {},
        "metadata": {"synthetic": True},
        "preview_chat_id": None,
        "batch_size": 100,
    }

    @app.middleware("http")
    async def preview_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-EarnAggregator-Mode"] = "synthetic-preview"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "healthy", "mode": "synthetic-preview", "external_connections": False}

    @app.get("/api/v1/products")
    def products(symbol: str | None = None, provider: str | None = None):
        items = [
            p
            for p in PRODUCTS
            if (not symbol or p["symbol"] == symbol.upper())
            and (not provider or p["provider"].lower() == provider.lower())
        ]
        return {
            "success": True,
            "source": "synthetic-preview",
            "data": sorted(items, key=lambda p: p["apy"], reverse=True),
            "count": len(items),
        }

    @app.get("/api/broadcasts/metrics/summary")
    def metrics():
        with lock:
            return {
                "total_broadcasts": len(records),
                "active_broadcasts": 0,
                "scheduled_broadcasts": 0,
                "pending_approval": 0,
                "sent_today": 0,
                "failed_today": 0,
            }

    @app.get("/api/broadcasts")
    def broadcasts(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        search: str = "",
        status: str | None = None,
    ):
        with lock:
            items = [
                deepcopy(r["broadcast"])
                for r in reversed(list(records.values()))
                if search.lower() in r["broadcast"]["title"].lower()
                and (not status or r["broadcast"]["status"] == status)
            ]
        return {
            "items": items[(page - 1) * per_page : page * per_page],
            "total": len(items),
            "page": page,
            "per_page": per_page,
        }

    @app.post("/api/broadcasts", status_code=201)
    def create(payload: BroadcastInput):
        with lock:
            if len(records) >= 100:
                raise HTTPException(409, "Preview capacity reached; restart to reset")
            identifier = len(records) + 1
            records[identifier] = {
                "broadcast": summary(identifier, payload),
                "content": payload.content.model_dump(),
                "filters": payload.filters,
                "metadata": {"synthetic": True},
                "preview_chat_id": None,
                "batch_size": payload.batch_size,
            }
        return {"broadcast_id": identifier, "status": "draft"}

    @app.get("/api/broadcasts/{identifier}")
    def detail(identifier: int):
        with lock:
            if identifier not in records:
                raise HTTPException(404, "Broadcast not found")
            return deepcopy(records[identifier])

    return app


app = create_app()
