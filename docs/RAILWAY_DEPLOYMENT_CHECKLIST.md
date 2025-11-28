# 🚂 Railway Deployment Checklist для EarnAggregator

## 📊 Статус підключень MCP

### ✅ GitHub MCP
**Статус:** ✅ Працює коректно
- Можу отримувати інформацію про репозиторій
- Можу створювати/оновлювати файли
- Можу створювати PR та теги

### ❌ Railway CLI
**Статус:** ❌ Не встановлено

**Що потрібно зробити:**
```bash
# Встановити Railway CLI
# macOS:
brew install railway

# Або через npm:
npm i -g @railway/cli

# Авторизуватися
railway login
```

**Альтернатива:** Використовувати Railway через веб-інтерфейс (https://railway.app)

---

## 🔍 Аналіз проекту на GitHub

### ✅ Що вже готово:

1. **Dockerfile** ✅
   - Знаходиться в корені проекту
   - Підтримує мультисервісний запуск через `SERVICE_NAME`
   - Використовує Python 3.11-slim

2. **Структура проекту** ✅
   - Чітко розділені сервіси (yield-api, telegram-bot)
   - Документація присутня
   - Версійність налаштована (v1.0.0)

3. **GitHub репозиторій** ✅
   - Репозиторій: `iow34/earnaggregator`
   - Гілки: `main`, `staging`
   - Тег v1.0.0 створено локально (потрібно запушити)

### ⚠️ Що потрібно доробити:

---

## 📋 Список необхідних налаштувань для Railway

### 🔴 Критичні (обов'язково перед деплоєм)

#### 1. **Підтримка Railway PORT змінної**

**Проблема:** Railway автоматично призначає порт через змінну `PORT`, але ваш код використовує фіксований порт 8000.

**Рішення:**
- Оновити `yield-data-service/app/main.py` для читання `PORT` змінної
- Оновити `Dockerfile` для використання `PORT`

**Файли для змін:**
- `yield-data-service/app/main.py` - додати підтримку `PORT`
- `Dockerfile` - оновити CMD для використання `PORT`

#### 2. **Створення `.dockerignore`**

**Проблема:** Відсутній `.dockerignore`, що може призвести до великих образів.

**Рішення:**
- Створити `.dockerignore` в корені проекту
- Виключити непотрібні файли (logs, venv, .git, тощо)

#### 3. **Підтримка Railway DATABASE_URL та REDIS_URL**

**Проблема:** Railway надає `DATABASE_URL` та `REDIS_URL` в іншому форматі, ніж ваш локальний `.env`.

**Рішення:**
- Переконатися, що `config.py` правильно обробляє Railway формати
- Додати fallback логіку для різних форматів URL

#### 4. **Створення `railway.json` або налаштування через UI**

**Проблема:** Відсутня конфігурація для Railway.

**Рішення:**
- Створити `railway.json` для налаштування сервісів
- Або налаштувати через Railway UI

#### 5. **Розділення сервісів на окремі Railway Services**

**Проблема:** Ваш проект має кілька сервісів (API, Bot, PostgreSQL, Redis), які потрібно розгорнути окремо.

**Рішення:**
- Створити окремі сервіси в Railway:
  - `yield-api` (FastAPI)
  - `telegram-bot` (Aiogram)
  - `postgres` (managed або container)
  - `redis` (managed або container)

#### 6. **Міграції БД перед запуском**

**Проблема:** Потрібно виконати міграції БД перед запуском API.

**Рішення:**
- Додати команду міграції в Dockerfile або Railway start command
- Або виконати міграції вручну після деплою

#### 7. **Налаштування змінних середовища**

**Проблема:** Потрібно налаштувати всі змінні середовища в Railway.

**Рішення:**
- Створити список всіх необхідних змінних
- Налаштувати їх в Railway UI або через CLI

---

### 🟡 Важливі (рекомендовано)

#### 8. **Health Check endpoints**

**Статус:** ✅ Вже є (`/health`, `/api/v1/health`)

**Що перевірити:**
- Railway автоматично використовує health checks
- Переконатися, що endpoints повертають коректні відповіді

#### 9. **Логування**

**Проблема:** Логи зберігаються в файли, але Railway показує логи через UI.

**Рішення:**
- Налаштувати логування в stdout/stderr
- Railway автоматично збирає логи з контейнерів

#### 10. **Обробка помилок при старті**

**Статус:** ✅ Вже є (try/catch в lifespan)

**Що перевірити:**
- Переконатися, що сервіс не падає при недоступній БД/Redis
- Graceful degradation працює

---

### 🟢 Опціональні (для оптимізації)

#### 11. **Build оптимізація**

**Проблема:** Dockerfile може бути оптимізований для швидшого build.

**Рішення:**
- Використовувати multi-stage builds
- Кешувати залежності

#### 12. **Моніторинг**

**Проблема:** Prometheus/Grafana не працюють на Railway без додаткових налаштувань.

**Рішення:**
- Використовувати Railway метрики
- Або винести моніторинг на окремий сервіс

---

## 📝 Детальний план дій

### Крок 1: Підготовка коду для Railway

#### 1.1. Оновити `yield-data-service/app/main.py` для підтримки PORT

**Поточний код:**
```python
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8000,  # Фіксований порт
    reload=True,
    log_level="info"
)
```

**Потрібно змінити на:**
```python
import os

port = int(os.getenv("PORT", 8000))  # Railway надає PORT
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=port,
    reload=False,  # В production не потрібен reload
    log_level="info"
)
```

#### 1.2. Оновити `Dockerfile` для використання PORT

**Поточний CMD:**
```dockerfile
CMD if [ "$SERVICE_NAME" = "yield-api" ]; then \
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; \
    ...
```

**Потрібно змінити на:**
```dockerfile
CMD if [ "$SERVICE_NAME" = "yield-api" ]; then \
        PORT=${PORT:-8000} && \
        python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT; \
    ...
```

#### 1.3. Створити `.dockerignore`

**Файл:** `.dockerignore`
```
# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
ENV/

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
.env.*.local

# Tests
tests/
.pytest_cache/
.coverage

# Documentation
docs/
*.md

# Docker
docker-compose*.yml
Dockerfile*

# Backups
backups/
*.sql
*.dump

# Node
node_modules/
npm-debug.log

# Build artifacts
dist/
build/
```

#### 1.4. Створити `railway.json` (опціонально)

**Файл:** `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### Крок 2: Налаштування Railway проекту

#### 2.1. Створити проект на Railway

1. Перейти на https://railway.app
2. Увійти/зареєструватися
3. Натиснути **"New Project"**
4. Обрати **"Deploy from GitHub repo"**
5. Вибрати репозиторій `iow34/earnaggregator`
6. Обрати гілку `main` або `staging`

#### 2.2. Створити сервіси

**Сервіс 1: PostgreSQL (Managed)**
1. **Add Service** → **Database** → **PostgreSQL**
2. Railway автоматично створить БД та надасть `DATABASE_URL`
3. Записати `DATABASE_URL` для використання в інших сервісах

**Сервіс 2: Redis (Managed)**
1. **Add Service** → **Database** → **Redis**
2. Railway автоматично створить Redis та надасть `REDIS_URL`
3. Записати `REDIS_URL` для використання в інших сервісах

**Сервіс 3: Yield API**
1. **Add Service** → **GitHub Repo** → вибрати `earnaggregator`
2. Railway автоматично виявить `Dockerfile`
3. Налаштувати:
   - **Root Directory:** `/` (корінь)
   - **Build Command:** (залишити порожнім, Railway використає Dockerfile)
   - **Start Command:** (залишити порожнім, Railway використає CMD з Dockerfile)
   - **Environment Variables:** (додати нижче)

**Сервіс 4: Telegram Bot**
1. **Add Service** → **GitHub Repo** → вибрати `earnaggregator`
2. Налаштувати:
   - **Root Directory:** `/` (корінь)
   - **Environment Variables:**
     - `SERVICE_NAME=telegram-bot`
     - Інші змінні (див. нижче)

---

### Крок 3: Налаштування змінних середовища

#### 3.1. Змінні для Yield API сервісу

**Обов'язкові:**
```bash
# Service identification
SERVICE_NAME=yield-api

# Database (з Railway PostgreSQL service)
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Railway автоматично підставляє

# Redis (з Railway Redis service)
REDIS_URL=${{Redis.REDIS_URL}}  # Railway автоматично підставляє

# API Configuration
PORT=${{PORT}}  # Railway автоматично надає
ENVIRONMENT=production
LOG_LEVEL=INFO

# Exchange APIs
BINANCE_API_KEY=your_production_binance_key
BINANCE_API_SECRET=your_production_binance_secret
BYBIT_API_KEY=your_production_bybit_key
BYBIT_API_SECRET=your_production_bybit_secret
OKX_API_KEY=your_production_okx_key
OKX_API_SECRET=your_production_okx_secret
OKX_API_PASSPHRASE=your_production_okx_passphrase
GATE_API_KEY=your_production_gate_key
GATE_API_SECRET=your_production_gate_secret
BITGET_API_KEY=your_production_bitget_key
BITGET_API_SECRET=your_production_bitget_secret
BITGET_API_PASSPHRASE=your_production_bitget_passphrase
KRAKEN_API_KEY=your_production_kraken_key
KRAKEN_API_SECRET=your_production_kraken_secret
KUCOIN_API_KEY=your_production_kucoin_key
KUCOIN_API_SECRET=your_production_kucoin_secret
KUCOIN_API_PASSPHRASE=your_production_kucoin_passphrase
HTX_API_KEY=your_production_htx_key
HTX_API_SECRET=your_production_htx_secret

# Referral Links
REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924
REFERRAL_BYBIT=https://www.bybit.com/invite?ref=YOUR_REF
REFERRAL_OKX=https://okx.com/join/YOUR_REF
REFERRAL_MEXC=https://promote.mexc.com/r/YOUR_REF
REFERRAL_BITMART=https://www.bitmart.com/register?referralCode=YOUR_REF
REFERRAL_GATE=https://www.gate.io/signup?referralCode=YOUR_REF
REFERRAL_BITGET=https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF
REFERRAL_KRAKEN=https://www.kraken.com/ref/YOUR_REF
REFERRAL_KUCOIN=https://www.kucoin.com/ref/YOUR_REF
REFERRAL_HTX=https://www.htx.com/ref/YOUR_REF
REFERRAL_NEXO=https://nexo.com/ref/YOUR_REF

# Tracking
TRACKING_REDIRECT_URL=https://your-railway-domain.railway.app
```

#### 3.2. Змінні для Telegram Bot сервісу

**Обов'язкові:**
```bash
# Service identification
SERVICE_NAME=telegram-bot

# Telegram
BOT_TOKEN=your_production_bot_token

# Database (з Railway PostgreSQL service)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (з Railway Redis service)
REDIS_URL=${{Redis.REDIS_URL}}

# Data Service URL (з Yield API service)
DATA_SERVICE_URL=${{YieldAPI.RAILWAY_PUBLIC_DOMAIN}}  # Або вказати URL вручну

# Tracking
TRACKING_REDIRECT_URL=https://your-railway-domain.railway.app
```

---

### Крок 4: Виконання міграцій БД

#### 4.1. Варіант 1: Через Railway CLI (після встановлення)

```bash
# Підключитися до проекту
railway link

# Виконати міграції
railway run alembic upgrade head
```

#### 4.2. Варіант 2: Додати в Dockerfile

**Оновити Dockerfile:**
```dockerfile
# Після встановлення залежностей
RUN if [ -f "yield-data-service/alembic.ini" ]; then \
        echo "Alembic знайдено, міграції будуть виконані при старті"; \
    fi

# Додати скрипт для міграцій
COPY scripts/run_migrations.sh /app/scripts/
RUN chmod +x /app/scripts/run_migrations.sh
```

**Створити `scripts/run_migrations.sh`:**
```bash
#!/bin/bash
set -e

echo "🔄 Виконання міграцій БД..."

cd yield-data-service
if [ -f "alembic.ini" ]; then
    alembic upgrade head
    echo "✅ Міграції виконано успішно"
else
    echo "⚠️ Alembic не знайдено, пропускаємо міграції"
fi
```

**Оновити CMD в Dockerfile:**
```dockerfile
CMD if [ "$SERVICE_NAME" = "yield-api" ]; then \
        /app/scripts/run_migrations.sh && \
        PORT=${PORT:-8000} && \
        python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT; \
    ...
```

---

### Крок 5: Налаштування доменів

#### 5.1. Генерація доменів

1. В Railway UI для кожного сервісу:
   - **Settings** → **Networking** → **Generate Domain**
2. Записати домени:
   - Yield API: `https://yield-api-production.up.railway.app`
   - Telegram Bot: (не потребує публічного домену)

#### 5.2. Оновлення змінних середовища

Після генерації доменів оновити:
- `TRACKING_REDIRECT_URL` в обох сервісах
- `DATA_SERVICE_URL` в Telegram Bot сервісі

---

### Крок 6: Тестування деплою

#### 6.1. Перевірка API

```bash
# Health check
curl https://your-railway-domain.railway.app/health

# API status
curl https://your-railway-domain.railway.app/api/v1/health

# Root endpoint
curl https://your-railway-domain.railway.app/
```

#### 6.2. Перевірка Telegram Bot

1. Відкрити Telegram
2. Знайти свого бота
3. Надіслати команду `/start`
4. Перевірити, що бот відповідає

#### 6.3. Перевірка логів

1. В Railway UI → **Deployments** → вибрати deployment
2. Переглянути логи
3. Перевірити наявність помилок

---

## 🔧 Технічні виправлення

### Виправлення 1: Підтримка PORT в main.py

**Файл:** `yield-data-service/app/main.py`

**Зміни:**
```python
import os

# В кінці файлу, в if __name__ == "__main__":
if __name__ == "__main__":
    logger.info("Запуск EarnAggregator Data Service...")
    
    # Railway надає PORT через змінну середовища
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,  # В production не потрібен reload
        log_level="info"
    )
```

### Виправлення 2: Оновлення Dockerfile

**Файл:** `Dockerfile`

**Зміни:**
```dockerfile
# Команда запуску залежно від SERVICE_NAME
CMD if [ "$SERVICE_NAME" = "yield-api" ]; then \
        echo "🚀 Запуск yield-api сервісу..." && \
        PORT=${PORT:-8000} && \
        python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT; \
    elif [ "$SERVICE_NAME" = "telegram-bot" ]; then \
        echo "🤖 Запуск telegram-bot сервісу..." && \
        python -m bot.main; \
    else \
        echo "❌ Невідомий SERVICE_NAME: $SERVICE_NAME" && \
        echo "📋 Доступні сервіси: yield-api, telegram-bot" && \
        exit 1; \
    fi
```

### Виправлення 3: Підтримка Railway DATABASE_URL формату

**Файл:** `yield-data-service/app/config.py`

**Поточний код вже підтримує різні формати**, але перевірити:
- Railway надає `DATABASE_URL` в форматі: `postgresql://user:pass@host:port/db`
- Ваш код очікує: `postgresql+asyncpg://user:pass@host:port/db`

**Потрібно додати обробку:**
```python
def get_database_url() -> str:
    """
    Отримує DATABASE_URL з підтримкою Railway формату.
    """
    db_url = settings.database_url
    
    # Якщо Railway надав URL без +asyncpg, додаємо
    if db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return db_url
```

---

## 📋 Чек-лист перед деплоєм

### Перед деплоєм:

- [ ] Оновлено `main.py` для підтримки PORT
- [ ] Оновлено `Dockerfile` для використання PORT
- [ ] Створено `.dockerignore`
- [ ] Створено `railway.json` (опціонально)
- [ ] Перевірено, що всі змінні середовища готові
- [ ] Налаштовано міграції БД
- [ ] Перевірено локально, що Dockerfile працює

### Після деплою:

- [ ] API доступний через Railway domain
- [ ] Health check endpoints працюють
- [ ] Telegram бот відповідає на команди
- [ ] Підключення до БД працює
- [ ] Підключення до Redis працює
- [ ] Scheduler запускається та працює
- [ ] Логи не містять критичних помилок
- [ ] Міграції БД виконано

---

## 🚨 Типові проблеми та рішення

### Проблема 1: "Port already in use"

**Причина:** Railway надає PORT, але код використовує фіксований 8000.

**Рішення:** Використовувати змінну `PORT` (див. виправлення вище).

### Проблема 2: "Database connection failed"

**Причина:** Railway надає `DATABASE_URL` в іншому форматі.

**Рішення:** Додати обробку формату URL (див. виправлення вище).

### Проблема 3: "Service crashes on startup"

**Причина:** Відсутні змінні середовища або неправильні значення.

**Рішення:** Перевірити всі змінні в Railway UI, переконатися, що всі обов'язкові змінні налаштовані.

### Проблема 4: "Build fails"

**Причина:** Відсутні залежності або помилки в Dockerfile.

**Рішення:** Перевірити логи build, переконатися, що `requirements.txt` актуальний.

---

## 📚 Додаткові ресурси

- [Railway Documentation](https://docs.railway.app/)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)
- [Railway Database](https://docs.railway.app/databases/postgresql)
- [Railway Redis](https://docs.railway.app/databases/redis)

---

## 🎯 Наступні кроки

1. **Встановити Railway CLI** (якщо хочеш використовувати CLI)
2. **Оновити код** для підтримки Railway (PORT, DATABASE_URL)
3. **Створити `.dockerignore`**
4. **Створити проект на Railway**
5. **Налаштувати сервіси** (PostgreSQL, Redis, API, Bot)
6. **Налаштувати змінні середовища**
7. **Виконати міграції БД**
8. **Протестувати деплой**

---

**Готовність до деплою:** ⚠️ Потрібні технічні виправлення (див. вище)

