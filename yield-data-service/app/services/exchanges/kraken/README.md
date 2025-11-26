# Kraken Earn API Integration

## Огляд

Інтеграція з Kraken Earn API для отримання даних про Flexible та Bonded staking продукти.

## Офіційна документація

- API docs: https://docs.kraken.com/api/docs/guides/spot-rest-earn
- Endpoint: `POST /0/private/Earn/Strategies`

## Типи продуктів

### 1. Flexible Staking
- **lock_type**: `"flexible"`
- **duration**: `0` днів
- **Особливості**: можна вилучити кошти в будь-який час
- **APY**: зазвичай нижчий ніж у Bonded

### 2. Bonded Staking
- **lock_type**: `"bonded"`
- **duration**: фіксований термін (наприклад, 28, 90, 180 днів)
- **Особливості**: кошти заблоковані на термін
- **APY**: зазвичай вищий ніж у Flexible

## Аутентифікація

### HMAC-SHA512 підпис

Kraken використовує складну схему підпису:

```python
# 1. Підготовка
nonce = str(int(time.time() * 1000))  # millisecond timestamp
data = {'nonce': nonce, ...params}
urlpath = "/0/private/Earn/Strategies"

# 2. SHA256(nonce + POST data)
postdata = urlencode(data)
encoded = (nonce + postdata).encode('utf-8')
sha256_hash = hashlib.sha256(encoded).digest()

# 3. HMAC-SHA512
message = urlpath.encode('utf-8') + sha256_hash
secret_decoded = base64.b64decode(api_secret)
signature = hmac.new(secret_decoded, message, hashlib.sha512)

# 4. Base64 encode
api_sign = base64.b64encode(signature.digest()).decode('utf-8')
```

### Заголовки запиту

```python
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "API-Key": api_key,
    "API-Sign": signature
}
```

**Критично**: Kraken використовує `application/x-www-form-urlencoded`, не JSON!

## Rate Limits

- **Базовий tier**: 2 calls/sec
- **Вищі tiers**: до 20 calls/sec
- **Points system**: Earn/Strategies коштує 2 points

### Рекомендації
- Використовувати затримку 600ms між запитами (~1.6 calls/sec)
- Моніторити помилки 429 (rate limit exceeded)
- Реалізувати exponential backoff при перевищенні

## Pagination

Kraken використовує cursor-based pagination:

```python
params = {
    "lock_type": ["flexible"],
    "limit": 100,
    "cursor": next_cursor  # з попередньої відповіді
}
```

### Структура відповіді

```json
{
    "error": [],
    "result": {
        "items": [...],
        "next_cursor": "eyJvZmZzZXQiOjEwMH0="  // або null
    }
}
```

**Важливо**: Ігнорування cursor призведе до неповного списку (>100 стратегій).

## Формат даних

### Приклад Flexible стратегії

```json
{
    "id": "ESFU3RVHYXLFTQDT",
    "asset": "ETH",
    "lock_type": {
        "type": "flexible"
    },
    "apr_estimate": {
        "low": "0.0400",  // як string, не число!
        "high": "0.0450"
    },
    "allocation_fee": "0",
    "user_cap": "unlimited",  // або число як string
    "can_allocate": true,
    "allocation_restriction_info": []
}
```

### Приклад Bonded стратегії

```json
{
    "id": "ESB9TU2NYQ65H2VT",
    "asset": "DOT",
    "lock_type": {
        "type": "bonded",
        "bonding_period": 28  // днів
    },
    "apr_estimate": {
        "low": "0.0800"
    },
    "can_allocate": true
}
```

## Нормалізація даних

### Парсинг числових полів

```python
# APY: string "0.04" -> float 4.0%
rate_str = item.get("apr_estimate", {}).get("low", "0")
apy = float(rate_str) * 100

# Min/Max amount
min_amount = float(item.get("allocation_fee", "0"))
max_amount_str = item.get("user_cap")
max_amount = None if max_amount_str == "unlimited" else float(max_amount_str)
```

### Визначення Risk Level

- **Low**: Stablecoins (USDT, USDC), BTC, ETH
- **Medium**: Популярні altcoins
- **High**: Assets з slashing ризиком (DOT, ATOM, KSM)

### Фільтрація

Тільки стратегії з `can_allocate == true` вважаються активними.

## Поширені помилки

