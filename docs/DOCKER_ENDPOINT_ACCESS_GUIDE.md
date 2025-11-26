# Доступ до Docker контейнера через API Endpoints

## ✅ Проблема вирішена!

### Що було не так:

1. **Неправильний DATABASE_URL**: Використовувався синхронний драйвер `postgresql://` замість async `postgresql+asyncpg://`
2. **Відсутня залежність**: Не було встановлено `greenlet>=3.0.0` для async SQLAlchemy
3. **Неправильна конфігурація Redis**: Код не читав `REDIS_URL` з Docker environment

### Як виправлено:

#### 1. Оновлено DATABASE_URL в `.env`

```bash
# Було:
DATABASE_URL=postgresql://yield_user:yield_secure_password_2024@postgres:5432/yield_db

# Стало:
DATABASE_URL=postgresql+asyncpg://yield_user:yield_secure_password_2024@postgres:5432/yield_db
```

#### 2. Додано greenlet до requirements.txt

```txt
greenlet>=3.0.0
```

#### 3. Оновлено конфігурацію Redis в `app/config.py`

```python
# Додано підтримку REDIS_URL
redis_url: Optional[str] = Field(default=None, description="Redis URL", alias="REDIS_URL")

def get_redis_url() -> str:
    # Якщо встановлений REDIS_URL, використовуємо його
    if settings.redis_url:
        return settings.redis_url

    # Інакше формуємо URL з окремих параметрів
    # ...
```

#### 4. Виправлено Pool конфігурацію в `app/db/database.py`

```python
# Замінено QueuePool на NullPool для async
poolclass=NullPool,  # Async engine вимагає NullPool або StaticPool
```

## 🚀 Поточний стан

### Docker контейнер працює правильно:

```bash
# Перевірка статусу
docker ps | grep earn-yield-api
# earn-yield-api  Up ... (healthy)  0.0.0.0:8000->8000/tcp

# Тест health endpoint
curl http://localhost:8000/health
```

**Результат:**

```json
{
  "status": "healthy",
  "service": "yield-data-service",
  "database": {
    "status": "healthy",
    "database_time": "2025-10-20T17:43:43.587778+00:00",
    "response_time_ms": 33.26,
    "pool_status": {
      "size": 0,
      "checked_in": 0,
      "checked_out": 0,
      "overflow": 0,
      "invalid": 0,
      "pool_type": "NullPool"
    }
  },
  "cache": {
    "status": "healthy",
    "redis_connected": true,
    "response_time_ms": 0.83,
    "fallback_active": false
  }
}
```

## 📋 Доступні Endpoints

### Основні endpoints:

- `GET http://localhost:8000/` - основний endpoint
- `GET http://localhost:8000/health` - стан сервісу
- `GET http://localhost:8000/docs` - Swagger документація

### API endpoints:

- `GET http://localhost:8000/api/v1/stats` - статистика БД
- `GET http://localhost:8000/api/v1/yield/{symbol}` - дані по монеті з валідацією
- `GET http://localhost:8000/api/v1/top` - топ пропозицій за APY
- `GET http://localhost:8000/api/v1/exchanges` - дані з конкретної біржі
- `GET http://localhost:8000/api/v1/exchanges/list` - список доступних бірж

### Кеш endpoints:

- `GET http://localhost:8000/api/v1/cache/stats` - статистика кешу
- `GET http://localhost:8000/api/v1/cache/health` - стан кешу
- `POST http://localhost:8000/api/v1/cache/clear` - очистити кеш

### Exchange endpoints:

- `GET http://localhost:8000/api/v1/binance/test` - тест Binance API
- `GET http://localhost:8000/api/v1/bybit/test` - тест Bybit API

## 🔧 Команди для роботи з Docker

### Запуск:

```bash
# Запустити всі сервіси
docker-compose up -d

# Запустити тільки API сервіс
docker-compose up -d yield-api
```

### Перезапуск після змін:

```bash
# Перебудова та запуск
docker-compose up --build -d yield-api

# Простий перезапуск
docker-compose restart yield-api
```

### Перевірка логів:

```bash
# Логи API сервісу
docker logs -f earn-yield-api

# Останні 20 рядків
docker logs --tail 20 earn-yield-api
```

