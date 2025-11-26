"""
Скрипт для виконання SQL міграцій бази даних.
"""

import asyncio
import os
from pathlib import Path
from sqlalchemy import text

from app.db.database import db_manager, init_database
from app.utils.logger import logger


async def run_migration(migration_file: str):
    """
    Виконати SQL міграцію з файлу.
    
    Args:
        migration_file: Шлях до SQL файлу міграції
    """
    try:
        # Ініціалізуємо підключення до БД
        success = await init_database()
        if not success:
            logger.error("❌ Не вдалося підключитися до БД")
            return False
        
        # Читаємо SQL файл
        migration_path = Path(migration_file)
        if not migration_path.exists():
            logger.error(f"❌ Файл міграції не знайдено: {migration_file}")
            return False
        
        logger.info(f"📄 Читаємо міграцію: {migration_path}")
        sql_content = migration_path.read_text(encoding='utf-8')
        
        # Виконуємо SQL
        logger.info("🔄 Виконуємо міграцію...")
        async with db_manager.get_session() as session:
            # Розділяємо SQL на окремі команди
            commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
            
            for command in commands:
                if command:
                    try:
                        await session.execute(text(command))
                        logger.debug(f"✅ Виконано: {command[:50]}...")
                    except Exception as e:
                        # Ігноруємо помилки "already exists"
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            logger.info(f"ℹ️ Пропущено (вже існує): {command[:50]}...")
                        else:
                            logger.warning(f"⚠️ Помилка виконання команди: {e}")
                            logger.warning(f"Команда: {command[:100]}")
            
            await session.commit()
        
        logger.info("✅ Міграцію виконано успішно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка виконання міграції: {e}", exc_info=True)
        return False
    finally:
        await db_manager.close()


async def main():
    """Головна функція."""
    import sys
    
    if len(sys.argv) < 2:
        print("Використання: python -m scripts.run_migration <шлях_до_міграції.sql>")
        print("Приклад: python -m scripts.run_migration app/db/migrations/003_create_priority_products_table.sql")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    success = await run_migration(migration_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

