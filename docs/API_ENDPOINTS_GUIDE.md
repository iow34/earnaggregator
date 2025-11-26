# Детальна інструкція по API Endpoints

## Розділ 1: Вступ та налаштування

### Що таке API Endpoints

API Endpoints (кінцеві точки API) - це адреси для взаємодії з EarnAggregator Data Service. Кожен endpoint представляє конкретну функціональність, таку як:

- Отримання даних про Earn продукти
- Управління кешем
- Моніторинг стану системи
- Синхронізація з біржами

### Базовий URL сервісу

**Локальна розробка:**

```
http://localhost:8000
```

**Продакшн:**

```
https://your-domain.com
```

### Як запустити сервер локально

1. **Підготовка середовища:**

```bash
cd yield-data-service
pip install -r requirements.txt
```

2. **Налаштування змінних середовища:**

```bash
# Скопіюйте .env.example в .env
cp .env.example .env

# Відредагуйте необхідні змінні
nano .env
```

3. **Запуск сервера:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Перевірка запуску:**

```bash
curl http://localhost:8000/
# Відповідь: {"message": "EarnAggregator Data Service", "status": "running", "version": "1.0.0"}
```

### Перевірка доступності API

**Базовий перевір:**

```bash
curl http://localhost:8000/
```

**Очікувана відповідь:**

```json
{
  "message": "EarnAggregator Data Service",
  "status": "running",
  "version": "1.0.0"
}
```

**Через браузер:**
Відкрийте `http://localhost:8000/` в браузері.

## Розділ 2: Загальні API Endpoints

### 2.1 Health Check

**Endpoint:** `GET /health`

**Призначення:** Перевірка стану сервісу, бази даних та кешу.

**Відповідь:**

```json
{
  "service": "yield-data-service",
  "version": "1.0.0",
  "status": "healthy",
  "database": {
    "status": "healthy",
    "connection_pool": "active"
  },
  "cache": {
    "status": "healthy",
    "redis_connected": true,
    "fallback_active": false
  },
  "api": {
    "binance": "healthy",
    "bybit": "healthy"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/health
```

**Браузер:**
Відкрийте `http://localhost:8000/health`

**Python:**

```python
import requests

response = requests.get("http://localhost:8000/health")
health_data = response.json()
print(f"Status: {health_data['status']}")
```

### 2.2 API Статистика

**Endpoint:** `GET /api/v1/stats`

**Призначення:** Отримання статистики бази даних та продуктів.

**Параметри:** Немає

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "total_products": 1250,
    "products_by_provider": {
      "Binance": 450,
      "Bybit": 800
    },
    "products_by_symbol": {
      "BTC": 45,
      "ETH": 38,
      "USDT": 52
    },
    "last_updated": "2024-01-15T10:30:00Z"
  },
  "message": "Статистика отримана успішно"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/stats
```

**Фільтрація в JavaScript:**

```javascript
fetch("http://localhost:8000/api/v1/stats")
  .then((response) => response.json())
  .then((data) => {
    console.log(`Всього продуктів: ${data.data.total_products}`);
    console.log(`Binance: ${data.data.products_by_provider.Binance}`);
  });
```

## Розділ 3: Yield Products Endpoints

### 3.1 Отримання продуктів за символом

**Endpoint:** `GET /api/v1/yield/{symbol}`

**Призначення:** Отримати всі Earn продукти для конкретної криптовалюти.

**Параметри:**

- `symbol` (обов'язковий): Символ криптовалюти (BTC, ETH, USDT, тощо)

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "binance_btc_flexible",
      "symbol": "BTC",
      "name": "Bitcoin Flexible Staking",
      "provider": "Binance",
      "apy": 2.5,
      "is_cefi": true,
      "min_amount": 0.0001,
      "max_amount": 1000.0,
      "lock_period_days": 0,
      "max_apy": 2.8,
      "risk_level": "Low",
      "is_active": true,
      "website_url": "https://www.binance.com/earn",
      "description": "Flexible Bitcoin staking",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1,
  "cached": true,
  "source": "cache",
  "message": "Знайдено 1 продуктів для BTC"
}
```

**Приклади використання:**

**Curl - отримання BTC продуктів:**

