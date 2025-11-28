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


@router.post("/run")
async def run_migrations(db: AsyncSession = Depends(get_database_session)):
    """
    Виконати всі SQL міграції бази даних.
    
    ВАЖЛИВО: Цей endpoint має бути захищений в production!
    """
    try:
        migrations_dir = Path("/app/app/db/migrations")
        
        if not migrations_dir.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Директорія міграцій не знайдена: {migrations_dir}"
            )
        
        migrations = [
            "001_create_tracking_tables.sql",
            "002_create_simple_clicks_table.sql",
            "003_create_priority_products_table.sql",
        ]
        
        results = []
        successful = 0
        failed = 0
        
        for migration_file in migrations:
            migration_path = migrations_dir / migration_file
            
            if not migration_path.exists():
                logger.warning(f"⚠️ Файл міграції не знайдено: {migration_path}")
                results.append({
                    "file": migration_file,
                    "status": "skipped",
                    "message": "File not found"
                })
                failed += 1
                continue
            
            logger.info(f"📄 Виконуємо міграцію: {migration_file}")
            
            try:
                sql_content = migration_path.read_text(encoding='utf-8')
                
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
                            if "already exists" in error_str or "duplicate" in error_str:
                                skipped += 1
                            else:
                                logger.warning(f"⚠️ Помилка виконання команди: {e}")
                                raise
                
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
                logger.error(f"❌ Помилка виконання міграції {migration_file}: {e}")
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
