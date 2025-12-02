#!/usr/bin/env python3
"""
Скрипт для тестування прямого підключення до Railway PostgreSQL.
Альтернатива MCP для перевірки доступності бази даних.
"""

import asyncio
import asyncpg
from urllib.parse import urlparse, parse_qs

# Railway DATABASE_PUBLIC_URL
DATABASE_URL = "postgresql://postgres:REMOVED_RAILWAY_POSTGRES_PASSWORD@maglev.proxy.rlwy.net:27723/railway"

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

        # Перевіряємо HTX продукти
        try:
            htx_count = await conn.fetchval("SELECT COUNT(*) FROM yield_products WHERE provider = 'HTX' AND is_active = true;")
            print(f"🏦 HTX активних продуктів: {htx_count}")

            # Перевіряємо топ 5 HTX продуктів
            htx_products = await conn.fetch("""
                SELECT id, symbol, name, apy, product_type
                FROM yield_products
                WHERE provider = 'HTX' AND is_active = true
                ORDER BY apy DESC
                LIMIT 5
            """)
            print("\n🏦 Топ 5 HTX продуктів:")
            for product in htx_products:
                print(f"  - {product['symbol']}: {product['apy']}% APY ({product['product_type']})")

        except Exception as e:
            print(f"⚠️  Помилка підрахунку HTX продуктів: {e}")

        # Перевіряємо priority_products
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM priority_products;")
            print(f"⭐ Записів у priority_products: {count}")
        except Exception as e:
            print(f"⚠️  Помилка підрахунку priority_products: {e}")
        
        # Тестуємо імітацію роботи телеграм бота з HTX
        try:
            print("\n🤖 Тестуємо імітацію HTX логіки телеграм бота...")

            # Імітуємо отримання HTX продуктів через YieldProductCRUD
            htx_products_db = await conn.fetch("""
                SELECT
                    id, symbol, name, provider, apy, is_cefi, min_amount, max_amount,
                    lock_period_days, max_apy, risk_level, is_active, website_url,
                    description, product_type, created_at, updated_at, last_checked, raw_data
                FROM yield_products
                WHERE provider = 'HTX' AND is_active = true
                ORDER BY apy DESC, symbol ASC
                LIMIT 10
            """)

            print(f"📱 Отримали {len(htx_products_db)} HTX продуктів для відображення")
            print("📱 Перші 3 продукти:")

            for i, product in enumerate(htx_products_db[:3], 1):
                print(f"  {i}. {product['symbol']} - {product['apy']}% APY ({product['product_type']})")

            print("✅ Імітація телеграм бота успішна!")

        except Exception as e:
            print(f"❌ Помилка тестування HTX логіки: {e}")

        # Тестуємо Railway API для HTX продуктів
        print("\n🌐 Тестуємо Railway API для HTX продуктів...")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get("https://go-to-the-exchange.up.railway.app/api/v1/htx/products?limit=5")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        products = data.get("data", [])
                        print(f"✅ Railway API повернув {len(products)} HTX продуктів")
                        if products:
                            print("📱 Перші 3 продукти з API:")
                            for i, product in enumerate(products[:3], 1):
                                print(f"  {i}. {product['symbol']} - {product['apy']}% APY ({product['product_type']})")
                    else:
                        print(f"❌ Railway API повернув помилку: {data}")
                else:
                    print(f"❌ HTTP помилка {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ Помилка тестування Railway API: {e}")

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

