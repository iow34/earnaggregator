#!/usr/bin/env python3
"""
Скрипт для тестування прямого підключення до Railway PostgreSQL.
Альтернатива MCP для перевірки доступності бази даних.
"""

import asyncio
import asyncpg
from urllib.parse import urlparse, parse_qs

# Railway DATABASE_PUBLIC_URL
DATABASE_URL = "postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway"

async def test_connection():
    """Тестує підключення до Railway PostgreSQL."""
    try:
        print("🔌 Підключення до Railway PostgreSQL...")
        print(f"📍 Host: maglev.proxy.rlwy.net:27723")
        print(f"📊 Database: railway")
        
        # Парсимо URL
        parsed = urlparse(DATABASE_URL)
        
        # Підключаємося
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            ssl='require'
        )
        
        print("✅ Підключення успішне!")
        
        # Тестуємо запит
        version = await conn.fetchval("SELECT version();")
        print(f"📋 PostgreSQL версія: {version[:50]}...")
        
        # Перевіряємо таблиці
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        print(f"\n📊 Знайдено таблиць: {len(tables)}")
        for table in tables[:10]:
            print(f"  - {table['table_name']}")
        
        if len(tables) > 10:
            print(f"  ... та ще {len(tables) - 10} таблиць")
        
        # Перевіряємо кількість записів у yield_products
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM yield_products;")
            print(f"\n📦 Записів у yield_products: {count}")
        except Exception as e:
            print(f"⚠️  Помилка підрахунку yield_products: {e}")
        
        # Перевіряємо priority_products
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM priority_products;")
            print(f"⭐ Записів у priority_products: {count}")
        except Exception as e:
            print(f"⚠️  Помилка підрахунку priority_products: {e}")
        
        await conn.close()
        print("\n✅ Тест завершено успішно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Помилка підключення: {e}")
        print(f"📝 Тип помилки: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)