```bash
curl http://localhost:8000/api/v1/yield/BTC
```

**Curl - отримання ETH продуктів:**

```bash
curl http://localhost:8000/api/v1/yield/ETH
```

**JavaScript:**

```javascript
async function getYieldProducts(symbol) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/v1/yield/${symbol}`
    );
    const data = await response.json();

    if (data.success) {
      console.log(`Знайдено ${data.count} продуктів для ${symbol}`);
      data.data.forEach((product) => {
        console.log(`${product.provider}: ${product.apy}% APY`);
      });
    }
  } catch (error) {
    console.error("Помилка:", error);
  }
}

getYieldProducts("BTC");
```

**Python requests:**

```python
import requests

def get_yield_products(symbol):
    url = f"http://localhost:8000/api/v1/yield/{symbol}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"Знайдено {data['count']} продуктів для {symbol}")
            for product in data['data']:
                print(f"{product['provider']}: {product['apy']}% APY")
        else:
            print(f"Помилка: {data['message']}")
    else:
        print(f"HTTP помилка: {response.status_code}")

get_yield_products('BTC')
```

### 3.2 Топ продуктів

**Endpoint:** `GET /api/v1/top`

**Призначення:** Отримати топ найкращих пропозицій за APY.

**Параметри (query):**

- `limit` (опціональний, default: 20): Кількість продуктів
- `sort` (опціональний, default: "apy"): Сортування (apy, min_amount, provider)

**Приклади URL:**

```
GET /api/v1/top
GET /api/v1/top?limit=10
GET /api/v1/top?limit=50&sort=apy
```

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "bybit_alt_high_yield",
      "symbol": "ALPHA",
      "name": "Alpha Token High Yield",
      "provider": "Bybit",
      "apy": 15.7,
      "is_cefi": false,
      "min_amount": 10.0,
      "lock_period_days": 30,
      "risk_level": "High",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1,
  "cached": true,
  "source": "cache",
  "message": "Топ 1 продуктів за APY"
}
```

**Приклади використання:**

**Curl - топ 10 продуктів:**

```bash
curl http://localhost:8000/api/v1/top?limit=10
```

**Curl - топ за APY:**

```bash
curl "http://localhost:8000/api/v1/top?limit=20&sort=apy"
```

**Браузер:** Відкрийте `http://localhost:8000/api/v1/top?limit=10`

### 3.3 Отримання всіх продуктів з фільтрацією

**Endpoint:** `GET /api/v1/products`

**Призначення:** Отримати всі продукти з можливістю фільтрації.

**Параметри (query):**

- `limit` (опціональний): Кількість продуктів
- `offset` (опціональний): Зміщення для пагінації
- `symbol` (опціональний): Фільтр по символу
- `provider` (опціональний): Фільтр по провайдеру (Binance, Bybit)
- `min_apy` (опціональний): Мінімальний APY
- `max_apy` (опціональний): Максимальний APY

**Приклади URL:**

```
GET /api/v1/products
GET /api/v1/products?symbol=BTC&provider=Binance
GET /api/v1/products?min_apy=5.0&max_apy=20.0
GET /api/v1/products?limit=100&offset=50
```

**Приклади використання:**

**Curl - фільтр по провайдеру:**

```bash
curl "http://localhost:8000/api/v1/products?provider=Bybit&limit=20"
```

**Curl - фільтр по APY:**

```bash
curl "http://localhost:8000/api/v1/products?min_apy=10.0&max_apy=25.0"
```

### 3.4 Створення продукту

**Endpoint:** `POST /api/v1/products`

**Призначення:** Створити новий продукт (для адміністративних цілей).

**Тіло запиту (JSON):**

```json
{
  "symbol": "NEW",
  "name": "New Token Staking",
  "provider": "CustomProvider",
  "apy": 12.5,
  "is_cefi": true,
  "min_amount": 1.0,
  "max_amount": 1000.0,
  "lock_period_days": 0,
  "max_apy": 15.0,
  "risk_level": "Medium",
  "website_url": "https://example.com",
  "description": "Custom staking product"
}
```

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "id": "custom_new_token_001",
    "symbol": "NEW",
    "name": "New Token Staking",
    "provider": "CustomProvider",
    "apy": 12.5,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "message": "Продукт створено успішно"
}
```

**Приклади використання:**

**Curl:**

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NEW",
    "name": "New Token Staking",
    "provider": "CustomProvider",
    "apy": 12.5,
    "is_cefi": true,
    "min_amount": 1.0,
    "lock_period_days": 0,
    "risk_level": "Medium"
  }'
```

