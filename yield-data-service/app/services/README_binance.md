# Binance API Інтеграція

## Огляд

Модуль `binance_service.py` забезпечує повну інтеграцію з Binance API для отримання, нормалізації та збереження даних про Earn продукти.

## Основні компоненти

### BinanceService

Головний сервіс для роботи з Binance API:

- Тестування підключення до API
- Обробка помилок (rate limits, timeouts)
- Нормалізація даних до єдиного формату
- Збереження в БД через CRUD операції
- Кешування результатів

### BinanceAPI

Базовий клієнт для роботи з Binance API endpoints:

- Simple Earn Flexible products
- Simple Earn Locked products
- Автоматична обробка підписів та автентифікації

## Конфігурація

Налаштування в `config.py` та `.env`:

```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
```

## API Endpoints

### Тестування підключення

```http
GET /api/v1/binance/test
```

Перевіряє підключення до Binance API та повертає статус.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "api_status": "active",
    "response_time_ms": 150.5,
    "products_found": 25
  },
  "message": "Тест підключення до Binance API виконано"
}
```

### Отримання продуктів

```http
GET /api/v1/binance/products?symbol=BTC
```

Отримує продукти Binance з кешуванням.

**Параметри:**

- `symbol` (опціонально) - фільтр по символу

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "binance_simple_flex_BTC_001",
      "symbol": "BTC",
      "name": "BTC Flexible Savings",
      "provider": "Binance",
      "apy": 5.2,
      "is_cefi": true,
      "min_amount": 0.001,
      "lock_period_days": 0,
      "risk_level": "Low"
    }
  ],
  "message": "Отримано 1 продуктів Binance",
  "cached": true
}
```

### Синхронізація з БД

```http
POST /api/v1/binance/sync?symbol=BTC
```

Синхронізує продукти з API в базу даних.

**Параметри:**

- `symbol` (опціонально) - синхронізувати тільки конкретний символ

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "products_count": 15,
    "sync_stats": {
      "created": 3,
      "updated": 12,
      "errors": 0
    }
  },
  "message": "Синхронізація Binance завершена: 3 створено, 12 оновлено"
}
```

### Health Check

```http
GET /api/v1/binance/health
```

Перевіряє стан Binance сервісу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "service": "binance",
    "configured": true,
    "connection": {
      "status": "success",
      "api_status": "active"
    },
    "cache_stats": {
      "hits": 45,
      "misses": 5,
      "hit_rate_percent": 90.0
    }
  }
}
```

## Використання в коді

### Базовий використання

```python
from app.services.binance_service import binance_service

# Тестування підключення
connection_result = await binance_service.test_connection()

# Отримання продуктів з кешуванням
products = await binance_service.get_products_with_cache("BTC")

# Синхронізація в БД
sync_result = await binance_service.sync_products_to_db("BTC")
```

### Отримання продуктів без кешування

```python
# Прямий виклик API (без кешування)
api_products = await binance_service.binance_api.get_earn_products()

# Нормалізація даних
normalized = await binance_service._normalize_products(api_products)
```

## Обробка помилок

### Rate Limits

Автоматично обробляються в `BaseExchange._make_request`:

- Автоматичний retry з експоненційною затримкою
- Читання заголовка `Retry-After`
- Максимум 3 спроби

### Timeouts

- Налаштований timeout: 30 секунд
- Автоматичний retry при timeout
- Логування всіх помилок

### Недоступність API

- Graceful degradation
- Повернення порожніх результатів замість падіння
- Детальне логування помилок

## Нормалізація даних

### Структура нормалізованого продукту

```python
{
    "id": "binance_simple_flex_BTC_001",
    "symbol": "BTC",
    "name": "BTC Flexible Savings",
    "provider": "Binance",
    "apy": 5.2,                    # Відсотки
    "is_cefi": True,               # Завжди True для Binance
    "min_amount": 0.001,           # Мінімальна сума
    "max_amount": None,            # Максимальна сума
    "lock_period_days": 0,         # 0 для Flexible, >0 для Locked
    "max_apy": 5.2,               # Максимальний APY
    "risk_level": "Low",           # Low/Medium/High
    "is_active": True,             # Активний продукт
    "website_url": "https://www.binance.com/en/earn",
    "description": "Bitcoin flexible savings",
    "raw_data": {...},            # Сирі дані з API
    "is_flexible": True           # Flexible чи Locked
}
```

### Визначення рівня ризику

- **Low**: Flexible продукти (lock_period_days = 0)
- **Medium**: Короткий lock (≤ 30 днів)
- **High**: Довгий lock (> 30 днів)

## Кешування

### Стратегія кешування

- **TTL**: 30 хвилин (1800 секунд)
- **Ключі**: `exchange:binance:symbol` або `exchange:binance:all`
- **Fallback**: Автоматичне перемикання на локальний кеш

### Використання кешу

```python
# Автоматичне кешування в get_products_with_cache()
products = await binance_service.get_products_with_cache("BTC")

# Перевірка статистики кешу
cache_stats = await cache_manager.get_cache_stats()
```

## Збереження в БД

### CRUD операції

- **Create**: Нові продукти зберігаються з ID від Binance
- **Update**: Існуючі продукти оновлюються
- **Exchange Data**: Raw дані зберігаються в `exchange_data` таблиці

### Структура збереження

```python
# Основна таблиця yield_products
await YieldProductCRUD.create_product(db, product_data)

# Raw дані в exchange_data
await ExchangeDataCRUD.create_exchange_data(
    db,
    product_id=product_id,
    exchange="binance",
    raw_data=raw_api_data
)
```

## Тестування

### Запуск тестів

```bash
pytest tests/test_binance_integration.py -v
```

### Тести покривають

- Ініціалізацію сервісу
- Тестування підключення
- Нормалізацію даних
- Обробку помилок
- Health check функціональність
- Кешування та fallback логіку

### Мок тести

Всі тести використовують моки для API викликів, що забезпечує:

- Швидке виконання тестів
- Незалежність від зовнішніх сервісів
- Стабільність результатів

## Моніторинг

### Логування

Всі операції логуються з рівнем INFO:

- `🧪 Тестування підключення до Binance API...`
- `🎯 Binance продукти отримано з кешу`
- `✅ Отримано 15 продуктів з Binance API`
- `❌ Помилка підключення до Binance API`

### Метрики

- Відсоток попадань в кеш
- Час відповіді API
- Кількість created/updated продуктів
- Статистика помилок

## Troubleshooting

### Поширені проблеми

1. **API ключі не налаштовані**

   ```
   "API ключі Binance не налаштовані"
   ```

   Рішення: Перевірити `.env` файл та змінні `BINANCE_API_KEY`, `BINANCE_API_SECRET`

2. **Rate limit exceeded**

   ```
   Rate limit exceeded
   ```

   Рішення: Автоматично обробляється, але можна збільшити затримки в коді

3. **Timeout errors**
   ```
   Request timeout
   ```
   Рішення: Перевірити мережевий зв'язок, API може бути тимчасово недоступний

### Налагодження

```python
# Детальне логування
import logging
logging.getLogger("yield_data_service").setLevel(logging.DEBUG)

# Перевірка health status
health = await binance_service.get_health_status()
print(health)
```