### 1. "EAPI:Invalid nonce"
**Причина**: Nonce не зростаючий або дублюється  
**Рішення**: Використовувати millisecond timestamp + уникати race conditions

### 2. "EAPI:Invalid signature"
**Причина**: Неправильне кодування POST data або path  
**Рішення**: Строго дотримуватися алгоритму підпису

### 3. "EGeneral:Permission denied"
**Причина**: API key без Earn permissions  
**Рішення**: Створити новий key з правами "Earn allocate/deallocate"

### 4. Rate limit exceeded (429)
**Причина**: Перевищення 2 calls/sec  
**Рішення**: Збільшити затримку між запитами

### 5. Неповний список продуктів
**Причина**: Ігнорування pagination cursor  
**Рішення**: Ітеративно запитувати з cursor до порожнього

## Особливості API

### Variable APY

Деякі стратегії мають `rate_type == "variable"`:
- Rate є estimate, може змінюватися
- Додати в description: "Variable APY, current estimate"

### Allocation Restrictions

Поле `allocation_restriction_info` вказує на обмеження:
- Geo restrictions (регіональні)
- Tier restrictions (рівень акаунта)
- Такі стратегії слід ігнорувати

### Issuing Asset

Деякі стратегії мають `issuing_asset` (rewards в іншій валюті):
- Наприклад, stake ETH -> отримай stETH
- Враховувати при відображенні користувачу

## Приклади використання

### Отримання Flexible продуктів

```python
from app.services.exchanges.kraken.service import KrakenService

service = KrakenService()
await service.initialize()

# Всі Flexible продукти
products = await service.api_client.get_flexible_savings_products()

# Для конкретного asset
eth_products = await service.api_client.get_flexible_savings_products(asset="ETH")
```

### Синхронізація в БД

```python
result = await service.sync_products_to_db()
# {"created": 50, "updated": 20, "errors": 0}
```

### Кешування

```python
# Перший запит - з API
products = await service.get_products_with_cache()

# Повторний запит протягом 30 хв - з кешу
products = await service.get_products_with_cache()
```

## Моніторинг

### Prometheus метрики

```python
from app.utils.metrics import EXTERNAL_API_CALLS, API_RESPONSE_TIME

EXTERNAL_API_CALLS.labels(exchange="kraken").inc()
API_RESPONSE_TIME.labels(exchange="kraken").observe(response_time)
```

### Логування

Всі критичні операції логуються:
- Початок/кінець запитів
- Кількість отриманих продуктів
- Помилки з `exc_info=True`

## Тестування

### Unit тести

```bash
pytest tests/services/test_kraken_api.py -v
```

### Інтеграційні тести

```bash
# Health check
curl http://localhost:8000/api/v1/kraken/test

# Продукти
curl "http://localhost:8000/api/v1/exchanges?exchange=kraken&limit=5"

# Синхронізація
curl -X POST "http://localhost:8000/api/v1/kraken/sync"
```

### Перевірка БД

```sql
SELECT COUNT(*) FROM yield_products WHERE provider = 'Kraken';
SELECT product_type, COUNT(*) FROM yield_products 
WHERE provider = 'Kraken' GROUP BY product_type;
```

## Troubleshooting

### Перевірка конфігурації

```python
from app.config import settings

print(f"Kraken API Key: {settings.kraken_api_key[:10]}...")
print(f"Configured: {bool(settings.kraken_api_key and settings.kraken_api_secret)}")
```

### Перевірка підпису

Якщо помилки з підписом - тестувати в Postman з точною імплементацією з документації.

### Rate limits

Якщо 429 помилки - збільшити затримку в `_rate_limit_delay()`.

## Ресурси

- [Kraken API Docs](https://docs.kraken.com/api/docs/guides/spot-rest-earn)
- [Stack Overflow: Kraken API](https://stackoverflow.com/questions/tagged/kraken-api)
- [GitHub: CCXT Kraken Issues](https://github.com/ccxt/ccxt/issues?q=kraken+earn)
- [Reddit: r/KrakenSupport](https://www.reddit.com/r/KrakenSupport/)

## Changelog

- **2024-10-31**: Початкова інтеграція Kraken Earn API
  - Flexible та Bonded staking
  - HMAC-SHA512 аутентифікація
  - Cursor pagination
  - Redis кешування 30 хв

