# 🚀 EarnAggregator: Перехід на Stage середовище

**Дата створення:** 2025-01-XX  
**Версія:** 1.0  
**Статус:** ⚠️ Потрібна підготовка перед деплоєм

---

## 📋 Зміст

1. [Аудит проекту](#аудит-проекту)
2. [Підготовка до GitHub](#підготовка-до-github)
3. [Структура репозиторію](#структура-репозиторію)
4. [Створення Stage середовища](#створення-stage-середовища)
5. [Деплой на хостинг](#деплой-на-хостинг)
6. [Перевірка та тестування](#перевірка-та-тестування)
7. [Чек-лист перед деплоєм](#чек-лист-перед-деплоєм)

---

## 🔍 Аудит проекту

### Поточна структура

```
EarnAggregator/
├── yield-data-service/      # FastAPI сервіс (основний API)
├── yield-telegram-bot/      # Telegram бот
├── broadcast-admin-web/     # React адмін-панель
├── server/                  # Node.js сервер (застарілий?)
├── docs/                    # Документація
├── scripts/                 # Допоміжні скрипти
├── backups/                 # Бекапи БД
├── logs/                    # Логи сервісів
├── docker-compose.yml       # Development конфігурація
├── docker-compose.prod.yml  # Production конфігурація
├── Dockerfile               # Універсальний образ
├── requirements.txt         # Python залежності
├── .env                     # Змінні середовища (локальні)
├── .env.production          # Production змінні
└── .gitignore              # Git ignore правила
```

### Сервіси та компоненти

#### 1. Yield Data Service (FastAPI)
- **Призначення:** REST API для агрегації даних з бірж
- **Порт:** 8000
- **База даних:** PostgreSQL
- **Кеш:** Redis
- **Моніторинг:** Prometheus + Grafana
- **Біржі:** Binance, Bybit, OKX, Gate.io, Bitget, Kraken, KuCoin, HTX, MEXC

#### 2. Telegram Bot
- **Призначення:** Telegram бот для пошуку yield продуктів
- **Framework:** Aiogram 3.x
- **Залежності:** yield-data-service (API)

#### 3. Broadcast Admin Web
- **Призначення:** Веб-адмінка для ручних розсилок
- **Технології:** React + TypeScript + Vite
- **Порт:** 4173 (production build)

#### 4. Broadcast Services
- **broadcast-admin:** FastAPI сервіс для адмін-панелі (порт 8081)
- **broadcast-worker:** Worker для обробки черги розсилок

### Проблеми виявлені при аудиті

#### 🔴 Критичні

1. **Секрети в .env файлі**
   - ❌ Реальні API ключі бірж в `.env` файлі
   - ❌ Токен Telegram бота в `.env`
   - ✅ `.env` в `.gitignore` - правильно
   - ⚠️ **Дії:** Переконатися що всі секрети в `.env.example` замінені на placeholders

2. **Відсутність .env.staging**
   - ❌ Немає окремого файлу для stage середовища
   - ⚠️ **Дії:** Створити `.env.staging` з stage конфігурацією

3. **Відсутність docker-compose.staging.yml**
   - ❌ Немає окремого compose файлу для stage
   - ⚠️ **Дії:** Створити `docker-compose.staging.yml`

#### 🟡 Важливі

4. **Логи в репозиторії**
   - ❌ Директорія `logs/` містить файли логів
   - ✅ `logs/` в `.gitignore` - правильно, але файли вже є в репозиторії
   - ⚠️ **Дії:** Очистити історію Git від логів

5. **Backups в репозиторії**
   - ❌ Директорія `backups/` може містити бекапи
   - ✅ `backup_*.sql` в `.gitignore` - правильно
   - ⚠️ **Дії:** Переконатися що бекапи не комітять

6. **Відсутність CI/CD**
   - ❌ Немає GitHub Actions workflow
   - ⚠️ **Дії:** Створити базовий CI/CD pipeline

7. **Відсутність .env.example**
   - ❌ Немає шаблону змінних середовища
   - ⚠️ **Дії:** Створити `.env.example` з placeholders

#### 🟢 Рекомендації

8. **Структура проекту**
   - ✅ Добре структурований монолітний репозиторій
   - ✅ Окремі сервіси в окремих директоріях
   - ✅ Документація в `docs/`

9. **Docker конфігурація**
   - ✅ Універсальний Dockerfile для всіх сервісів
   - ✅ Docker Compose для оркестрації
   - ⚠️ Рекомендація: Розглянути окремі образи для кожного сервісу

---

## 🔐 Підготовка до GitHub

### Крок 1: Очищення репозиторію

#### Перевірка що не потрапляє в Git

```bash
# Перевірити які файли будуть додані
git status

# Перевірити що .env в .gitignore
grep -r "\.env" .gitignore

# Перевірити що logs/ в .gitignore
grep -r "logs/" .gitignore
```

#### Очищення логів та тимчасових файлів

```bash
# Видалити логи (якщо вони вже в репозиторії)
git rm -r --cached logs/
git rm -r --cached backups/*.sql

# Очистити __pycache__
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Очистити .DS_Store (macOS)
find . -name ".DS_Store" -delete
```

### Крок 2: Створення .env.example

Створити файл `.env.example` в корені проекту:

```bash
# Створити .env.example з placeholders
cp .env .env.example

# Замінити всі секрети на placeholders
# Використати sed або відредагувати вручну
```

**Шаблон `.env.example`:**

```env
# =============================================================================
# EarnAggregator - Environment Variables Template
# =============================================================================
# Скопіюйте цей файл як .env та заповніть реальними значеннями
# НЕ комітьте .env файл в Git!

# =============================================================================
# PostgreSQL Database
# =============================================================================
POSTGRES_DB=yield_db
POSTGRES_USER=yield_user
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://yield_user:your_secure_password_here@postgres:5432/yield_db

# =============================================================================
# Redis Cache
# =============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_URL=redis://redis:6379/0

# =============================================================================
# Exchange APIs (замініть на ваші реальні ключі)
# =============================================================================
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here
OKX_API_KEY=your_okx_api_key_here
OKX_API_SECRET=your_okx_api_secret_here
OKX_API_PASSPHRASE=your_okx_passphrase_here
# ... (інші біржі)

# =============================================================================
# Telegram Bot
# =============================================================================
BOT_TOKEN=your_telegram_bot_token_here
DATA_SERVICE_URL=http://yield-api:8000
TRACKING_REDIRECT_URL=http://localhost:8000

# =============================================================================
# Environment
# =============================================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Крок 3: Створення .env.staging

Створити файл `.env.staging` для stage середовища:

```env
# =============================================================================
# EarnAggregator - Staging Environment
# =============================================================================

ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Database (stage)
POSTGRES_DB=yield_db_staging
POSTGRES_USER=yield_user_staging
POSTGRES_PASSWORD=your_staging_password_here
DATABASE_URL=postgresql+asyncpg://yield_user_staging:your_staging_password_here@postgres:5432/yield_db_staging

# Redis (stage)
REDIS_URL=redis://redis:6379/1

# Exchange APIs (stage keys або тестові)
BINANCE_API_KEY=your_staging_binance_key
BINANCE_API_SECRET=your_staging_binance_secret
# ... (інші біржі)

# Telegram Bot (stage bot token)
BOT_TOKEN=your_staging_bot_token
TRACKING_REDIRECT_URL=https://staging-api.earnaggregator.com

# Monitoring
PROMETHEUS_ENDPOINT=http://prometheus:9090
GRAFANA_ENDPOINT=http://grafana:3000
```

### Крок 4: Створення docker-compose.staging.yml

Створити окремий compose файл для stage:

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    container_name: earn-postgres-staging
    restart: unless-stopped
    env_file: .env.staging
    environment:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
      - ./yield-data-service/app/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    networks:
      - backend_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: earn-redis-staging
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_staging_data:/data
    networks:
      - backend_net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  yield-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: earn-yield-api-staging
    restart: unless-stopped
    env_file: .env.staging
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    volumes:
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    networks:
      - backend_net
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: earn-telegram-bot-staging
    restart: unless-stopped
    env_file: .env.staging
    environment:
      - SERVICE_NAME=telegram-bot
    command: python -m bot.main
    volumes:
      - ./yield-telegram-bot/bot:/app/bot
      - ./logs:/app/logs
    networks:
      - backend_net
    depends_on:
      yield-api:
        condition: service_healthy

  broadcast-admin:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: earn-broadcast-admin-staging
    restart: unless-stopped
    env_file: .env.staging
    environment:
      - SERVICE_NAME=broadcast-admin
    command: uvicorn bot.admin_app:app --host 0.0.0.0 --port 8081
    volumes:
      - ./yield-telegram-bot/bot:/app/bot
      - ./logs:/app/logs
    ports:
      - "8081:8081"
    networks:
      - backend_net
    depends_on:
      postgres:
        condition: service_healthy

  broadcast-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: earn-broadcast-worker-staging
    restart: unless-stopped
    env_file: .env.staging
    environment:
      - SERVICE_NAME=broadcast-worker
    command: python -m bot.broadcasts.worker_app
    volumes:
      - ./yield-telegram-bot/bot:/app/bot
      - ./logs:/app/logs
    networks:
      - backend_net
    depends_on:
      redis:
        condition: service_healthy

  broadcast-web:
    build:
      context: ./broadcast-admin-web
      dockerfile: Dockerfile
    container_name: earn-broadcast-web-staging
    restart: unless-stopped
    depends_on:
      broadcast-admin:
        condition: service_started
    ports:
      - "4173:80"
    networks:
      - backend_net

  prometheus:
    image: prom/prometheus:latest
    container_name: earn-prometheus-staging
    restart: unless-stopped
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=7d"
      - "--web.enable-lifecycle"
    volumes:
      - ./yield-data-service/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_staging_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - backend_net
    depends_on:
      yield-api:
        condition: service_healthy

  grafana:
    image: grafana/grafana:latest
    container_name: earn-grafana-staging
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_AUTH_ANONYMOUS_ENABLED=false
    volumes:
      - grafana_staging_data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - backend_net
    depends_on:
      prometheus:
        condition: service_started

networks:
  backend_net:
    driver: bridge
    name: earn_backend_staging

volumes:
  postgres_staging_data:
  redis_staging_data:
  prometheus_staging_data:
  grafana_staging_data:
```

---

## 📁 Структура репозиторію

### Що РОЗМІЩУВАТИ на GitHub

#### ✅ Обов'язково

```
EarnAggregator/
├── yield-data-service/          # ✅ Весь код Python
│   ├── app/                     # ✅ Весь код
│   ├── tests/                   # ✅ Тести
│   ├── monitoring/              # ✅ Конфігурація Prometheus/Grafana
│   └── scripts/                 # ✅ Скрипти міграцій
├── yield-telegram-bot/          # ✅ Весь код Python
│   ├── bot/                     # ✅ Весь код
│   ├── tests/                   # ✅ Тести
│   ├── alembic/                 # ✅ Міграції БД
│   └── alembic.ini              # ✅ Конфігурація Alembic
├── broadcast-admin-web/         # ✅ Весь код React
│   ├── src/                     # ✅ Весь код
│   ├── public/                  # ✅ Статичні файли
│   ├── package.json             # ✅ Залежності
│   ├── Dockerfile               # ✅ Dockerfile
│   └── vite.config.ts           # ✅ Конфігурація Vite
├── docs/                        # ✅ Вся документація
├── scripts/                     # ✅ Допоміжні скрипти (без секретів)
├── docker-compose.yml           # ✅ Development конфігурація
├── docker-compose.prod.yml      # ✅ Production конфігурація
├── docker-compose.staging.yml   # ✅ Staging конфігурація (створити)
├── Dockerfile                   # ✅ Універсальний Dockerfile
├── requirements.txt             # ✅ Python залежності
├── .env.example                 # ✅ Шаблон змінних (створити)
├── .env.staging                 # ⚠️ Можна, але БЕЗ секретів (тільки структура)
├── .gitignore                   # ✅ Git ignore
├── README.md                    # ✅ Головний README
└── .github/                     # ✅ CI/CD workflows (створити)
    └── workflows/
        └── deploy-staging.yml
```

#### ⚠️ Умовно

- `.env.staging` - можна додати, але БЕЗ реальних секретів (тільки структура з placeholders)
- `server/` - якщо не використовується, видалити або документувати статус

#### ❌ НЕ розміщувати на GitHub

```
❌ .env                      # Секрети
❌ .env.production           # Production секрети
❌ logs/                     # Логи
❌ backups/                  # Бекапи БД
❌ venv/                     # Virtual environment
❌ __pycache__/              # Python cache
❌ .DS_Store                 # macOS файли
❌ node_modules/             # Node.js залежності
❌ *.pyc                     # Compiled Python
❌ *.log                     # Лог файли
❌ *.sql                     # SQL дампи
❌ *.pem, *.key, *.crt      # Сертифікати
```

### Команди для підготовки репозиторію

```bash
# 1. Перевірити статус
git status

# 2. Додати всі файли (з урахуванням .gitignore)
git add .

# 3. Перевірити що буде додано
git status

# 4. Створити перший коміт
git commit -m "Initial commit: EarnAggregator project structure"

# 5. Створити приватний репозиторій на GitHub (через веб-інтерфейс)

# 6. Додати remote
git remote add origin https://github.com/YOUR_USERNAME/EarnAggregator.git

# 7. Встановити upstream та запушити
git branch -M main
git push -u origin main
```

---

## 🏗️ Створення Stage середовища

### Варіант 1: VPS/Хостинг з Docker

#### Вимоги до хостингу

- **ОС:** Linux (Ubuntu 20.04+ / Debian 11+)
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **RAM:** мінімум 2GB (рекомендовано 4GB+)
- **Диск:** мінімум 20GB (рекомендовано 50GB+)
- **CPU:** мінімум 2 cores

#### Крок 1: Підготовка сервера

```bash
# Підключитися до сервера
ssh user@your-staging-server.com

# Оновити систему
sudo apt update && sudo apt upgrade -y

# Встановити Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Встановити Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Додати користувача до групи docker
sudo usermod -aG docker $USER
newgrp docker

# Перевірити встановлення
docker --version
docker-compose --version
```

#### Крок 2: Клонування репозиторію

```bash
# Створити директорію для проекту
sudo mkdir -p /opt/earnaggregator
sudo chown $USER:$USER /opt/earnaggregator
cd /opt/earnaggregator

# Клонувати репозиторій
git clone https://github.com/YOUR_USERNAME/EarnAggregator.git .

# Перейти на staging гілку (якщо використовуєте)
git checkout staging  # або створити: git checkout -b staging
```

#### Крок 3: Налаштування змінних середовища

```bash
# Створити .env.staging з реальними значеннями
cp .env.example .env.staging
nano .env.staging

# Або використати GitHub Secrets (рекомендовано)
# Налаштувати через GitHub Actions Secrets:
# - STAGING_DB_PASSWORD
# - STAGING_BOT_TOKEN
# - STAGING_API_KEYS (кожен окремо)
```

**Важливі зміни для stage:**

```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Database (stage БД)
DATABASE_URL=postgresql+asyncpg://yield_user_staging:STRONG_PASSWORD@postgres:5432/yield_db_staging

# Redis
REDIS_URL=redis://redis:6379/1

# Telegram Bot (окремий stage bot)
BOT_TOKEN=your_staging_bot_token_here

# Public URLs (замінити на реальні)
TRACKING_REDIRECT_URL=https://staging-api.earnaggregator.com
DATA_SERVICE_URL=http://yield-api:8000
```

#### Крок 4: Запуск сервісів

```bash
# Запустити stage середовище
docker-compose -f docker-compose.staging.yml up -d --build

# Перевірити статус
docker-compose -f docker-compose.staging.yml ps

# Перевірити логи
docker-compose -f docker-compose.staging.yml logs -f yield-api

# Перевірити health
curl http://localhost:8000/api/v1/health
```

#### Крок 5: Міграції БД

```bash
# Виконати міграції Alembic
docker-compose -f docker-compose.staging.yml exec yield-api alembic upgrade head

# Або для telegram-bot
docker-compose -f docker-compose.staging.yml exec telegram-bot alembic upgrade head
```

### Варіант 2: Cloud платформи

#### Railway.app

1. **Підключити GitHub репозиторій**
2. **Налаштувати змінні середовища** через Railway dashboard
3. **Налаштувати Dockerfile** для автоматичного деплою
4. **Railway автоматично деплоїть** при push в staging гілку

#### DigitalOcean App Platform

1. **Створити новий App** з GitHub репозиторію
2. **Вказати docker-compose.staging.yml**
3. **Налаштувати Environment Variables**
4. **Автоматичний деплой** при push

#### AWS / GCP / Azure

- Використати контейнери (ECS, Cloud Run, Container Instances)
- Або Kubernetes (EKS, GKE, AKS)
- Налаштувати через CI/CD pipeline

---

## 🔄 Деплой на хостинг

### Варіант 1: Ручний деплой

```bash
# На сервері
cd /opt/earnaggregator

# Отримати останні зміни
git pull origin staging

# Перебудувати образи
docker-compose -f docker-compose.staging.yml build --no-cache

# Зупинити старі контейнери
docker-compose -f docker-compose.staging.yml down

# Запустити нові контейнери
docker-compose -f docker-compose.staging.yml up -d

# Перевірити статус
docker-compose -f docker-compose.staging.yml ps

# Перевірити логи
docker-compose -f docker-compose.staging.yml logs -f
```

### Варіант 2: CI/CD з GitHub Actions

Створити `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ staging, develop ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.7.0
        with:
          ssh-private-key: ${{ secrets.STAGING_SSH_KEY }}

      - name: Deploy to staging server
        run: |
          ssh user@staging-server.com << 'EOF'
            cd /opt/earnaggregator
            git pull origin staging
            docker-compose -f docker-compose.staging.yml pull
            docker-compose -f docker-compose.staging.yml up -d --build
            docker-compose -f docker-compose.staging.yml exec -T yield-api alembic upgrade head || true
          EOF

      - name: Health check
        run: |
          sleep 30
          curl -f https://staging-api.earnaggregator.com/api/v1/health || exit 1
```

**Налаштування GitHub Secrets:**

1. `STAGING_SSH_KEY` - приватний SSH ключ для доступу до сервера
2. `STAGING_DB_PASSWORD` - пароль БД для stage
3. `STAGING_BOT_TOKEN` - токен Telegram бота для stage
4. Інші API ключі (за потреби)

### Варіант 3: Webhook деплой

```bash
# На сервері створити webhook endpoint
# /opt/earnaggregator/deploy.sh

#!/bin/bash
cd /opt/earnaggregator
git pull origin staging
docker-compose -f docker-compose.staging.yml up -d --build
```

---

## ✅ Перевірка та тестування

### Health Checks

```bash
# API Health
curl https://staging-api.earnaggregator.com/api/v1/health

# Telegram Bot (перевірити через бота)
# Надіслати /start в stage бот

# Broadcast Admin
curl https://staging-api.earnaggregator.com:8081/health

# Prometheus
curl http://staging-server.com:9090/-/healthy

# Grafana
curl http://staging-server.com:3000/api/health
```

### Тестування API

```bash
# Отримати топ продукти
curl https://staging-api.earnaggregator.com/api/v1/top?limit=5

# Отримати продукти для BTC
curl https://staging-api.earnaggregator.com/api/v1/yield/BTC

# Перевірити scheduler
curl https://staging-api.earnaggregator.com/api/v1/scheduler/status

# Перевірити метрики
curl https://staging-api.earnaggregator.com/api/v1/scheduler/metrics
```

### Перевірка БД

```bash
# Підключитися до БД
docker-compose -f docker-compose.staging.yml exec postgres psql -U yield_user_staging -d yield_db_staging

# Перевірити таблиці
\dt

# Перевірити кількість продуктів
SELECT COUNT(*) FROM yield_products;

# Перевірити останні оновлення
SELECT exchange, COUNT(*), MAX(updated_at) FROM yield_products GROUP BY exchange;
```

### Перевірка Redis

```bash
# Підключитися до Redis
docker-compose -f docker-compose.staging.yml exec redis redis-cli

# Перевірити ключі
KEYS *

# Перевірити кеш
GET yield:products:BTC
```

### Моніторинг

```bash
# Перевірити Prometheus targets
open http://staging-server.com:9090/targets

# Перевірити Grafana dashboards
open http://staging-server.com:3000

# Перевірити логи
docker-compose -f docker-compose.staging.yml logs -f --tail=100
```

---

## 📋 Чек-лист перед деплоєм

### Підготовка коду

- [ ] Створено `.env.example` з placeholders
- [ ] Створено `.env.staging` для stage середовища
- [ ] Створено `docker-compose.staging.yml`
- [ ] Перевірено що `.env` в `.gitignore`
- [ ] Очищено логи та бекапи з репозиторію
- [ ] Перевірено що секрети не в коді
- [ ] Оновлено README.md з інструкціями

### GitHub репозиторій

- [ ] Створено приватний репозиторій
- [ ] Додано всі необхідні файли
- [ ] НЕ додано секрети
- [ ] Створено гілку `staging` або `develop`
- [ ] Налаштовано GitHub Secrets (якщо використовується CI/CD)

### Хостинг

- [ ] Обрано хостинг (VPS/Cloud)
- [ ] Налаштовано Docker та Docker Compose
- [ ] Налаштовано файрвол (порти 80, 443, 8000, 8081)
- [ ] Налаштовано домен (опціонально)
- [ ] Налаштовано SSL сертифікати (опціонально)

### Конфігурація

- [ ] Створено окремі API ключі для stage (або тестові)
- [ ] Створено окремий Telegram бот для stage
- [ ] Налаштовано змінні середовища на сервері
- [ ] Налаштовано базу даних
- [ ] Налаштовано Redis

### Тестування

- [ ] Протестовано локально з `docker-compose.staging.yml`
- [ ] Протестовано API endpoints
- [ ] Протестовано Telegram бота
- [ ] Протестовано Broadcast Admin
- [ ] Протестовано міграції БД

### Безпека

- [ ] Всі паролі сильні та унікальні
- [ ] API ключі мають обмежені права (read-only)
- [ ] Налаштовано файрвол
- [ ] Налаштовано SSL (для production)
- [ ] Налаштовано backup стратегію

### Моніторинг

- [ ] Налаштовано Prometheus
- [ ] Налаштовано Grafana
- [ ] Налаштовано алерти
- [ ] Налаштовано логування

---

## 🚨 Розв'язання проблем

### Проблема: Контейнери не запускаються

```bash
# Перевірити логи
docker-compose -f docker-compose.staging.yml logs

# Перевірити конфігурацію
docker-compose -f docker-compose.staging.yml config

# Перевірити ресурси
docker stats

# Перебудувати образи
docker-compose -f docker-compose.staging.yml build --no-cache
```

### Проблема: БД не підключається

```bash
# Перевірити змінні середовища
docker-compose -f docker-compose.staging.yml exec yield-api env | grep DATABASE

# Перевірити доступність postgres
docker-compose -f docker-compose.staging.yml exec yield-api ping postgres

# Перевірити логи postgres
docker-compose -f docker-compose.staging.yml logs postgres
```

### Проблема: API ключі не працюють

```bash
# Перевірити змінні середовища
docker-compose -f docker-compose.staging.yml exec yield-api env | grep API_KEY

# Перевірити логи API
docker-compose -f docker-compose.staging.yml logs yield-api | grep -i error
```

### Проблема: Telegram бот не відповідає

```bash
# Перевірити токен
docker-compose -f docker-compose.staging.yml exec telegram-bot env | grep BOT_TOKEN

# Перевірити логи бота
docker-compose -f docker-compose.staging.yml logs telegram-bot

# Перевірити доступність API
docker-compose -f docker-compose.staging.yml exec telegram-bot curl http://yield-api:8000/api/v1/health
```

---

## 📚 Додаткові ресурси

### Документація

- [Deployment Guide](deployment.md) - загальний гайд по деплою
- [Docker Setup](docker-setup.md) - налаштування Docker
- [Development Guide](development-guide.md) - розробка

### Корисні команди

```bash
# Перезапуск сервісів
docker-compose -f docker-compose.staging.yml restart

# Зупинка всіх сервісів
docker-compose -f docker-compose.staging.yml down

# Видалення volumes (ОБЕРЕЖНО - видалить дані!)
docker-compose -f docker-compose.staging.yml down -v

# Перегляд використання ресурсів
docker stats

# Очищення старих образів
docker image prune -a
```

---

## 🎯 Наступні кроки

Після успішного деплою на stage:

1. **Тестування** - провести повне тестування всіх функцій
2. **Моніторинг** - перевірити метрики в Grafana
3. **Документація** - оновити документацію з stage URL
4. **Production** - підготовка до production деплою

---

**Створено:** 2025-01-XX  
**Автор:** EarnAggregator Team  
**Версія:** 1.0

