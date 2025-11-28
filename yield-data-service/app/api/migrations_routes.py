"""
API endpoints для виконання міграцій бази даних.
Використовується для ручного запуску міграцій через HTTP запит.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from sqlalchemy import text

from app.db.database import get_database_session
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/migrations", tags=["migrations"])

# SQL міграції вбудовані напряму (на випадок, якщо файли не доступні)
MIGRATION_001 = """
CREATE TABLE IF NOT EXISTS tracking_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    user_uuid VARCHAR(36) UNIQUE NOT NULL,
    acquisition_source VARCHAR(255) NOT NULL,
    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracking_telegram_id ON tracking_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tracking_user_uuid ON tracking_users(user_uuid);
CREATE INDEX IF NOT EXISTS idx_tracking_source ON tracking_users(acquisition_source);
CREATE INDEX IF NOT EXISTS idx_tracking_joined_at ON tracking_users(joined_at);

CREATE TABLE IF NOT EXISTS tracking_clicks (
    id SERIAL PRIMARY KEY,
    user_uuid VARCHAR(36) NOT NULL REFERENCES tracking_users(user_uuid) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    page VARCHAR(50) NOT NULL,
    exchange VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    ref_code VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_tracking_click_uuid ON tracking_clicks(user_uuid);
CREATE INDEX IF NOT EXISTS idx_tracking_click_source ON tracking_clicks(source);
CREATE INDEX IF NOT EXISTS idx_tracking_click_page ON tracking_clicks(page);
CREATE INDEX IF NOT EXISTS idx_tracking_click_exchange ON tracking_clicks(exchange);
CREATE INDEX IF NOT EXISTS idx_tracking_click_timestamp ON tracking_clicks(timestamp);

CREATE TABLE IF NOT EXISTS tracking_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    description TEXT,
    total_users INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracking_campaign_id ON tracking_campaigns(campaign_id);

CREATE TABLE IF NOT EXISTS tracking_sessions (
    id SERIAL PRIMARY KEY,
    user_uuid VARCHAR(36) NOT NULL REFERENCES tracking_users(user_uuid) ON DELETE CASCADE,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    source VARCHAR(255) NOT NULL,
    session_start TIMESTAMP NOT NULL DEFAULT NOW(),
    session_end TIMESTAMP,
    total_clicks INTEGER DEFAULT 0,
    total_time INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tracking_session_uuid ON tracking_sessions(user_uuid);

CREATE TABLE IF NOT EXISTS tracking_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    user_uuid VARCHAR(36),
    context JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracking_log_type ON tracking_logs(event_type);
"""

MIGRATION_002 = """
CREATE TABLE IF NOT EXISTS simple_clicks (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    source VARCHAR(255) NOT NULL DEFAULT 'organic',
    page VARCHAR(50) NOT NULL,
    exchange VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    ref_code VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_simple_click_telegram_id ON simple_clicks(telegram_id);
CREATE INDEX IF NOT EXISTS idx_simple_click_source ON simple_clicks(source);
CREATE INDEX IF NOT EXISTS idx_simple_click_page ON simple_clicks(page);
CREATE INDEX IF NOT EXISTS idx_simple_click_exchange ON simple_clicks(exchange);
CREATE INDEX IF NOT EXISTS idx_simple_click_timestamp ON simple_clicks(timestamp);
CREATE INDEX IF NOT EXISTS idx_simple_click_source_exchange ON simple_clicks(source, exchange);
CREATE INDEX IF NOT EXISTS idx_simple_click_page_exchange ON simple_clicks(page, exchange);
CREATE INDEX IF NOT EXISTS idx_simple_click_telegram_exchange ON simple_clicks(telegram_id, exchange);
"""

MIGRATION_003 = """
CREATE TABLE IF NOT EXISTS priority_products (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    apy DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    product_id VARCHAR(100),
    lock_period_days INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_priority_exchange_symbol UNIQUE (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS idx_priority_exchange_symbol ON priority_products(exchange, symbol);
CREATE INDEX IF NOT EXISTS idx_priority_exchange ON priority_products(exchange);
CREATE INDEX IF NOT EXISTS idx_priority_symbol ON priority_products(symbol);
CREATE INDEX IF NOT EXISTS idx_priority_updated_at ON priority_products(updated_at);
"""


@router.post("/run")
async def run_migrations(db: AsyncSession = Depends(get_database_session)):
    """
    Виконати всі SQL міграції бази даних.
    
    ВАЖЛИВО: Цей endpoint має бути захищений в production!
    """
    try:
        migrations = [
            ("001_create_tracking_tables.sql", MIGRATION_001),
            ("002_create_simple_clicks_table.sql", MIGRATION_002),
            ("003_create_priority_products_table.sql", MIGRATION_003),
        ]
        
        results = []
        successful = 0
        failed = 0
        
        for migration_file, sql_content in migrations:
            logger.info(f"📄 Виконуємо міграцію: {migration_file}")
            
            try:
                # Розділяємо SQL на окремі команди
                commands = [
                    cmd.strip() 
                    for cmd in sql_content.split(';') 
                    if cmd.strip() and not cmd.strip().startswith('--')
                ]
                
                executed = 0
                skipped = 0
                
                for command in commands:
                    if command:
                        try:
                            await db.execute(text(command))
                            executed += 1
                        except Exception as e:
                            error_str = str(e).lower()
                            if "already exists" in error_str or "duplicate" in error_str or "already defined" in error_str:
                                skipped += 1
                                logger.debug(f"ℹ️ Пропущено (вже існує): {command[:50]}...")
                            else:
                                logger.warning(f"⚠️ Помилка виконання команди: {e}")
                                logger.warning(f"Команда: {command[:100]}")
                                # Продовжуємо виконання інших команд
                
                await db.commit()
                
                logger.info(f"✅ Міграція {migration_file} виконано успішно")
                results.append({
                    "file": migration_file,
                    "status": "success",
                    "executed_commands": executed,
                    "skipped_commands": skipped
                })
                successful += 1
                
            except Exception as e:
                logger.error(f"❌ Помилка виконання міграції {migration_file}: {e}", exc_info=True)
                results.append({
                    "file": migration_file,
                    "status": "error",
                    "message": str(e)
                })
                failed += 1
        
        return {
            "status": "completed",
            "total": len(migrations),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Критична помилка виконання міграцій: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Помилка виконання міграцій: {str(e)}")
