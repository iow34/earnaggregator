# =============================================================================
# EarnAggregator Universal Dockerfile (Multi-Stage Build)
# =============================================================================
# Оптимізований Dockerfile з multi-stage builds та кешуванням залежностей
# Вибір сервісу відбувається через змінну середовища SERVICE_NAME
# =============================================================================

# =============================================================================
# Stage 1: Builder - встановлення залежностей
# =============================================================================
FROM python:3.11-slim as builder

# Встановлюємо системні залежності для компіляції
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements.txt окремо для кешування
# Docker кешує цей шар, якщо requirements.txt не змінився
COPY requirements.txt .

# Встановлюємо Python залежності в окремий каталог для копіювання
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Runtime - фінальний образ
# =============================================================================
FROM python:3.11-slim as runtime

# Встановлюємо тільки runtime залежності (без компіляторів)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    redis-server \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копіюємо встановлені залежності з builder stage
COPY --from=builder /root/.local /root/.local

# Додаємо /root/.local/bin до PATH для доступу до встановлених пакетів
ENV PATH=/root/.local/bin:$PATH

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо код проекту
# Структура проекту:
# - yield-data-service/app/ -> /app/app/ (для yield-api)
# - yield-telegram-bot/bot/ -> /app/bot/ (для telegram-bot) - включає static_tracking_links.json
# - VERSION -> /app/VERSION (для версійності)
# - yield-data-service/scripts/ -> /app/scripts/ (для міграцій)
# - docker-entrypoint.sh -> /docker-entrypoint.sh (для Railway)
COPY yield-data-service/app /app/app
COPY yield-telegram-bot/bot /app/bot
COPY VERSION /app/VERSION
COPY yield-data-service/scripts /app/scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Створюємо директорії для логів та тестів
RUN mkdir -p /app/logs /app/tests

# Встановлюємо змінні середовища
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Відкриваємо порт (Railway надає PORT через змінну середовища)
EXPOSE 8000

# Встановлюємо права на виконання для entrypoint скрипта
RUN chmod +x /docker-entrypoint.sh

# Використовуємо CMD замість ENTRYPOINT для Railway compatibility
CMD ["/docker-entrypoint.sh"]
