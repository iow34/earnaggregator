# HTX Exchange Integration

## Огляд

Модуль для інтеграції з HTX (колишній Huobi) API для отримання даних про Earn/Savings продукти.

## Підтримувані продукти

- **Flexible Savings** - гнучкі заощадження без блокування коштів
- **Fixed Savings** - фіксовані заощадження з блокуванням на термін (7, 30, 60, 90+ днів)

## API Документація

Офіційна документація HTX API: https://www.htx.com/en-us/opend/newApiPages

Основний endpoint для Savings: `GET /v1/dw/savings/products/get`

## Специфіка HTX API

### Аутентифікація

HTX використовує специфічну аутентифікацію HmacSHA256:

1. **Обов'язкові параметри:**
   - `AccessKeyId` - API ключ
   - `SignatureMethod` - завжди "HmacSHA256"
   - `SignatureVersion` - завжди "2"
   - `Timestamp` - UTC timestamp в форматі ISO 8601

2. **Формат підпису:**
   ```
   method\nhost\npath\nsorted_params
   ```

3. **Генерація:**
   - Відсортувати параметри за ключами
   - URL-encode параметрів
   - Створити HMAC SHA256 з API secret
   - Base64 encode результату

### Rate Limits

- **100 запитів на 10 секунд** для підписаних endpoints
- Реалізовано exponential backoff при помилках 429

### Формат відповіді

**Успішна відповідь:**
```json
{
  "status": "ok",
  "data": [
    {
      "productId": "12345",
      "currency": "BTC",
      "apr": "0.02",
      "minPurchaseAmount": "0.001",
      "maxPurchaseAmount": "10",
      "status": "ONLINE",
      "type": "FLEXIBLE",
      "term": "0",
      "redeemType": "IMMEDIATE"
    }
  ]
}
```

**Помилка:**
```json
{
  "status": "error",
  "err-code": "invalid-signature",
  "err-msg": "Invalid signature"
}
```

## Використання

### Базове використання

```python
from app.services.exchanges.htx.service import HTXService

# Ініціалізація
service = HTXService()

# Отримання всіх продуктів
products = await service.get_products_with_cache()

# Отримання продуктів для конкретного активу
btc_products = await service.get_products_with_cache(symbol="BTC")

# Тест підключення
result = await service.test_connection()

# Перевірка здоров'я
health = await service.get_health_status()
```

### API клієнт

```python
from app.services.exchanges.htx.api import HTXAPI

# Ініціалізація
api = HTXAPI(api_key="your_key", api_secret="your_secret")

# Отримання Flexible продуктів
flexible = await api.get_flexible_savings_products()

# Отримання Fixed продуктів
fixed = await api.get_locked_savings_products()

# Отримання всіх продуктів
all_products = await api.get_earn_products()

# Фільтрація по активу
btc_products = await api.get_earn_products_by_asset("BTC")
```

## Нормалізація даних

Всі продукти HTX нормалізуються до стандартного формату:

```python
{
    "id": "htx_flex_12345",  # або "htx_fixed_12345_30" для Fixed
    "symbol": "BTC",
    "name": "BTC Flexible Savings",  # або "BTC Fixed Savings (30 days)"
    "provider": "HTX",
    "apy": 2.0,  # в відсотках
    "min_amount": 0.001,
    "max_amount": 10.0,  # або null
    "lock_period_days": 0,  # або 30, 60, 90 для Fixed
    "product_type": "Flexible",  # або "Fixed"
    "is_active": True,
    "risk_level": "Low",  # або "Medium"
    "description": "...",
    "website_url": "https://www.htx.com/earn",
    "raw_data": {...}  # оригінальні дані з API
}
```

## Обробка помилок

### Retry Logic

Реалізовано exponential backoff з 4 спробами:
- 1 → 2 → 4 → 8 секунд затримки

### Типи помилок

1. **Invalid Signature**
   - Повторна спроба з новим підписом
   - Логування в `/logs/htx_failed_signature.log`

2. **Invalid Timestamp**
   - Повторна спроба з оновленим часом
   - Затримка 1 секунда

