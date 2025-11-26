# 🏗️ EarnAggregator Architecture

## 📋 Зміст

1. [Загальна архітектура](#загальна-архітектура)
2. [Мікросервіси](#мікросервіси)
3. [База даних](#база-даних)
4. [Кешування](#кешування)
5. [API Gateway](#api-gateway)
6. [Моніторинг](#моніторинг)
7. [Безпека](#безпека)

---

## 🎯 Загальна архітектура

EarnAggregator - це мікросервісна система для агрегації та аналізу Earn продуктів з різних криптобірж.

### **Архітектурна діаграма:**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Web Frontend  │    │   Mobile App    │
│   (Aiogram)     │    │   (Next.js)     │    │   (React Native)│
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     API Gateway          │
                    │   (FastAPI + CORS)       │
                    └─────────────┬─────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│  Data Service   │    │  Telegram Bot   │    │  Scheduler      │
│  (FastAPI)      │    │  Service        │    │  Service        │
│                 │    │  (Aiogram)      │    │  (APScheduler)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   PostgreSQL    │    │      Redis       │    │  External APIs  │
│   (Database)    │    │     (Cache)      │    │ (Binance, Bybit)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🔧 Мікросервіси

### **1. Data Service (FastAPI)**

**Призначення:** Основний API для отримання даних про Earn продукти.

**Технології:**

- **FastAPI** - асинхронний веб-фреймворк
- **SQLAlchemy** - ORM для роботи з PostgreSQL
- **Pydantic** - валідація даних
- **httpx** - HTTP клієнт для API бірж

**Функції:**

- Агрегація даних з різних бірж
- Кешування результатів
- API endpoints для клієнтів
- Валідація та нормалізація даних

**Приклад структури:**

```
yield-data-service/
├── app/
│   ├── main.py              # FastAPI додаток
│   ├── config.py            # Налаштування
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── services/
│   │   ├── exchanges/       # Інтеграції з біржами
│   │   ├── cache.py        # Redis кешування
│   │   └── scheduler.py    # Фонові задачі
│   ├── db/
│   │   ├── models.py       # SQLAlchemy моделі
│   │   └── crud.py         # CRUD операції
│   └── utils/
│       └── logger.py       # Логування
```

### **2. Telegram Bot Service (Aiogram)**

**Призначення:** Telegram бот для взаємодії з користувачами.

**Технології:**

- **Aiogram 3.x** - Telegram Bot framework
- **Redis** - зберігання стану користувачів (FSM)
- **PostgreSQL** - історія запитів користувачів

**Функції:**

- Команди `/yield`, `/top`, `/recommendations`
- Персоналізовані рекомендації
- Реферальні посилання
- Статистика користувачів

### **3. Scheduler Service (APScheduler)**

**Призначення:** Автоматичне оновлення даних.

**Функції:**

- Оновлення кешу кожну годину
- Синхронізація з API бірж
- Очищення застарілих даних
- Моніторинг здоров'я сервісів

---

## 🗄️ База даних

### **PostgreSQL - Основна БД**

**Таблиці:**

#### **earn_products** - Earn продукти

```sql
CREATE TABLE earn_products (
    product_id VARCHAR(255) PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    apy DECIMAL(10,4) NOT NULL,
    min_amount DECIMAL(20,8),
    max_amount DECIMAL(20,8),
    lock_period_days INTEGER,
    product_type VARCHAR(50),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    is_cefi BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_api_sync TIMESTAMP,
    remaining_pool_size DECIMAL(20,8),
    global_product BOOLEAN DEFAULT false,
    exchange_specific_data JSONB
);
```

#### **earn_products_history** - Історія змін

```sql
CREATE TABLE earn_products_history (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) REFERENCES earn_products(product_id),
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT NOW()
);
```

#### **api_sync_log** - Лог синхронізації

```sql
CREATE TABLE api_sync_log (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    products_count INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### **user_queries** - Статистика користувачів

```sql
CREATE TABLE user_queries (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### **Індекси для продуктивності:**

```sql
-- Швидкий пошук по символу та біржі
CREATE INDEX idx_earn_products_symbol_exchange ON earn_products(symbol, exchange);

-- Сортування по APY
CREATE INDEX idx_earn_products_apy ON earn_products(apy DESC);

-- Активні продукти
CREATE INDEX idx_earn_products_active ON earn_products(is_active) WHERE is_active = true;

-- Статистика користувачів
CREATE INDEX idx_user_queries_user_timestamp ON user_queries(user_id, timestamp);
```

---

## ⚡ Кешування

### **Redis - In-Memory Cache**

**Стратегія кешування:**

#### **1. Ключі кешу:**

```
yield:{SYMBOL}              # Дані по монеті (yield:BTC)
top:yields:{LIMIT}          # Топ пропозицій (top:yields:10)
recommendations:{USER_ID}    # Рекомендації користувача
exchange:{EXCHANGE}:products # Продукти конкретної біржі
```

#### **2. Час життя (TTL):**

- **Популярні монети (BTC, ETH):** 1 година
- **Рідкісні монети:** 6 годин
- **Топ списки:** 30 хвилин
- **Рекомендації:** 2 години

#### **3. Приклад використання:**

```python
# Збереження в кеш
await redis.setex(
    "yield:BTC",
    3600,  # 1 година
    json.dumps(products_data)
)

# Отримання з кешу
cached_data = await redis.get("yield:BTC")
if cached_data:
    return json.loads(cached_data)
```

---

## 🌐 API Gateway

### **FastAPI як API Gateway**

**Функції:**

- **CORS** - підтримка крос-доменних запитів
- **Rate Limiting** - обмеження кількості запитів
- **Authentication** - авторизація (буде додана)
- **Request/Response Logging** - логування запитів
- **Error Handling** - централізована обробка помилок

**Приклад middleware:**

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} ({process_time:.3f}s)"
    )
    return response
```

---

## 📊 Моніторинг

### **Health Checks**

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": await check_database(),
            "redis": await check_redis(),
            "exchanges": await check_exchanges()
        }
    }
```

### **Метрики:**

- **API Response Time** - час відповіді
- **Cache Hit Rate** - ефективність кешу
- **Exchange API Errors** - помилки з бірж
- **Database Connections** - підключення до БД

### **Логування:**

```python
# Структуроване логування
logger.info("API request", extra={
    "method": "GET",
    "endpoint": "/api/v1/yield/BTC",
    "user_id": 123456,
    "response_time": 0.150
})
```

---

## 🔒 Безпека

### **Поточні заходи:**

- **CORS** - контроль доступу
- **Rate Limiting** - захист від DDoS
- **Input Validation** - валідація вхідних даних
- **SQL Injection Protection** - ORM захист

### **Майбутні заходи:**

- **JWT Authentication** - токени доступу
- **API Keys** - ключі для клієнтів
- **HTTPS** - шифрування трафіку
- **Request Signing** - підпис запитів

### **Приклад валідації:**

```python
from pydantic import BaseModel, validator

class YieldRequest(BaseModel):
    symbol: str

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalpha() or len(v) < 2 or len(v) > 10:
            raise ValueError('Invalid symbol format')
        return v.upper()
```

---

## 🚀 Deployment Architecture

### **Docker Compose (Development)**

```yaml
services:
  postgres: # PostgreSQL database
  redis: # Redis cache
  yield-api: # FastAPI service
  telegram-bot: # Telegram bot (буде додано)
  scheduler: # Background tasks (буде додано)
```

### **Production (Майбутнє)**

- **Kubernetes** - оркестрація контейнерів
- **Load Balancer** - розподіл навантаження
- **Monitoring** - Prometheus + Grafana
- **Logging** - ELK Stack

---

## 📈 Масштабування

### **Горизонтальне масштабування:**

- **API Replicas** - кілька екземплярів FastAPI
- **Database Read Replicas** - репліки PostgreSQL
- **Redis Cluster** - кластер Redis

### **Вертикальне масштабування:**

- **CPU/Memory** - збільшення ресурсів
- **Database Optimization** - оптимізація запитів
- **Caching Strategy** - покращення кешування

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Архітектура визначена
