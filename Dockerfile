# =============================================================================
# EarnAggregator Universal Dockerfile
# =============================================================================
# Єдиний образ для всіх сервісів з усіма залежностями
# Вибір сервісу відбувається через змінну середовища SERVICE_NAME

FROM python:3.11-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо та встановлюємо всі Python залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Створюємо директорії для всіх сервісів
RUN mkdir -p /app/logs /app/app /app/tests /app/bot

# Встановлюємо змінні середовища
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Відкриваємо порт (за замовчуванням 8000, але telegram-bot може використовувати інший)
EXPOSE 8000

# Команда запуску залежно від SERVICE_NAME
CMD if [ "$SERVICE_NAME" = "yield-api" ]; then \
        echo "🚀 Запуск yield-api сервісу..." && \
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; \
    elif [ "$SERVICE_NAME" = "telegram-bot" ]; then \
        echo "🤖 Запуск telegram-bot сервісу..." && \
        python -m bot.main; \
    else \
        echo "❌ Невідомий SERVICE_NAME: $SERVICE_NAME" && \
        echo "📋 Доступні сервіси: yield-api, telegram-bot" && \
        exit 1; \
    fi
