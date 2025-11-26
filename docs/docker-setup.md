# 🐳 Docker Setup Guide - EarnAggregator

## 📋 Зміст

1. [Огляд Архітектури](#огляд-архітектури)
2. [Структура Проекту](#структура-проекту)
3. [Контейнери та Сервіси](#контейнери-та-сервіси)
4. [Мережі та Volumes](#мережі-та-volumes)
5. [Команди для Роботи](#команди-для-роботи)
6. [Розробка vs Production](#розробка-vs-production)

---

## 🏗️ Огляд Архітектури

### Мікросервісна Архітектура

```
┌─────────────────────────────────────────────────────────────┐
│                    EarnAggregator                           │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React/Next.js)    │  Port: 3000                 │
├─────────────────────────────────────────────────────────────┤
│  Telegram Bot (Python)       │  Port: 8081                 │
├─────────────────────────────────────────────────────────────┤
│  Yield API (FastAPI)         │  Port: 8000                 │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL Database         │  Port: 5432                 │
│  Redis Cache                 │  Port: 6379                 │
└─────────────────────────────────────────────────────────────┘
```

### Порядок Запуску Сервісів

```
1. postgres    → База даних
2. redis       → Кеш
3. yield-api   → FastAPI сервіс
4. telegram-bot → Telegram Bot (пізніше)
5. frontend    → React додаток (пізніше)
```

---

## 📁 Структура Проекту

```
EarnAggregator/
├── .env                          # Змінні середовища
├── .env.example                  # Шаблон .env
├── .gitignore                    # Git ігнорування
├── Dockerfile                    # Образ для yield-api
├── docker-compose.yml            # Оркестрація сервісів
├── requirements.txt              # Python залежності
├── docs/                         # Документація
│   ├── docker-setup.md          # Цей файл
│   └── ...
├── logs/                         # Логи всіх сервісів
├── yield-data-service/           # FastAPI сервіс
│   ├── app/
│   │   ├── main.py
│   │   ├── db/
│   │   └── services/
│   └── tests/
├── yield-telegram-bot/           # Telegram Bot
│   ├── bot/
│   └── tests/
└── server/                       # Frontend
    ├── package.json
    └── ...
```

---

## 🐳 Контейнери та Сервіси

### 1. **postgres** - База Даних

```yaml
postgres:
  image: postgres:15-alpine
  container_name: earn-postgres
  ports: ["5432:5432"]
  environment:
    POSTGRES_DB: yield_db
    POSTGRES_USER: yield_user
    POSTGRES_PASSWORD: yield_secure_password_2024
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./yield-data-service/app/db/schema.sql:/docker-entrypoint-initdb.d/
```

**Призначення:**

- Зберігання даних про Earn продукти
- Історія змін APY
- Логи синхронізацій
- Статистика користувачів

### 2. **redis** - Кеш

```yaml
redis:
  image: redis:7-alpine
  container_name: earn-redis
  ports: ["6379:6379"]
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

**Призначення:**

- Кешування API відповідей
- Сесії користувачів
- Тимчасові дані

### 3. **yield-api** - FastAPI Сервіс

```yaml
yield-api:
  build: .
  container_name: earn-yield-api
  ports: ["8000:8000"]
  environment:
    - DATABASE_URL=postgresql://...
    - REDIS_URL=redis://...
  depends_on:
    - postgres
    - redis
```

**Призначення:**

- REST API для Earn продуктів
- Синхронізація з біржами
- Обробка запитів від Telegram Bot
- Аналітика та статистика

### 4. **telegram-bot** - Telegram Bot (Майбутнє)

```yaml
telegram-bot:
  build: ./yield-telegram-bot
  container_name: earn-telegram-bot
  environment:
    - BOT_TOKEN=${BOT_TOKEN}
    - DATA_SERVICE_URL=http://yield-api:8000
  depends_on:
    - yield-api
```

**Призначення:**

- Обробка команд користувачів
- Відправка рекомендацій
- Відстеження популярних запитів

### 5. **frontend** - React Додаток (Майбутнє)

```yaml
frontend:
  build: ./server
  container_name: earn-frontend
  ports: ["3000:3000"]
  environment:
    - NEXT_PUBLIC_API_URL=http://localhost:8000
  depends_on:
    - yield-api
```

**Призначення:**

- Веб-інтерфейс
- Візуалізація даних
- Графіки APY

---

## 🌐 Мережі та Volumes

### Мережі

#### **backend_net** - Внутрішня мережа бекенду

```yaml
networks:
  backend_net:
    driver: bridge
    name: earn_backend
```

**Підключені сервіси:**

- postgres
- redis
- yield-api
- telegram-bot

#### **frontend_net** - Мережа фронтенду

```yaml
networks:
  frontend_net:
    driver: bridge
    name: earn_frontend
```

**Підключені сервіси:**

- frontend

### Volumes (Постійні Дані)

#### **postgres_data** - Дані PostgreSQL

```yaml
volumes:
  postgres_data:
    driver: local
    name: earn_postgres_data
```

**Містить:**

- Таблиці та індекси
- Конфігурацію БД
- Логи PostgreSQL

#### **redis_data** - Дані Redis

```yaml
volumes:
  redis_data:
    driver: local
    name: earn_redis_data
```

**Містить:**

- Кешовані дані
- Сесії користувачів
- Тимчасові ключі

---

## 🚀 Команди для Роботи

### Основні Команди

#### Запуск всіх сервісів

```bash
# Запуск в фоновому режимі
docker-compose up -d

# Запуск з логами
docker-compose up

# Перебудова образів
docker-compose up --build
```

#### Зупинка сервісів

```bash
# Зупинка (зберігає дані)
docker-compose down

# Зупинка з видаленням volumes
docker-compose down -v

# Зупинка з видаленням образів
docker-compose down --rmi all
```

#### Перегляд статусу

```bash
# Статус контейнерів
docker-compose ps

# Логи сервісу
docker-compose logs yield-api
docker-compose logs postgres

# Логи в реальному часі
docker-compose logs -f yield-api
```

### Робота з Контейнерами

#### Підключення до контейнера

```bash
# Підключитись до yield-api
docker-compose exec yield-api bash

# Підключитись до postgres
docker-compose exec postgres psql -U yield_user -d yield_db

# Підключитись до redis
docker-compose exec redis redis-cli
```

#### Перезапуск сервісу

```bash
# Перезапуск yield-api
docker-compose restart yield-api

# Перезапуск з перебудовою
docker-compose up --build yield-api
```

### Робота з Базами Даних

#### Виконання SQL скриптів

```bash
# Виконати schema.sql
docker-compose exec postgres psql -U yield_user -d yield_db -f /docker-entrypoint-initdb.d/01-schema.sql

# Створити backup
docker-compose exec postgres pg_dump -U yield_user yield_db > backup.sql

# Відновити з backup
docker-compose exec -T postgres psql -U yield_user -d yield_db < backup.sql
```

#### Перевірка підключення

```bash
# Перевірити БД
docker-compose exec yield-api python -c "
import psycopg2
conn = psycopg2.connect('postgresql://yield_user:yield_secure_password_2024@postgres:5432/yield_db')
print('✅ PostgreSQL connected')
conn.close()
"

# Перевірити Redis
docker-compose exec yield-api python -c "
import redis
r = redis.Redis(host='redis', port=6379, db=0)
r.ping()
print('✅ Redis connected')
"
```

---

## 🔧 Розробка vs Production

### Development (Поточна конфігурація)

**Особливості:**

- ✅ Hot reload (автооновлення коду)
- ✅ Детальні логи
- ✅ Debug режим
- ✅ Локальні порти відкриті

**Змінні:**

```env
ENVIRONMENT=development
DEBUG=true
API_RELOAD=true
LOG_LEVEL=DEBUG
```

### Production (Майбутня конфігурація)

**Особливості:**

- ✅ Оптимізовані образи
- ✅ Health checks
- ✅ Resource limits
- ✅ SSL сертифікати

**Змінні:**

```env
ENVIRONMENT=production
DEBUG=false
API_RELOAD=false
LOG_LEVEL=INFO
```

---

## 📊 Моніторинг та Логи

### Health Checks

Всі сервіси мають health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Логи

```bash
# Всі логи
docker-compose logs

# Конкретний сервіс
docker-compose logs yield-api

# Останні 100 рядків
docker-compose logs --tail=100 yield-api

# Логи з timestamp
docker-compose logs -t yield-api
```

### Моніторинг Ресурсів

```bash
# Використання ресурсів
docker stats

# Інформація про контейнери
docker-compose ps

# Використання disk space
docker system df
```

---

## 🚨 Troubleshooting

### Проблема: Контейнер не запускається

```bash
# Перевірити логи
docker-compose logs yield-api

# Перевірити конфігурацію
docker-compose config

# Перебудувати образ
docker-compose build --no-cache yield-api
```

### Проблема: База даних недоступна

```bash
# Перевірити статус postgres
docker-compose exec postgres pg_isready -U yield_user

# Перевірити підключення
docker-compose exec yield-api python -c "
import psycopg2
conn = psycopg2.connect('postgresql://yield_user:yield_secure_password_2024@postgres:5432/yield_db')
print('Connected!')
"
```

### Проблема: Порти зайняті

```bash
# Перевірити які порти використовуються
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Зупинити конфліктуючі процеси
sudo kill -9 <PID>
```

---

## 📝 Налаштування Docker, кроки

### Частина 1: Аналіз Проекту та Створення Docker Структури
- [ ] Створити структуру Docker файлів
- [ ] Оновити .env файл з усіма змінними
- [ ] Створити Dockerfile для yield-data-service
- [ ] Створити docker-compose.yml для всіх сервісів
- [ ] Створити документацію по Docker структурі

### Частина 2: Тестування Docker Setup

- [ ] Запуск docker-compose up
- [ ] Перевірка health checks
- [ ] Тестування підключення БД
- [ ] Перевірка API endpoints

### Частина 3: Додавання Telegram Bot

- [ ] Dockerfile для telegram-bot
- [ ] Налаштування в docker-compose
- [ ] Тестування інтеграції

### Частина 4: Додавання Frontend

- [ ] Dockerfile для React додатку
- [ ] Налаштування в docker-compose
- [ ] Тестування повної архітектури

---
