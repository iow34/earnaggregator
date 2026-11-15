from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot.broadcasts.api import router as broadcast_router
from bot.db.database import db_manager
from bot.utils.logger import logger
from bot.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        if not await db_manager.initialize():
            raise RuntimeError("Database initialization failed")
        logger.info("✅ Database initialized for Broadcast Admin API")
    except Exception as e:
        logger.error(f"⚠️ Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    try:
        await db_manager.close_engine()
        logger.info("✅ Database closed for Broadcast Admin API")
    except Exception as e:
        logger.error(f"⚠️ Error closing database: {e}")


app = FastAPI(title="EarnAggregator Broadcast Admin API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BROADCAST_ADMIN_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(broadcast_router)
