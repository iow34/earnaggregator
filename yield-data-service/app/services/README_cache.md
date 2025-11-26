# Модуль кешування (Cache)

## Огляд

Модуль `cache.py` забезпечує комплексне кешування для Data Service з підтримкою Redis та fallback логікою.

## Основні компоненти

### CacheManager

Головний клас для роботи з кешем:

- Автоматичне підключення до Redis
- Fallback до локального кешу при недоступності Redis
- Статистика використання кешу
- Health check функціональність

### CacheStats

Клас для збору статистики:

- Кількість HIT/MISS операцій
- Відсоток попадань в кеш
- Кількість операцій set/delete
- Облік помилок

## API функції

### Базові операції

```python
from app.services.cache import cache_manager

# Отримання даних
data = await cache_manager.get_cached_data("yield:BTC")

# Збереження даних
await cache_manager.set_cached_data("yield:BTC", data, expiration=3600)

# Видалення ключа
await cache_manager.delete_cached_data("yield:BTC")

# Очищення за патерном
await cache_manager.clear_cache("yield:*")
```

### Зручні функції

```python
from app.services.cache import get_cached_data, set_cached_data

# Коротші функції
data = await get_cached_data("key")
await set_cached_data("key", data)
```

### Стратегії ключів

```python
from app.services.cache import (
    get_yield_cache_key,
    get_top_cache_key,
    get_exchange_cache_key,
    get_recommendations_cache_key
)

# Yield дані по символу
yield_key = get_yield_cache_key("BTC")  # "yield:BTC"

# Топ продукти
top_key = get_top_cache_key(20)  # "top:20"

# Дані біржі
exchange_key = get_exchange_cache_key("binance", "BTC")  # "exchange:binance:BTC"

# Рекомендації користувача
rec_key = get_recommendations_cache_key("12345")  # "recommendations:12345"
```

## Конфігурація

Налаштування в `config.py`:

- `cache_expiration: int = 3600` - час життя кешу (секунди)
- `redis_host: str = "localhost"` - хост Redis
- `redis_port: int = 6379` - порт Redis
- `redis_password: Optional[str] = None` - пароль Redis

## Fallback логіка

При недоступності Redis автоматично перемикається на локальний кеш:

- Зберігає дані в пам'яті процесу
- Автоматично видаляє застарілі дані
- Обмежує розмір fallback кешу (1000 ключів)

## Моніторинг

### Статистика кешу

```python
stats = await cache_manager.get_cache_stats()
# {
#     "hits": 100,
#     "misses": 50,
#     "hit_rate_percent": 66.67,
#     "redis_connected": True,
#     "fallback_cache_size": 0
# }
```

### Health Check

```python
health = await cache_manager.health_check()
# {
#     "status": "healthy",
#     "redis_connected": True,
#     "response_time_ms": 2.5,
#     "fallback_active": False
# }
```

### API Endpoints

- `GET /api/v1/cache/stats` - статистика кешу
- `GET /api/v1/cache/health` - стан кешу
- `POST /api/v1/cache/clear?pattern=*` - очищення кешу

## Використання в endpoints

### Приклад інтеграції

```python
@router.get("/yield/{symbol}")
async def get_yield_by_symbol(symbol: str, db: AsyncSession = Depends(get_database_session)):
    cache_key = get_yield_cache_key(symbol.upper())

    # Перевіряємо кеш
    cached_data = await cache_manager.get_cached_data(cache_key)
    if cached_data is not None:
        return YieldResponse(
            success=True,
            data=cached_data["data"],
            cached=True,
            source="cache"
        )

    # Отримуємо з БД
    products = await YieldProductCRUD.get_products_by_symbol(db, symbol)

    # Зберігаємо в кеш
    cache_data = {
        "data": [product.model_dump() for product in products],
        "count": len(products)
    }
    await cache_manager.set_cached_data(cache_key, cache_data)

    return YieldResponse(data=products, cached=False, source="database")
```

## Стратегія кешування

### Ключі кешу

- `yield:{SYMBOL}` - дані по конкретній монеті
- `top:{LIMIT}` - топ N продуктів
- `exchange:{EXCHANGE}` - дані біржі
- `exchange:{EXCHANGE}:{SYMBOL}` - дані біржі по монеті
- `recommendations:{USER_ID}` - рекомендації користувача

### TTL стратегія

- За замовчуванням: 3600 секунд (1 година)
- Можна налаштувати для кожного ключа окремо
- Автоматичне оновлення через scheduler

### Інвалідація

- Автоматична по TTL
- Ручна через API endpoint
- При запиті до scheduler

## Обробка помилок

- При недоступності Redis - fallback до локального кешу
- При помилках серіалізації - логування та повернення помилки
- При помилках десеріалізації - видалення пошкодженого ключа

## Логування

Всі операції логуються:

- `🎯 Cache HIT: key` - вдале попадання в кеш
- `❌ Cache MISS: key` - промах в кеші
- `💾 Cache SET: key` - збереження в кеш
- `🗑️ Cache DELETE: key` - видалення з кешу

## Тестування

Запуск тестів кешу:

```bash
pytest tests/test_cache.py -v
```

Тести покривають:

- Базові операції кешу
- Fallback логіку
- Статистику та моніторинг
- Стратегії ключів
- Обробку помилок
