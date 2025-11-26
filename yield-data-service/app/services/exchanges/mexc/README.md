# MEXC Exchange Integration (API Mode)

## Огляд

MEXC має публічний API для отримання Savings/Earn продуктів через ендпоінт `/api/financialactivity/financial/products/list`. Інтеграція працює в **API mode**:

- Дані отримуються автоматично через публічний API MEXC
- Продукти нормалізуються та зберігаються в PostgreSQL з автоматичною синхронізацією
- Підтримується кешування в Redis
- MEXCService працює з API та кешуванням
- Фільтрація по мінімальному APR для кожного типу продукту

## Архітектура

```
┌─────────────────────────────────────────────────┐
│  MEXC Public API                                │
│  GET /api/financialactivity/financial/products/list
│  https://www.mexc.com                           │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  MEXCAPI.get_earn_products()                    │
│  (запити до API, парсинг JSON)                  │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  MEXCService._normalize_products()              │
│  (фільтрація активних, вибір min APR)           │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  PostgreSQL (yield_products table)              │
│  provider = 'MEXC', автоматична синхронізація   │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Redis Cache (TTL: 30 хвилин)                   │
│  Кешовані продукти для швидкого доступу         │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  MEXCService.get_products_with_cache()          │
│  (читає з кешу або БД)                          │
└─────────────────────────────────────────────────┘
```

## API Інтеграція

### MEXC Public API

MEXC надає публічний API без аутентифікації для отримання Savings/Earn продуктів:

**Базовий URL:** `https://www.mexc.com`

**Ендпоінт:** `GET /api/financialactivity/financial/products/list`

**Параметри:**

- `matchMemberAssets` (boolean, optional): Фільтр за активами користувача (default: false)
- `page` (integer, optional): Номер сторінки (default: 1)
- `pageSize` (integer, optional): Розмір сторінки (default: 100, max: 100)

### Нормалізація даних

Згідно з технічним завданням, дані нормалізуються наступним чином:

1. **Фільтрація активних продуктів:**

   - `financialState = 2` (активний)
   - `soldOut = false` (не розпродано)

2. **Вибір мінімального APR:**

   - Для кожного `currency` і типу продукту (`FLEXIBLE`/`FIXED`) обирається продукт з найменшим APR
   - Якщо є `tiered_subsidy_apr`, обирається мінімальний APR з tiers

3. **Стандартизація полів:**
   - `id`: `mexc_{тип}_{financialId}`
   - `symbol`: currency з API
   - `product_type`: "Flexible" або "Locked"
   - `apy`: нормалізований APR
   - `min_amount`: 0.001 (default)
   - `max_amount`: null
   - `lock_period_days`: 0 для Flexible, `fixedInvestPeriodCount` для Fixed

### Автоматична синхронізація

Дані автоматично синхронізуються через scheduler щогодини:

```bash
# Ручний запуск синхронізації
curl -X POST http://localhost:8000/api/v1/sync/mexc
```

### Перевірка роботи

```bash
# Перевірити статус API та БД
curl http://localhost:8000/api/v1/mexc/test

# Отримати продукти
curl http://localhost:8000/api/v1/mexc/products?limit=10

# Перевірити кеш
curl http://localhost:8000/api/v1/mexc/products?use_cache=true
```

## API Endpoints

### `GET /api/v1/mexc/products`

Отримання MEXC продуктів з кешу/БД.

**Query Parameters:**