### Тестування endpoints:

```bash
# Health check
curl http://localhost:8000/health

# З красивим форматуванням
curl -s http://localhost:8000/health | jq

# Основна сторінка
curl http://localhost:8000/

# Документація (в браузері)
open http://localhost:8000/docs
```

### Приклади використання нових API endpoints (РОЗДІЛ 3.1):

```bash
# GET /api/v1/yield/{symbol} - дані по монеті з валідацією
curl "http://localhost:8000/api/v1/yield/BTC?limit=10&min_apy=5.0"
curl "http://localhost:8000/api/v1/yield/ETH?provider=binance"

# GET /api/v1/top - топ пропозицій за APY
curl "http://localhost:8000/api/v1/top?limit=20"

# GET /api/v1/exchanges - дані з конкретної біржі
curl "http://localhost:8000/api/v1/exchanges?exchange=binance&symbol=BTC"
curl "http://localhost:8000/api/v1/exchanges?exchange=bybit&limit=50"

# GET /api/v1/exchanges/list - список доступних бірж
curl "http://localhost:8000/api/v1/exchanges/list"

# GET /api/v1/health - статус сервісу (покращено)
curl "http://localhost:8000/api/v1/health"
```

### Валідація параметрів (РОЗДІЛ 3.1):

#### GET /api/v1/yield/{symbol} - Покращена валідація:

**Параметри:**

- `symbol` (path): Символ криптовалюти, 2-10 символів, тільки літери та цифри
- `limit` (query): Кількість результатів, 1-100 (за замовчуванням: 50)
- `min_apy` (query): Мінімальний APY, 0-1000% (опціонально)
- `provider` (query): Фільтр по провайдеру (binance, bybit, nexo, etc.)

**Приклади валідації:**

```bash
# ✅ Валідні запити
curl "http://localhost:8000/api/v1/yield/BTC?limit=20&min_apy=5.0"
curl "http://localhost:8000/api/v1/yield/ETH?provider=binance"

# ❌ Невалідні запити (повернуть 400 Bad Request)
curl "http://localhost:8000/api/v1/yield/btc-invalid"  # Неправильні символи
curl "http://localhost:8000/api/v1/yield/A?limit=200"  # Ліміт > 100
curl "http://localhost:8000/api/v1/yield/BTC?min_apy=-5"  # Негативний APY
```

#### GET /api/v1/exchanges - Валідація бірж:

**Параметри:**

- `exchange` (query, required): Назва біржі (binance, bybit) - обов'язково
- `symbol` (query, optional): Символ для фільтрації
- `limit` (query): Кількість результатів, 1-200 (за замовчуванням: 50)

**Приклади:**

```bash
# ✅ Валідні запити
curl "http://localhost:8000/api/v1/exchanges?exchange=binance&symbol=BTC"
curl "http://localhost:8000/api/v1/exchanges?exchange=bybit&limit=100"

# ❌ Невалідні запити (повернуть 400 Bad Request)
curl "http://localhost:8000/api/v1/exchanges?exchange=coinbase"  # Непідтримувана біржа
curl "http://localhost:8000/api/v1/exchanges"  # Відсутній обов'язковий параметр exchange
```

## 🐛 Troubleshooting

### Якщо контейнер не запускається:

```bash
# Перевірити логи
docker logs earn-yield-api

# Перевірити статус
docker ps -a | grep earn-yield-api

# Перевірити змінні середовища
docker exec earn-yield-api env | grep -E "(REDIS|DATABASE)"
```

### Якщо endpoint не відповідає:

```bash
# Перевірити чи контейнер запущений
docker ps | grep earn-yield-api

# Перевірити чи порт доступний
netstat -an | grep 8000

# Тест всередині контейнера
docker exec earn-yield-api curl localhost:8000/health
```

## ✅ РОЗДІЛ 3.1: API endpoints та валідація - РЕАЛІЗОВАНО

### Що було додано/покращено:

#### 🔧 НОВІ API ENDPOINTS:

1. **`GET /api/v1/exchanges`** - дані з конкретної біржі (binance, bybit)

   - Параметри: `exchange` (required), `symbol` (optional), `limit` (1-200)
   - Валідація назви біржі
   - Кешування результатів

