# Bybit API Інтеграція

## Огляд

Модуль `bybit_service.py` забезпечує повну інтеграцію з Bybit API для отримання, нормалізації та збереження даних про Earn продукти.

## Основні компоненти

### BybitService

Головний сервіс для роботи з Bybit API:

- Тестування підключення до API
- Обробка помилок (rate limits, timeouts, специфіка Bybit)
- Нормалізація даних до єдиного формату
- Збереження в БД через CRUD операції
- Кешування результатів

### BybitAPI

Базовий клієнт для роботи з Bybit API v5:

- FlexibleSaving (Easy Earn) продукти
- OnChain (он-чейн стейкінг) продукти
- Публічні endpoints (не потребують автентифікації)

## Особливості Bybit API

### Публічний доступ

Bybit Earn API є публічним і не потребує API ключів для отримання списку продуктів:

```python
# Працює без API ключів
bybit_api = BybitAPI("", "")
products = await bybit_api.get_earn_products()
```

### Категорії продуктів

1. **FlexibleSaving** - Easy Earn (гнучкі заощадження)
2. **OnChain** - он-чейн стейкінг (ETH 2.0, SOL тощо)

## Конфігурація

Налаштування в `config.py` та `.env`:

```env
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here
```

**Примітка:** API ключі не обов'язкові для Earn продуктів, але зберігаються для сумісності.

## API Endpoints

### Тестування підключення

```http
GET /api/v1/bybit/test
```

Перевіряє підключення до Bybit API та повертає статус.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "success",
    "api_status": "active",
    "response_time_ms": 200.5,
    "products_found": 237,
    "public_api": true
  },
  "message": "Тест підключення до Bybit API виконано"
}
```

### Отримання продуктів

```http
GET /api/v1/bybit/products?symbol=BTC
```

Отримує продукти Bybit з кешуванням.

**Параметри:**

- `symbol` (опціонально) - фільтр по символу

**Відповідь:**

```json
{
  "success": true,
  "data": [
    {
      "id": "bybit_flexsaving_BTC_001",
      "symbol": "BTC",
      "name": "BTC Flexible Saving",
      "provider": "Bybit",
      "apy": 4.2,
      "is_cefi": true,
      "min_amount": 0.001,
      "lock_period_days": 0,
      "risk_level": "Low",
      "product_category": "FlexibleSaving",
      "product_type": "Flexible"
    }
  ],
  "message": "Отримано 1 продуктів Bybit",
  "cached": true
}
```

### Синхронізація з БД

```http
POST /api/v1/bybit/sync?symbol=ETH
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
  "message": "Синхронізація Bybit завершена: 3 створено, 12 оновлено"
}
```

### Health Check

```http
GET /api/v1/bybit/health
```

Перевіряє стан Bybit сервісу.

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "service": "bybit",
    "configured": true,
    "connection": {
      "status": "success",
      "api_status": "active",
      "public_api": true
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
from app.services.bybit_service import bybit_service

# Тестування підключення
connection_result = await bybit_service.test_connection()

# Отримання продуктів з кешуванням
products = await bybit_service.get_products_with_cache("BTC")

# Синхронізація в БД
sync_result = await bybit_service.sync_products_to_db("BTC")
```

### Робота з категоріями

```python
from app.services.exchanges.bybit_api import BybitAPI

bybit_api = BybitAPI("", "")

# Тільки FlexibleSaving продукти
flexible = await bybit_api.get_flexible_saving_products("BTC")

# Тільки OnChain продукти
onchain = await bybit_api.get_onchain_products("ETH")

# Всі продукти
all_products = await bybit_api.get_earn_products()
```

## Обробка помилок

### Специфіка Bybit

Bybit API має свої особливості:

- Публічні endpoints не обмежені API ключами
- Може повертати помилки при невалідних параметрах категорії
- Rate limits застосовуються на IP основі

### Автоматична обробка

Всі помилки обробляються в `BaseExchange._make_request()`:

- Retry з експоненційною затримкою
- Обробка HTTP 429 (rate limit)
- Timeout handling
- Graceful degradation

## Нормалізація даних

### Структура нормалізованого продукту