3. **Rate Limit (429)**
   - Затримка 10 секунд
   - Повторна спроба

4. **Network Errors**
   - Exponential backoff
   - До 4 спроб

## Конфігурація

### Змінні середовища (.env)

```bash
HTX_API_KEY=your_api_key_here
HTX_API_SECRET=your_api_secret_here
```

### Docker Compose

```yaml
environment:
  - HTX_API_KEY=${HTX_API_KEY}
  - HTX_API_SECRET=${HTX_API_SECRET}
```

### Settings (config.py)

```python
htx_api_key: Optional[str] = Field(default=None, description="HTX API Key")
htx_api_secret: Optional[str] = Field(default=None, description="HTX API Secret")
```

## Тестування

### Unit тести

```bash
# Запуск всіх тестів HTX
pytest tests/services/test_htx_api.py tests/services/test_htx_service.py

# Окремо API
pytest tests/services/test_htx_api.py -v

# Окремо сервіс
pytest tests/services/test_htx_service.py -v
```

### Інтеграційні тести

```bash
# Тест основного endpoint
curl "http://localhost:8000/api/v1/exchanges?exchange=htx&limit=5"

# Тест популярних продуктів
curl "http://localhost:8000/api/v1/exchanges/htx/popular?limit=5"

# Тест health check
curl "http://localhost:8000/api/v1/health"
```

### Перевірка бази даних

```sql
-- Кількість HTX продуктів
SELECT COUNT(*) FROM yield_products WHERE provider = 'HTX';

-- Розподіл за типами
SELECT product_type, COUNT(*) 
FROM yield_products 
WHERE provider = 'HTX' 
GROUP BY product_type;

-- ТОП 10 за APY
SELECT symbol, apy, lock_period_days 
FROM yield_products 
WHERE provider = 'HTX' AND is_active = true 
ORDER BY apy DESC LIMIT 10;
```

## Моніторинг

### Prometheus метрики

- `EXTERNAL_API_CALLS{exchange="htx"}` - кількість викликів API
- `API_RESPONSE_TIME{exchange="htx"}` - час відповіді API
- `CACHE_HITS{exchange="htx"}` - попадання в кеш
- `CACHE_MISSES{exchange="htx"}` - промахи кешу

### Логування

Логи зберігаються в `yield-data-service/logs/`:
- `app.log` - загальні логи
- `errors.log` - тільки помилки
- `htx_failed_signature.log` - невдалі підписи (діагностика)

## Telegram Bot

Після інтеграції HTX автоматично підтримується в Telegram боті:

### Команди

- `/all_htx_products` - всі продукти HTX
- `/yield BTC` - пошук BTC продуктів (включаючи HTX)
- `/top` - топ продукти за APY (включаючи HTX)

### Функції

- Фільтри по біржі (вибір HTX)
- Сортування за популярністю
- Пагінація (30 продуктів на сторінку)
- Реферальне посилання HTX

## Troubleshooting

### Проблема: Invalid Signature

**Рішення:**
1. Перевірте формат підпису в логах `/logs/htx_failed_signature.log`
2. Переконайтеся що API key/secret коректні
3. Перевірте синхронізацію часу (NTP)

### Проблема: Rate Limit Exceeded

**Рішення:**
1. Збільшіть TTL кешу (за замовчуванням 30 хвилин)
2. Зменшіть частоту синхронізації
3. Використовуйте кеш замість прямих викликів API

### Проблема: No Products Returned

**Рішення:**
1. Перевірте що продукти мають статус "ONLINE"
2. Перевірте логи на помилки API
3. Виконайте manual sync: `curl -X POST http://localhost:8000/api/v1/htx/sync`

## Посилання

- [HTX Official Website](https://www.htx.com/)
- [HTX API Documentation](https://www.htx.com/en-us/opend/newApiPages)
- [HTX Earn Products](https://www.htx.com/earn)
- [Project Documentation](../../../docs/)

## Підтримка

Для питань та звітів про баги:
- GitHub Issues: [EarnAggregator/issues](https://github.com/your-repo/EarnAggregator/issues)
- Email: support@earnaggregator.com

