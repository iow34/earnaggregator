import asyncio
import sys
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import init_database, create_tables, db_manager
from app.utils.logger import logger


async def create_priority_products_table():
    try:
        logger.info("🚀 Початок створення таблиці priority_products...")

        success = await init_database()
        if not success:
            logger.error("❌ Не вдалося підключитися до БД")
            return False

        await create_tables()

        logger.info("✅ Таблиця priority_products створена/перевірена")
        return True

    except Exception as e:
        logger.error(f"❌ Помилка створення таблиці: {e}", exc_info=True)
        return False
    finally:
        await db_manager.close()


if __name__ == "__main__":
    success = asyncio.run(create_priority_products_table())
    sys.exit(0 if success else 1)