```python
{
    "id": "bybit_flexsaving_BTC_001",
    "symbol": "BTC",
    "name": "BTC Flexible Saving",
    "provider": "Bybit",
    "apy": 4.2,                    # Відсотки
    "is_cefi": True,               # True для FlexibleSaving, False для OnChain
    "min_amount": 0.001,           # Мінімальна сума
    "max_amount": 100.0,           # Максимальна сума
    "lock_period_days": 0,         # 0 для Flexible, >0 для Fixed
    "max_apy": 4.2,               # Максимальний APY
    "risk_level": "Low",           # Low/Medium/High
    "is_active": True,             # Активний продукт
    "website_url": "https://www.bybit.com/earn",
    "description": "Bybit Easy Earn - Flexible",
    "product_category": "FlexibleSaving",  # FlexibleSaving/OnChain
    "product_type": "Flexible",    # Flexible/Fixed
    "raw_data": {...}             # Сирі дані з API
}
```

### Визначення CeFi/DeFi

- **CeFi (True)**: FlexibleSaving продукти (керується Bybit)
- **DeFi (False)**: OnChain продукти (он-чейн стейкінг)

### Визначення рівня ризику

**FlexibleSaving:**

- **Low**: Flexible продукти (lock_period_days = 0)
- **Medium**: Короткий lock (≤ 30 днів)
- **High**: Довгий lock (> 30 днів)

**OnChain:**

- **Medium**: Короткий lock (≤ 7 днів)
- **High**: Довгий lock (> 7 днів)

## Кешування

### Стратегія кешування

- **TTL**: 30 хвилин (1800 секунд)
- **Ключі**: `exchange:bybit:symbol` або `exchange:bybit:all`
- **Fallback**: Автоматичне перемикання на локальний кеш

### Використання кешу

```python
# Автоматичне кешування в get_products_with_cache()
products = await bybit_service.get_products_with_cache("BTC")

# Перевірка статистики кешу
cache_stats = await cache_manager.get_cache_stats()
```

## Збереження в БД

### CRUD операції

- **Create**: Нові продукти зберігаються з ID від Bybit
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
    exchange="bybit",
    raw_data=raw_api_data,
    api_endpoint="/v5/earn/product"
)
```

## Тестування

### Запуск тестів

```bash
pytest tests/test_bybit_integration.py -v
```

### Тести покривають

- Ініціалізацію сервісу
- Тестування підключення до публічного API
- Нормалізацію даних для різних категорій
- Обробку помилок та специфіки Bybit
- Health check функціональність
- Кешування та fallback логіку

### Специфічні тести Bybit

- Робота з публічним API без ключів
- Обробка FlexibleSaving та OnChain продуктів
- Правильне визначення CeFi/DeFi статусу
- Категоріальна обробка даних

## Моніторинг

### Логування

Всі операції логуються з рівнем INFO:

- `🧪 Тестування підключення до Bybit API...`
- `🎯 Bybit продукти отримано з кешу`
- `✅ Отримано 237 продуктів з Bybit API`
- `❌ Помилка підключення до Bybit API`

### Метрики

- Відсоток попадань в кеш
- Час відповіді API
- Кількість created/updated продуктів
- Статистика помилок
- Підтвердження публічного API

## Порівняння з Binance

| Аспект             | Bybit                   | Binance             |
| ------------------ | ----------------------- | ------------------- |
| **API доступ**     | Публічний (без ключів)  | Потребує API ключі  |
| **Категорії**      | FlexibleSaving, OnChain | Flexible, Locked    |
| **Автентифікація** | Не потрібна для Earn    | Потрібна для всіх   |
| **Rate limits**    | На IP основі            | На API ключ основі  |
| **Продукти**       | ~237 FlexibleSaving     | Залежить від ключів |

## Troubleshooting

### Поширені проблеми

1. **API недоступний**

   ```
   "API Error"
   ```

   Рішення: Перевірити мережевий зв'язок, Bybit API може бути тимчасово недоступний

2. **Немає продуктів**

   ```
   "Продукти не знайдено"
   ```

   Рішення: Перевірити параметри фільтрації, можливо для символу немає активних продуктів

3. **Невалідні категорії**
   ```
   "Invalid category parameter"
   ```
   Рішення: Використовувати тільки "FlexibleSaving" та "OnChain"

### Налагодження

```python
# Детальне логування
import logging
logging.getLogger("yield_data_service").setLevel(logging.DEBUG)

# Перевірка health status
health = await bybit_service.get_health_status()
print(health)

# Тест реального API
products = await bybit_service.bybit_api.get_flexible_saving_products()
print(f"Знайдено {len(products)} продуктів")
```

### Корисні команди

```bash
# Тест підключення
curl "http://localhost:8000/api/v1/bybit/test"

# Отримання продуктів BTC
curl "http://localhost:8000/api/v1/bybit/products?symbol=BTC"

# Синхронізація в БД
curl -X POST "http://localhost:8000/api/v1/bybit/sync"
```
