#!/bin/bash
# Default to telegram-bot if SERVICE_NAME is not set (for Railway compatibility)
SERVICE_NAME=${SERVICE_NAME:-telegram-bot}

if [ "$SERVICE_NAME" = "redis" ]; then
    echo "🔴 Запуск Redis сервісу..."
    # For Redis service, start Redis server
    exec redis-server
elif [ "$SERVICE_NAME" = "yield-api" ]; then
    echo "🚀 Запуск yield-api сервісу..."
    echo "📋 SERVICE_NAME: $SERVICE_NAME"
    echo "🌐 PORT: ${PORT:-8000}"
    echo "🏠 HOST: ${HOST:-0.0.0.0}"
    PORT=${PORT:-8000}
    HOST=${HOST:-0.0.0.0}
    echo "🔧 Запуск uvicorn з параметрами: --host $HOST --port $PORT"
    exec python -m uvicorn app.main:app --host $HOST --port $PORT --log-level info
elif [ "$SERVICE_NAME" = "telegram-bot" ]; then
    echo "🤖 Запуск telegram-bot сервісу..."
    exec python -m bot.main
else
    echo "❌ Невідомий SERVICE_NAME: $SERVICE_NAME"
    echo "📋 Доступні сервіси: redis, yield-api, telegram-bot"
    exit 1
fi