**Python requests:**

```python
import requests

product_data = {
    "symbol": "NEW",
    "name": "New Token Staking",
    "provider": "CustomProvider",
    "apy": 12.5,
    "is_cefi": True,
    "min_amount": 1.0,
    "lock_period_days": 0,
    "risk_level": "Medium"
}

response = requests.post(
    "http://localhost:8000/api/v1/products",
    json=product_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    result = response.json()
    print(f"Створено продукт: {result['data']['id']}")
```

## Розділ 4: Cache Management Endpoints

### 4.1 Статистика кешу

**Endpoint:** `GET /api/v1/cache/stats`

**Призначення:** Отримати статистику використання кешу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "hits": 245,
    "misses": 89,
    "sets": 156,
    "deletes": 12,
    "errors": 0,
    "total_requests": 334,
    "hit_rate_percent": 73.35,
    "redis_connected": true,
    "fallback_cache_size": 0,
    "last_reset": "2024-01-15T09:00:00Z"
  },
  "message": "Статистика кешу отримана успішно"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/cache/stats
```

**Моніторинг в реальному часі:**

```bash
# Оновлення кожні 5 секунд
watch -n 5 'curl -s http://localhost:8000/api/v1/cache/stats | jq .data.hit_rate_percent'
```

### 4.2 Очищення кешу

**Endpoint:** `POST /api/v1/cache/clear`

**Призначення:** Очистити кеш за патерном.

**Параметри (query):**

- `pattern` (опціональний, default: "\*"): Патерн для видалення ключів

**Приклади патернів:**

- `*` - видалити всі ключі
- `yield:*` - видалити тільки yield ключі
- `exchange:binance:*` - видалити тільки Binance ключі

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "deleted_count": 45,
    "pattern": "*"
  },
  "message": "Кеш очищено: видалено 45 ключів"
}
```

**Приклади використання:**

**Curl - очистити весь кеш:**

```bash
curl -X POST http://localhost:8000/api/v1/cache/clear
```

**Curl - очистити тільки yield кеш:**

```bash
curl -X POST "http://localhost:8000/api/v1/cache/clear?pattern=yield:*"
```

**Curl - очистити тільки Binance кеш:**

```bash
curl -X POST "http://localhost:8000/api/v1/cache/clear?pattern=exchange:binance:*"
```

### 4.3 Health check кешу

**Endpoint:** `GET /api/v1/cache/health`

**Призначення:** Перевірити стан кешу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "message": "Redis підключено та працює",
    "connected_to_redis": true,
    "fallback_cache_active": false,
    "fallback_cache_size": 0,
    "last_checked": "2024-01-15T10:30:00Z"
  },
  "message": "Стан кешу перевірено"
}
```

**Варіанти статусу:**

- `healthy` - Redis працює нормально
- `degraded` - Redis недоступний, використовується fallback
- `unhealthy` - Проблеми з кешуванням

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/cache/health
```

## Розділ 5: Binance API Endpoints

### 5.1 Тест підключення

**Endpoint:** `GET /api/v1/binance/test`

**Призначення:** Перевірка підключення до Binance API.

