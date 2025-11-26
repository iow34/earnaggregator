#!/usr/bin/env python3
"""
Простий скрипт для запуску сервера з правильними налаштуваннями.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Налаштування для локальної розробки
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://yield_user:yield_secure_password_2024@localhost:5432/yield_db",
        "REDIS_HOST": "localhost", 
        "REDIS_PORT": "6379",
        "REDIS_URL": "redis://localhost:6379/0",
        "BINANCE_API_KEY": "your_binance_api_key_here",
        "BINANCE_API_SECRET": "your_binance_api_secret_here"
    }
    
    print("🚀 Запуск EarnAggregator Data Service...")
    print("📍 Увага: Переконайтеся що PostgreSQL та Redis запущені локально")
    
    # Встановлюємо змінні середовища
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Вибираємо порт для локальної розробки
    LOCAL_DEV_PORT = 8001
    
    # Команда для запуску
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--host", "127.0.0.1", 
        "--port", str(LOCAL_DEV_PORT), 
        "--reload"
    ]
    
    print(f"🔧 Команда: {' '.join(cmd)}")
    print(f"🌐 Локальний сервер буде доступний на: http://localhost:{LOCAL_DEV_PORT}")
    print(f"📖 Документація: http://localhost:{LOCAL_DEV_PORT}/docs")
    print("🐳 Docker сервер (якщо запущений): http://localhost:8000")
    print("🔄 Для зупинки натисніть Ctrl+C")
    print("-" * 50)
    
    try:
        # Запускаємо сервер
        subprocess.run(cmd, cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n✅ Сервер зупинено")
    except Exception as e:
        print(f"❌ Помилка запуску: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
