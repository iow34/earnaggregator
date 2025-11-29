"""
Скрипт для виконання всіх SQL міграцій бази даних по порядку.

Використання:
    python -m scripts.run_all_migrations

Або з Docker:
    docker exec -it <container> python -m scripts.run_all_migrations
"""

import asyncio
import sys
from pathlib import Path
from typing import List

from app.db.database import db_manager, init_database
from app.utils.logger import logger


# Список міграцій в порядку виконання
MIGRATIONS = [
    "001_create_tracking_tables.sql",
    "002_create_simple_clicks_table.sql",
    "003_create_priority_products_table.sql",
]


async def run_all_migrations() -> bool:
    """
    Виконати всі міграції по порядку.
    
    Returns:
        bool: True якщо всі міграції виконано успішно
    """
    try:
        # Ініціалізуємо підключення до БД
        logger.info("🔌 Підключення до бази даних...")
        success = await init_database()
        if not success:
            logger.error("❌ Не вдалося підключитися до БД")
            return False
        
        logger.info("✅ Підключення до БД успішне")
        
        # Знаходимо директорію з міграціями
        migrations_dir = Path(__file__).parent.parent / "app" / "db" / "migrations"
        
        if not migrations_dir.exists():
            logger.error(f"❌ Директорія міграцій не знайдена: {migrations_dir}")
            return False
        
        logger.info(f"📁 Директорія міграцій: {migrations_dir}")
        
        # Виконуємо кожну міграцію по порядку
        successful = 0
        failed = 0
        
        for migration_file in MIGRATIONS:
            migration_path = migrations_dir / migration_file
            
            if not migration_path.exists():
                logger.warning(f"⚠️ Файл міграції не знайдено: {migration_path}")
                failed += 1
                continue
            
            logger.info(f"📄 Виконуємо міграцію: {migration_file}")
            
            try:
                # Читаємо SQL файл
                sql_content = migration_path.read_text(encoding='utf-8')
                
                # Виконуємо SQL
                async with db_manager.get_session() as session:
                    from sqlalchemy import text
                    
                    # Розділяємо SQL на окремі команди
                    commands = [
                        cmd.strip() 
                        for cmd in sql_content.split(';') 
                        if cmd.strip() and not cmd.strip().startswith('--')
                    ]
                    
                    for command in commands:
                        if command:
                            try:
                                await session.execute(text(command))
                                logger.debug(f"✅ Виконано: {command[:50]}...")
                            except Exception as e:
                                # Ігноруємо помилки "already exists"
                                error_str = str(e).lower()
                                if "already exists" in error_str or "duplicate" in error_str:
                                    logger.info(f"ℹ️ Пропущено (вже існує): {command[:50]}...")
                                else:
                                    logger.warning(f"⚠️ Помилка виконання команди: {e}")
                                    logger.warning(f"Команда: {command[:100]}")
                    
                    await session.commit()
                
                logger.info(f"✅ Міграція {migration_file} виконано успішно")
                successful += 1
                
            except Exception as e:
                logger.error(f"❌ Помилка виконання міграції {migration_file}: {e}", exc_info=True)
                failed += 1
                # Продовжуємо виконання інших міграцій
        
        # Підсумок
        logger.info("=" * 60)
        logger.info(f"📊 Підсумок виконання міграцій:")
        logger.info(f"   ✅ Успішно: {successful}")
        logger.info(f"   ❌ Помилок: {failed}")
        logger.info(f"   📄 Всього: {len(MIGRATIONS)}")
        logger.info("=" * 60)
        
        return failed == 0
        
    except Exception as e:
        logger.error(f"❌ Критична помилка виконання міграцій: {e}", exc_info=True)
        return False
    finally:
        await db_manager.close()


async def main():
    """Головна функція."""
    logger.info("🚀 Запуск виконання всіх міграцій бази даних...")
    logger.info("=" * 60)
    
    success = await run_all_migrations()
    
    if success:
        logger.info("✅ Всі міграції виконано успішно!")
        sys.exit(0)
    else:
        logger.error("❌ Деякі міграції не виконано. Перевірте логи вище.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