2. **`GET /api/v1/exchanges/list`** - список доступних бірж з їх статусом

   - Перевіряє здоров'я кожної біржі
   - Повертає опис та доступні endpoints

3. **`GET /api/v1/health`** - покращена перевірка статусу сервісу
   - Детальна інформація про БД, кеш та API бірж
   - Список доступних endpoints

#### 🛡️ ПОКРАЩЕНА ВАЛІДАЦІЯ:

1. **`GET /api/v1/yield/{symbol}`** - оновлено з додатковою валідацією:

   - `symbol`: 2-10 символів, тільки літери та цифри
   - `limit`: 1-100 результатів
   - `min_apy`: 0-1000% для фільтрації
   - `provider`: фільтр по провайдеру
   - Перевірка популярних символів
   - Покращена обробка помилок

2. **`GET /api/v1/exchanges`** - валідація параметрів:
   - Обов'язковий параметр `exchange` (binance/bybit)
   - Валідація лімітів та символів

#### 📋 ВСІ ДОСТУПНІ ENDPOINTS:

- `GET /api/v1/yield/{symbol}` - дані по монеті з валідацією
- `GET /api/v1/top` - топ пропозицій за APY
- `GET /api/v1/exchanges` - дані з конкретної біржі
- `GET /api/v1/exchanges/list` - список доступних бірж
- `GET /api/v1/health` - статус сервісу
- `GET /api/v1/stats` - статистика БД
- `GET /api/v1/cache/stats` - статистика кешу
- `POST /api/v1/cache/clear` - очищення кешу

## РОЗДІЛ 3.2: API endpoints з сервісом агрегації - РЕАЛІЗОВАНО

### Нові endpoints для сервісу агрегації

**GET `/api/v1/aggregation/stats`**

- Статистика сервісу агрегації
- Метрики cache, джерел, якості даних

```bash
curl "http://localhost:8000/api/v1/aggregation/stats"
```

**GET `/api/v1/aggregation/test`**

- Тестування роботи агрегації
- Параметри: `symbol`, `strategy`, `limit`

```bash
curl "http://localhost:8000/api/v1/aggregation/test?symbol=BTC&strategy=fast_cache_first&limit=10"
```

### Оновлені endpoints з агрегацією

**GET `/api/v1/yield/{symbol}`** (оновлено)

- Використовує сервіс агрегації з `FAST_CACHE_FIRST` стратегією
- Інтегрована валідація та graceful degradation

**GET `/api/v1/exchanges`** (оновлено)

- Використовує сервіс агрегації з `COMPREHENSIVE` стратегією
- Фільтрація по конкретній біржі

### Стратегії агрегації

1. **FAST_CACHE_FIRST**: швидкий доступ з пріоритетом кешу
2. **COMPREHENSIVE**: повна агрегація з усіх джерел
3. **FALLBACK_CHAIN**: ланцюжок fallback при помилках

### Приклади використання сервісу агрегації

```bash
# Тест швидкої агрегації
curl "http://localhost:8000/api/v1/aggregation/test?strategy=fast_cache_first&limit=5"

# Тест повної агрегації
curl "http://localhost:8000/api/v1/aggregation/test?strategy=comprehensive&symbol=ETH&limit=20"

# Тест fallback ланцюжка
curl "http://localhost:8000/api/v1/aggregation/test?strategy=fallback_chain&limit=10"

# Статистика агрегації
curl "http://localhost:8000/api/v1/aggregation/stats"
```

## ✅ Висновок РОЗДІЛУ 3.2

Docker контейнер `earn-yield-api` тепер включає **СЕРВІС АГРЕГАЦІЇ** з реалізованими вимогами:

1. ✅ **Сервіс агрегації** - об'єднання даних з бірж Binance та Bybit
2. ✅ **Логіка кешування** - коли використовувати кеш, коли API
3. ✅ **Обробка помилок** - graceful degradation при помилках
4. ✅ **Валідація даних** - перевірка якості даних
5. ✅ **Логування операцій** - для моніторингу та статистики

База даних, Redis та API бірж інтегровані в єдину систему через сервіс агрегації!