**Відповідь (успішна):**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "message": "Підключення до Binance API успішне",
    "response_time_ms": 245.67,
    "api_status": "active",
    "products_found": 12,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Тест підключення до Binance API виконано"
}
```

**Відповідь (помилка - відсутні ключі):**

```json
{
  "success": true,
  "data": {
    "status": "error",
    "message": "Binance API ключі не налаштовані в .env",
    "configured": false
  },
  "message": "Тест підключення до Binance API виконано"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/binance/test
```

### 5.2 Отримання продуктів

**Endpoint:** `GET /api/v1/binance/products`

**Призначення:** Отримати продукти Binance з кешуванням.

**Параметри (query):**

- `symbol` (опціональний): Фільтр по символу

**Приклади URL:**

```
GET /api/v1/binance/products
GET /api/v1/binance/products?symbol=BTC
```

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "binance_btc_flexible_001",
      "symbol": "BTC",
      "name": "Bitcoin Flexible Savings",
      "provider": "Binance",
      "apy": 2.5,
      "is_cefi": true,
      "min_amount": 0.0001,
      "lock_period_days": 0,
      "risk_level": "Low",
      "is_active": true,
      "raw_data": {
        "asset": "BTC",
        "annualInterestRate": "2.5000",
        "productId": "BTC_FLEXIBLE_SAVINGS"
      }
    }
  ],
  "message": "Отримано 1 продуктів Binance",
  "cached": true
}
```

**Приклади використання:**

**Curl - всі продукти:**

```bash
curl http://localhost:8000/api/v1/binance/products
```

**Curl - тільки BTC:**

```bash
curl "http://localhost:8000/api/v1/binance/products?symbol=BTC"
```

### 5.3 Синхронізація

**Endpoint:** `POST /api/v1/binance/sync`

**Призначення:** Синхронізувати продукти Binance з API в БД.

**Параметри (query):**

- `symbol` (опціональний): Синхронізувати тільки конкретний символ

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "message": "Синхронізація завершена",
    "products_count": 45,
    "sync_stats": {
      "created": 12,
      "updated": 33,
      "errors": 0
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Синхронізація Binance завершена: 12 створено, 33 оновлено"
}
```

**Приклади використання:**

**Curl - повна синхронізація:**

```bash
curl -X POST http://localhost:8000/api/v1/binance/sync
```

**Curl - синхронізація тільки BTC:**

```bash
curl -X POST "http://localhost:8000/api/v1/binance/sync?symbol=BTC"
```

### 5.4 Health check Binance

**Endpoint:** `GET /api/v1/binance/health`

**Призначення:** Перевірити стан Binance сервісу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "service": "binance",
    "configured": true,
    "connection": {
      "status": "success",
      "response_time_ms": 189.45,
      "products_found": 45
    },
    "cache_stats": {
      "hits": 23,
      "misses": 8,
      "hit_rate_percent": 74.19
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Стан Binance сервісу перевірено"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/binance/health
```

## Розділ 6: Bybit API Endpoints

### 6.1 Тест підключення

**Endpoint:** `GET /api/v1/bybit/test`

**Призначення:** Перевірка підключення до Bybit API (публічний API).

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "message": "Підключення до Bybit API успішне",
    "response_time_ms": 156.78,
    "api_status": "active",
    "products_found": 8,
    "public_api": true,
    "configured": true,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Тест підключення до Bybit API виконано"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/bybit/test
```

### 6.2 Отримання продуктів

**Endpoint:** `GET /api/v1/bybit/products`

**Призначення:** Отримати продукти Bybit з кешуванням.

**Параметр (query):**

- `symbol` (опціональний): Фільтр по символу

**Приклади URL:**

```
GET /api/v1/bybit/products
GET /api/v1/bybit/products?symbol=BTC
```

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "bybit_btc_flexible_001",
      "symbol": "BTC",
      "name": "BTC Flexible Saving",
      "provider": "Bybit",
      "apy": 3.2,
      "is_cefi": true,
      "min_amount": 0.001,
      "lock_period_days": 0,
      "risk_level": "Low",
      "is_active": true,
      "product_category": "FlexibleSaving",
      "raw_data": {
        "coin": "BTC",
        "apy": "3.20",
        "category": "FlexibleSaving"
      }
    }
  ],
  "message": "Отримано 1 продуктів Bybit",
  "cached": true
}
```

**Приклади використання:**

**Curl - всі продукти:**

```bash
curl http://localhost:8000/api/v1/bybit/products
```

**Curl - тільки ETH:**

```bash
curl "http://localhost:8000/api/v1/bybit/products?symbol=ETH"
```

### 6.3 Синхронізація

**Endpoint:** `POST /api/v1/bybit/sync`

**Призначення:** Синхронізувати продукти Bybit з API в БД.

**Параметр (query):**

- `symbol` (опціональний): Синхронізувати тільки конкретний символ

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "message": "Синхронізація завершена",
    "products_count": 234,
    "sync_stats": {
      "created": 89,
      "updated": 145,
      "errors": 0
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Синхронізація Bybit завершена: 89 створено, 145 оновлено"
}
```

**Приклади використання:**

**Curl - повна синхронізація:**

```bash
curl -X POST http://localhost:8000/api/v1/bybit/sync
```

**Curl - синхронізація тільки ETH:**

```bash
curl -X POST "http://localhost:8000/api/v1/bybit/sync?symbol=ETH"
```

### 6.4 Health check Bybit

**Endpoint:** `GET /api/v1/bybit/health`

**Призначення:** Перевірити стан Bybit сервісу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "service": "bybit",
    "configured": true,
    "connection": {
      "status": "success",
      "response_time_ms": 98.23,
      "public_api": true
    },
    "cache_stats": {
      "hits": 156,
      "misses": 34,
      "hit_rate_percent": 82.11
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "Стан Bybit сервісу перевірено"
}
```

**Приклади використання:**

**Curl:**

```bash
curl http://localhost:8000/api/v1/bybit/health
```

## Розділ 7: Troubleshooting та помилки

### 7.1 Типові HTTP коди помилок

| Код | Назва                 | Опис                  | Рішення                       |
| --- | --------------------- | --------------------- | ----------------------------- |
| 200 | OK                    | Успішний запит        | -                             |
| 400 | Bad Request           | Неправильні параметри | Перевірити вхідні дані        |
| 404 | Not Found             | Endpoint не знайдено  | Перевірити URL                |
| 500 | Internal Server Error | Помилка сервера       | Перевірити логи               |
| 503 | Service Unavailable   | Сервіс недоступний    | Перевірити підключення БД/API |

### 7.2 Сценарії коли endpoints не працюють

#### Сценарій 1: Сервіс не запущений

**Симптоми:**

```bash
curl http://localhost:8000/health
# curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Рішення:**

```bash
# Перевірити процеси
ps aux | grep uvicorn

# Запустити сервіс
cd yield-data-service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Перевірити порт
netstat -tlnp | grep 8000
```

#### Сценарій 2: PostgreSQL недоступний

**Симптоми:**

```json
{
  "status": "unhealthy",
  "database": {
    "status": "unhealthy",
    "error": "Connection refused"
  }
}
```

**Рішення:**

```bash
# Перевірити Docker контейнер
docker ps | grep postgres

# Запустити PostgreSQL
docker run -d \
  --name yield_postgres \
  -e POSTGRES_DB=yield_db \
  -e POSTGRES_USER=yield_user \
  -e POSTGRES_PASSWORD=yield_secure_password_2024 \
  -p 5432:5432 \
  postgres:15

# Перевірити підключення
psql -h localhost -p 5432 -U yield_user -d yield_db
```

#### Сценарій 3: Redis недоступний

**Симптоми:**

```json
{
  "cache": {
    "status": "degraded",
    "message": "Redis недоступний, використовується fallback кеш"
  }
}
```

**Рішення:**

```bash
# Запустити Redis
docker run -d --name yield_redis -p 6379:6379 redis:alpine

# Або ігнорувати - система працює з fallback кешем
```

#### Сценарій 4: API ключі не налаштовані

**Симптоми:**

```json
{
  "data": {
    "status": "error",
    "message": "Binance API ключі не налаштовані в .env"
  }
}
```

**Рішення:**

```bash
# Перевірити .env файл
cat .env | grep BINANCE

# Додати ключі (якщо немає)
echo "BINANCE_API_KEY=your_api_key_here" >> .env
echo "BINANCE_API_SECRET=your_api_secret_here" >> .env

# Перезавантажити сервіс
```

#### Сценарій 5: Біржа недоступна

**Симптоми:**

```json
{
  "data": {
    "status": "error",
    "message": "Connection timeout to exchange API"
  }
}
```

**Рішення:**

1. Перевірити інтернет з'єднання
2. Перевірити статус біржі
3. Спробувати пізніше
4. Перевірити rate limits

### 7.3 Типові помилки та рішення

**Помилка валідації Pydantic:**

```json
{
  "detail": [
    {
      "loc": ["body", "apy"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

**Рішення:** Перевірити правильність JSON тіла запиту.

**Помилка аутентифікації:**

```json
{
  "message": "Authentication failed",
  "details": "Invalid API credentials"
}
```

**Рішення:** Перевірити API ключі в `.env`.

**Timeout помилка:**

```json
{
  "message": "Request timeout",
  "details": "Connection to exchange timed out"
}
```

**Рішення:** Перевірити мережеве з'єднання та спробувати пізніше.

## Розділ 8: Практичні приклади

### 8.1 Базовий workflow

**Повний цикл роботи з API:**

```bash
#!/bin/bash
# complete_workflow.sh

echo "🚀 Початок повного циклу роботи з API"

# 1. Перевірка health
echo "1️⃣ Перевірка health..."
curl -s http://localhost:8000/health | jq '.status'

# 2. Тест підключення до бірж
echo "2️⃣ Тест підключення до Bybit..."
curl -s http://localhost:8000/api/v1/bybit/test | jq '.data.status'

# 3. Отримання BTC продуктів
echo "3️⃣ Отримання BTC продуктів..."
curl -s "http://localhost:8000/api/v1/yield/BTC" | jq '.count'

# 4. Синхронізація Bybit даних
echo "4️⃣ Синхронізація Bybit..."
curl -s -X POST "http://localhost:8000/api/v1/bybit/sync?symbol=BTC" | jq '.message'

# 5. Перевірка статистики
echo "5️⃣ Статистика БД..."
curl -s http://localhost:8000/api/v1/stats | jq '.data.total_products'

echo "✅ Цикл завершено"
```

### 8.2 Робота через браузер

**Swagger UI (інтерактивна документація):**

```
http://localhost:8000/docs
```

**ReDoc (альтернативна документація):**

```
http://localhost:8000/redoc
```

**Прямі GET запити в браузері:**

- Health check: `http://localhost:8000/health`
- Статистика: `http://localhost:8000/api/v1/stats`
- BTC продукти: `http://localhost:8000/api/v1/yield/BTC`
- Топ продуктів: `http://localhost:8000/api/v1/top?limit=10`

### 8.3 Автоматизація через скрипти

#### Python скрипт для моніторингу

```python
#!/usr/bin/env python3
"""
Моніторинг API endpoints
"""

import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def check_service_health():
    """Перевірка загального здоров'я сервісу."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def get_exchange_status():
    """Перевірка статусу бірж."""
    status = {}

    # Bybit (завжди повинен працювати)
    try:
        response = requests.get(f"{API_BASE}/api/v1/bybit/test", timeout=10)
        status["bybit"] = response.json().get("data", {}).get("status") == "success"
    except:
        status["bybit"] = False

    # Binance (може бути недоступний)
    try:
        response = requests.get(f"{API_BASE}/api/v1/binance/test", timeout=10)
        status["binance"] = response.json().get("data", {}).get("status") == "success"
    except:
        status["binance"] = False

    return status

def get_cache_stats():
    """Отримання статистики кешу."""
    try:
        response = requests.get(f"{API_BASE}/api/v1/cache/stats", timeout=5)
        if response.status_code == 200:
            return response.json().get("data", {})
    except:
        pass
    return {}

def main():
    """Головна функція моніторингу."""
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Моніторинг API")

    # Перевірка health
    healthy, health_data = check_service_health()
    print(f"🏥 Service Health: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

    if healthy:
        # Статус бірж
        exchange_status = get_exchange_status()
        print(f"🏦 Exchanges: Bybit {'✅' if exchange_status.get('bybit') else '❌'}, "
              f"Binance {'✅' if exchange_status.get('binance') else '❌'}")

        # Статистика кешу
        cache_stats = get_cache_stats()
        if cache_stats:
            hit_rate = cache_stats.get("hit_rate_percent", 0)
            print(f"💾 Cache Hit Rate: {hit_rate}%")

    print("-" * 50)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60)  # Перевірка кожну хвилину
```

#### Bash скрипт для швидкої перевірки

```bash
#!/bin/bash
# quick_api_check.sh

echo "🔍 Швидка перевірка API endpoints..."

# Функція для перевірки endpoint
check_endpoint() {
    local url=$1
    local name=$2

    if curl -s --max-time 10 "$url" > /dev/null; then
        echo "✅ $name: Available"
        return 0
    else
        echo "❌ $name: Unavailable"
        return 1
    fi
}

# Перевірка основних endpoints
check_endpoint "http://localhost:8000/health" "Health Check"
check_endpoint "http://localhost:8000/api/v1/stats" "Stats API"
check_endpoint "http://localhost:8000/api/v1/bybit/test" "Bybit API"
check_endpoint "http://localhost:8000/api/v1/yield/BTC" "Yield BTC API"

echo "🏁 Перевірка завершена"
```

### 8.4 Інтеграція з іншими системами

#### JavaScript/Node.js

```javascript
const axios = require("axios");

const API_BASE = "http://localhost:8000";

class EarnAggregatorAPI {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async getHealth() {
    try {
      const response = await axios.get(`${this.baseUrl}/health`);
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  }

  async getYieldProducts(symbol) {
    try {
      const response = await axios.get(
        `${this.baseUrl}/api/v1/yield/${symbol}`
      );
      return response.data;
    } catch (error) {
      throw new Error(
        `Failed to get yield products for ${symbol}: ${error.message}`
      );
    }
  }

  async getTopProducts(limit = 20) {
    try {
      const response = await axios.get(
        `${this.baseUrl}/api/v1/top?limit=${limit}`
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get top products: ${error.message}`);
    }
  }

  async syncBybitProducts(symbol = null) {
    try {
      const url = symbol
        ? `${this.baseUrl}/api/v1/bybit/sync?symbol=${symbol}`
        : `${this.baseUrl}/api/v1/bybit/sync`;

      const response = await axios.post(url);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to sync Bybit products: ${error.message}`);
    }
  }
}

// Використання
(async () => {
  const api = new EarnAggregatorAPI();

  try {
    // Перевірка health
    const health = await api.getHealth();
    console.log("Service status:", health.status);

    // Отримання BTC продуктів
    const btcProducts = await api.getYieldProducts("BTC");
    console.log(`Found ${btcProducts.count} BTC products`);

    // Синхронізація
    const syncResult = await api.syncBybitProducts();
    console.log("Sync completed:", syncResult.message);
  } catch (error) {
    console.error("API Error:", error.message);
  }
})();
```

## Розділ 8.5: CoinGecko Endpoints

### 8.5.1 Загальна інформація

CoinGecko API інтегровано для отримання даних про популярність криптовалют та trending cryptocurrencies. Це дозволяє сортувати продукти за популярністю та показувати trending монети.

### 8.5.2 Trending Cryptocurrencies

**Endpoint:** `GET /api/v1/coingecko/trending`

**Призначення:** Отримання списку trending cryptocurrencies з CoinGecko.

**Параметри:** Немає

**Відповідь:**

```json
{
  "success": true,
  "message": "Отримано 15 trending cryptocurrencies",
  "data": {
    "trending_coins": [
      {
        "coin_id": "bitcoin",
        "coin_id_num": 1,
        "symbol": "BTC",
        "name": "Bitcoin",
        "market_cap_rank": 1,
        "thumb": "https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png",
        "large": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
        "slug": "bitcoin",
        "price_btc": 1.0,
        "score": 8
      }
    ],
    "total_count": 15
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

**Приклад використання:**

```bash
curl "http://localhost:8000/api/v1/coingecko/trending"
```

### 8.5.3 Trending Score конкретної монети

**Endpoint:** `GET /api/v1/coingecko/trending/{symbol}`

**Призначення:** Отримання trending score конкретної монети.

**Параметри:**
- `symbol` (path): Символ монети (BTC, ETH, SOL, тощо)

**Відповідь:**

```json
{
  "success": true,
  "message": "Trending score для BTC",
  "data": {
    "symbol": "BTC",
    "trending_score": 8,
    "is_trending": true
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

**Приклад використання:**

```bash
curl "http://localhost:8000/api/v1/coingecko/trending/BTC"
```

### 8.5.4 Статистика Trending

**Endpoint:** `GET /api/v1/coingecko/trending-stats`

**Призначення:** Отримання статистики по trending cryptocurrencies.

**Параметри:** Немає

**Відповідь:**

```json
{
  "success": true,
  "message": "Статистика trending cryptocurrencies",
  "data": {
    "total_trending_coins": 15,
    "trending_coins": [
      {
        "coin_id": "bitcoin",
        "symbol": "BTC",
        "score": 8
      }
    ],
    "last_update": "2025-11-05T22:47:36.067234+00:00"
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

**Приклад використання:**

```bash
curl "http://localhost:8000/api/v1/coingecko/trending-stats"
```

### 8.5.5 Популярність монети

**Endpoint:** `GET /api/v1/coingecko/popularity/{symbol}`

**Призначення:** Отримання рейтингу популярності конкретної монети за market cap rank.

**Параметри:**
- `symbol` (path): Символ монети (BTC, ETH, SOL, тощо)

**Відповідь:**

```json
{
  "success": true,
  "message": "Рейтинг популярності для BTC",
  "data": {
    "symbol": "BTC",
    "market_cap_rank": 1,
    "is_popular": true
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

### 8.5.6 Статистика популярності

**Endpoint:** `GET /api/v1/coingecko/popularity-stats`

**Призначення:** Отримання статистики по всім даним популярності.

**Параметри:** Немає

**Відповідь:**

```json
{
  "success": true,
  "message": "Статистика популярності монет",
  "data": {
    "total_coins": 250,
    "last_update": "2025-11-05T00:00:00+00:00",
    "top_coins": [
      {
        "symbol": "BTC",
        "rank": 1
      }
    ]
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

### 8.5.7 Оновлення популярності

**Endpoint:** `POST /api/v1/coingecko/update-popularity`

**Призначення:** Оновлення рейтингу популярності монет з CoinGecko API.

**Параметри:** Немає

**Відповідь:**

```json
{
  "success": true,
  "message": "Рейтинг популярності успішно оновлено",
  "data": {
    "coins_processed": 250,
    "coins_updated": 250,
    "duration_seconds": 15.5,
    "message": "Оновлено рейтинг 250 монет з CoinGecko"
  },
  "timestamp": "2025-11-05T22:47:36.067234+00:00"
}
```

## Розділ 9: Додаткові матеріали

### 9.1 Glossary термінів

| Термін         | Пояснення                                                              |
| -------------- | ---------------------------------------------------------------------- |
| **API**        | Application Programming Interface - інтерфейс для взаємодії з сервісом |
| **Endpoint**   | Кінцева точка API - конкретна URL адреса для виконання операції        |
| **APY**        | Annual Percentage Yield - річна процентна дохідність                   |
| **CeFi**       | Centralized Finance - централізовані фінансові сервіси                 |
| **DeFi**       | Decentralized Finance - децентралізовані фінансові сервіси             |
| **Cache**      | Кеш - тимчасове зберігання даних для швидкого доступу                  |
| **Redis**      | Система кешування та зберігання даних в пам'яті                        |
| **Rate Limit** | Обмеження кількості запитів за одиницю часу                            |
| **Fallback**   | Резервний механізм при недоступності основного сервісу                 |

### 9.2 FAQ

**Q: Чому не працюють Binance endpoints?**
A: Перевірте налаштування API ключів в `.env` файлі. Binance API потребує валідних ключів.

**Q: Як очистити кеш?**
A: Використовуйте `POST /api/v1/cache/clear` endpoint або параметр `pattern` для часткового очищення.

**Q: Чи можна використовувати API без Redis?**
A: Так, система автоматично перемикається на fallback кеш при недоступності Redis.

**Q: Як часто оновлюються дані?**
A: Дані кешуються на 30 хвилин. Для свіжих даних використовуйте sync endpoints.

**Q: Які символи підтримуються?**
A: Підтримуються всі основні криптовалюти: BTC, ETH, USDT, BNB, SOL, тощо.

**Q: Як зменшити час відповіді?**
A: Використовуйте кешування та фільтри в запитах для отримання менших наборів даних.

### 9.3 Корисні посилання

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **GitHub репозиторій:** [Посилання на ваш репозиторій]
- **Binance API документація:** https://binance-docs.github.io/apidocs/
- **Bybit API документація:** https://bybit-exchange.github.io/docs/

---

**Останнє оновлення:** 2024-01-15
**Версія:** 1.0.0
