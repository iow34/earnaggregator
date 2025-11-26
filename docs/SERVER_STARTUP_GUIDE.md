# Інструкція по запуску сервера

## 🎯 Рішення конфлікту портів

### Автоматичне рішення

**Рекомендовано:** Використовувати різні порти для різних середовищ

```bash
# Автоматичний пошук вільних портів
python port_manager.py
```

### Ручне рішення

**Docker контейнер:** `localhost:8000`  
**Локальна розробка:** `localhost:8001` (або інший вільний)

```bash
# Запуск локального сервера (автоматично порт 8001)
python run_server.py

# Або вручну вказати порт
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Неправильна конфігурація БД

**Проблема:** Використовувався Docker connection string без `asyncpg` драйвера

**Було:**

```
DATABASE_URL=postgresql://yield_user:yield_secure_password_2024@postgres:5432/yield_db
REDIS_HOST=redis
```

**Стало:**

```
DATABASE_URL=postgresql+asyncpg://yield_user:yield_secure_password_2024@localhost:5432/yield_db
REDIS_HOST=localhost
```

### 3. Відсутня залежність asyncpg

**Проблема:** `No module named 'asyncpg'`

**Рішення:**

```bash
cd yield-data-service
pip install asyncpg
```

### 4. Блокування при старті

**Проблема:** Сервер блокувався при спробі підключитися до недоступної БД

**Рішення:** Додано try/catch в `lifespan` функцію в `app/main.py`

## Способи запуску сервера

### Спосіб 1: Використання Python скрипта (рекомендований)

```bash
cd yield-data-service
python run_server.py
```

### Спосіб 2: Прямий запуск з змінними середовища

```bash
cd yield-data-service
export DATABASE_URL="postgresql+asyncpg://yield_user:yield_secure_password_2024@localhost:5432/yield_db"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Спосіб 3: Використання Bash скрипта

```bash
cd yield-data-service
./start_server.sh
```

## Перевірка роботи

### Базовий тест

```bash
curl http://localhost:8000/
# Очікувана відповідь: {"message":"EarnAggregator Data Service","status":"running","version":"1.0.0"}
```

### Health check

```bash
curl http://localhost:8000/health
```

### Документація API

Відкрити в браузері: `http://localhost:8000/docs`

## Важливі зауваження

1. **PostgreSQL** повинен бути запущений локально або доступний на `localhost:5432`
2. **Redis** повинен бути запущений локально або доступний на `localhost:6379`
3. Якщо БД недоступна, сервер все одно запуститься (тільки endpoints з БД не працюватимуть)
4. Якщо Redis недоступний, використовується fallback in-memory кеш

## Troubleshooting

### Порт зайнятий

```bash
# Знайти процес
lsof -i :8000

# Зупинити процес
kill -9 <PID>
```

### Проблеми з БД

- Перевірити що PostgreSQL запущений
- Перевірити правильність DATABASE_URL
- Перевірити що asyncpg встановлений: `pip install asyncpg`

### Проблеми з Redis

- Перевірити що Redis запущений: `redis-cli ping`
- Без Redis сервіс працює з fallback кешем