- `symbol` (optional): Фільтр по символу (BTC, ETH, etc.)
- `limit` (optional, default=100): Ліміт продуктів
- `use_cache` (optional, default=true): Використовувати кеш

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "mexc_flexible_123",
      "symbol": "USDT",
      "name": "USDT Flexible Savings",
      "provider": "MEXC",
      "apy": 5.5,
      "product_type": "Flexible",
      "is_active": true,
      "risk_level": "Low"
    }
  ],
  "count": 25,
  "cached": true
}
```

### `GET /api/v1/mexc/test`

Тест підключення до MEXC API та БД.

**Response:**

```json
{
  "status": "success",
  "message": "MEXC API працює. Продуктів в API: 15, в БД: 25",
  "manual_mode": false,
  "api_status": "success",
  "api_products": 15,
  "db_products": 25,
  "public_api": true
}
```

### `POST /api/v1/sync/mexc`

Ручна синхронізація продуктів з MEXC API.

**Query Parameters:**

- `symbol` (optional): Синхронізувати тільки певний символ

**Response:**

```json
{
  "status": "success",
  "message": "Синхронізація завершена",
  "created": 3,
  "updated": 12,
  "deleted": 0,
  "total": 25
}
```

## Інтеграція з Telegram ботом

MEXC автоматично підтримується в Telegram боті:

- **Команда**: `/all_mexc_products` - всі продукти MEXC
- **Головне меню**: Огляд MEXC з 4 пріоритетними монетами
- **Фільтри**: По типу (Flexible/Locked), APY, продукту
- **Сортування**: За популярністю, APY (↑/↓)

## Автоматична синхронізація

### Scheduler налаштування

Продукти автоматично оновлюються через scheduler:

- **Інтервал**: Щогодини
- **TTL кешу**: 30 хвилин
- **Retry політика**: 3 спроби з exponential backoff
- **Логування**: Всі помилки та зміни в логи

### Моніторинг синхронізації

```bash
# Перевірити статус останньої синхронізації
curl http://localhost:8000/api/v1/health/mexc

# Перевірити логи синхронізації
docker-compose logs yield-api | grep "MEXC.*sync"
```

## Troubleshooting

### API недоступний

```json
{
  "status": "warning",
  "message": "MEXC працює через БД (API недоступний). Продуктів в БД: 25"
}
```

**Рішення**:

1. Перевірити інтернет підключення
2. Перевірити чи не змінилась структура API MEXC
3. Дані будуть братись з останньої успішної синхронізації

### Помилка нормалізації

```
[MEXCService] Помилка нормалізації продукту 123: invalid APR value
```

**Рішення**:

- Перевірити логи для деталей помилки
- Можливо змінилася структура відповіді MEXC API
- Зв'язатися з розробниками для оновлення парсера

### Продукти не оновлюються

```bash
curl http://localhost:8000/api/v1/mexc/test
# {"api_products": 0, "db_products": 25}
```

**Рішення**:

1. Перевірити scheduler логи
2. Запустити ручну синхронізацію: `POST /api/v1/sync/mexc`
3. Перевірити API доступність

## Приклади

### Приклад 1: Отримання продуктів

```bash
# Отримати всі MEXC продукти
curl "http://localhost:8000/api/v1/mexc/products?limit=5"

# Отримати продукти для конкретного активу
curl "http://localhost:8000/api/v1/mexc/products?symbol=USDT"

# Отримати продукти без кешу
curl "http://localhost:8000/api/v1/mexc/products?use_cache=false"
```

### Приклад 2: Тестування API

```bash
# Перевірити статус API та БД
curl http://localhost:8000/api/v1/mexc/test

# Response:
# {
#   "status": "success",
#   "message": "MEXC API працює. Продуктів в API: 15, в БД: 25",
#   "api_status": "success",
#   "api_products": 15,
#   "db_products": 25
# }
```

### Приклад 3: Ручна синхронізація

```bash
# Синхронізувати всі продукти
curl -X POST http://localhost:8000/api/v1/sync/mexc

# Синхронізувати тільки USDT
curl -X POST "http://localhost:8000/api/v1/sync/mexc?symbol=USDT"

# Response:
# {
#   "status": "success",
#   "message": "Синхронізація завершена",
#   "created": 2,
#   "updated": 8,
#   "deleted": 1,
#   "total": 25
# }
```
