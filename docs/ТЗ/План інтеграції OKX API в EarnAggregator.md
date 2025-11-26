# План інтеграції OKX API в EarnAggregator

## Етап 0: Підготовка та створення базових модулів

### 0.1 Створення структури директорій

- Створити `/Users/user777/Documents/EarnAggregator/yield-data-service/app/services/exchanges/okx/`
- Створити файли: `__init__.py`, `api.py`, `service.py`, `models.py`

### 0.2 Оновлення конфігурації

- Додати в `/Users/user777/Documents/EarnAggregator/.env`:
  - `OKX_API_KEY`
  - `OKX_API_SECRET`
  - `OKX_API_PASSPHRASE` (специфічний для OKX)
  - `OKX_BASE_URL` (за замовчуванням: `https://www.okx.com`)
- Оновити `/Users/user777/Documents/EarnAggregator/yield-data-service/app/config.py`:
  - Додати поля `okx_api_key`, `okx_api_secret`, `okx_api_passphrase`, `okx_base_url` в клас Settings

### 0.3 Реалізація Rate Limiter (Token Bucket)

- Створити `/Users/user777/Documents/EarnAggregator/yield-data-service/app/utils/rate_limiter.py`
- Реалізувати Token Bucket алгоритм для 3 req/s
- Інтегрувати в OKX API клієнт

---

## Етап 1: Реалізація API клієнта (api.py)

### 1.1 Базова структура класу OKXAPI

- Успадкування від `BaseExchange`
- Ініціалізація з 3 параметрами: `api_key`, `api_secret`, `api_passphrase`
- Базовий URL: `https://www.okx.com`

### 1.2 Аутентифікація OKX

- Реалізувати метод `_generate_signature(timestamp: str, method: str, request_path: str, body: str) -> str`
  - Формат: `timestamp + method + requestPath + body`
  - Підпис: `base64(HMAC-SHA256(message, secret_key))`
- Реалізувати метод `get_headers() -> Dict[str, str]`
  - `OK-ACCESS-KEY`: API ключ
  - `OK-ACCESS-SIGN`: підпис
  - `OK-ACCESS-TIMESTAMP`: ISO 8601 timestamp (формат: `2025-10-29T14:23:45.123Z`)
  - `OK-ACCESS-PASSPHRASE`: passphrase

### 1.3 On-chain earn продукти

- Реалізувати `async def get_onchain_earn_products(product_id: Optional[str] = None, protocol_type: Optional[str] = None, ccy: Optional[str] = None) -> List[Dict[str, Any]]`
- Endpoint: `GET /api/v5/finance/staking-defi/offers`
- Парсинг відповіді:
  - `code == "0"` - успіх
  - `data` - масив продуктів
  - Поля: `ccy`, `productId`, `protocol`, `protocolType`, `term`, `apy`, `earlyRedeem`, `investData`, `state`
- Нормалізація в формат EarnAggregator:
  - `id`: `okx_onchain_{productId}`
  - `symbol`: `ccy`
  - `name`: `{ccy} On-chain Earn ({protocol})`
  - `provider`: `"OKX"`
  - `apy`: перетворення з `"0.0395"` -> `3.95`
  - `lock_period_days`: `0` (flexible) або з `term`
  - `product_type`: `"OnChain"`
  - `is_active`: `state == "purchasable"`

### 1.4 Simple Earn Flexible продукти

- Реалізувати `async def get_simple_earn_flexible_products(ccy: Optional[str] = None) -> List[Dict[str, Any]]`
- Endpoint: `GET /api/v5/finance/simple-earn/products` (перевірити в офіційній документації)
- Парсинг відповіді:
  - Поля: `ccy`, `rate`, `minAmt`, `maxAmt`, `autoRenew`, `status`
- Нормалізація:
  - `id`: `okx_simple_flex_{ccy}`
  - `product_type`: `"SimpleFlexible"`
  - `lock_period_days`: `0`

### 1.5 Агрегація всіх продуктів

- Реалізувати `async def get_earn_products() -> List[Dict[str, Any]]`
  - Викликати обидва методи (on-chain, simple earn)
  - Об'єднати результати
  - Нормалізувати через `normalize_earn_product()`
- Реалізувати `async def get_earn_products_by_asset(asset: str) -> List[Dict[str, Any]]`
  - Фільтрація за символом активу

---

## Етап 2: Реалізація сервісу (service.py)

### 2.1 Базова структура класу OKXService

- Успадкування від `BaseExchangeService`
- Ініціалізація: `__init__(self): super().__init__(exchange_name="okx", api_class=OKXAPI)`
- Додати перевірку наявності `passphrase` в конструкторі

### 2.2 Основні методи сервісу

- `async def initialize(self)`
  - Ініціалізація API клієнта з 3 параметрами
  - Логування стану конфігурації
- `async def get_products_from_api(symbol: Optional[str] = None) -> List[Dict[str, Any]]`
  - Виклик `api_client.get_earn_products()` або `get_earn_products_by_asset(symbol)`
- `async def get_products_with_cache(symbol: Optional[str] = None) -> List[Dict[str, Any]]`
  - Перевірка Redis кешу (TTL: 60 хв)
  - Fallback до API при відсутності кешу
  - Збереження в кеш після отримання з API

### 2.3 Додаткові методи

- `async def test_connection() -> Dict[str, Any]`
  - Тест виклику `get_onchain_earn_products(ccy="BTC")` з size=1
  - Метрики: `response_time_ms`, `products_found`
- `async def get_health_status() -> Dict[str, Any]`
  - Статус конфігурації, підключення, кешу
- `async def sync_products_to_db(symbol: Optional[str] = None) -> Dict[str, Any]`
  - Успадковується від `BaseExchangeService`

### 2.4 Prometheus метрики

- Інтеграція метрик:
  - `okx_api_calls_total`
  - `okx_api_errors_total`
  - `okx_api_response_time_seconds`
- Додати в методи `get_products_with_cache` та `test_connection`

---

## Етап 3: Реалізація моделей (models.py)

### 3.1 Pydantic моделі для On-chain earn

```python
class OKXOnChainProduct(BaseModel):
    product_id: str
    ccy: str  # symbol
    protocol: str
    protocol_type: str
    term: str  # lock days або порожній для flexible
    apy: str  # "0.0395" формат
    early_redeem: bool
    state: str  # "purchasable" / "sold_out" / "suspend"
```

### 3.2 Pydantic моделі для Simple Earn

```python
class OKXSimpleEarnProduct(BaseModel):
    ccy: str
    rate: str  # APY у string форматі
    min_amt: str
    max_amt: str
    auto_renew: bool
    status: str  # "available"
```

### 3.3 Unified модель

```python
class OKXUnifiedProduct(BaseModel):
    id: str
    symbol: str
    name: str
    provider: str = "OKX"
    apy: float
    min_amount: Optional[float]
    max_amount: Optional[float]
    lock_period_days: int
    product_type: str  # "OnChain" / "SimpleFlexible"
    is_active: bool
    risk_level: str = "Low"
    raw_data: Dict[str, Any]
```

---

## Етап 4: Реєстрація в системі

### 4.1 Налаштування імпортів в **init**.py

```python
from .api import OKXAPI
from .service import OKXService
from .models import OKXOnChainProduct, OKXSimpleEarnProduct, OKXUnifiedProduct

__all__ = ["OKXAPI", "OKXService", "OKXOnChainProduct", "OKXSimpleEarnProduct", "OKXUnifiedProduct"]
```

### 4.2 Перевірка автоматичної реєстрації

- ExchangeRegistry автоматично знайде модуль `okx` в `app/services/exchanges/`
- Перевірити що `OKXService` має всі необхідні методи для динамічного завантаження

---

## Етап 5: Додавання API endpoints

### 5.1 Додати маршрути в routes.py

- `GET /api/v1/okx/test` - тест підключення
- `GET /api/v1/exchanges/okx/products` - отримання продуктів (з пагінацією)
- `GET /api/v1/exchanges/okx/popular` - популярні продукти
- `POST /api/v1/okx/sync` - синхронізація в БД

### 5.2 Інтеграція в aggregation_service.py

- Додати `DataSource.API_OKX = "api_okx"`
- Додати в `fallback_chain`
- Додати обробку в методі `_get_exchange_data`

---

## Етап 6: Інтеграція з Telegram ботом

### 6.1 Оновлення API клієнта бота

- В `yield-telegram-bot/bot/services/api_client.py`:
  - `async def get_okx_products(limit: Optional[int] = None) -> Dict[str, Any]`
  - `async def get_okx_popular(limit: Optional[int] = None) -> Dict[str, Any]`

### 6.2 Додавання команд/хендлерів

- Команда `/okx` - відображення OKX продуктів
- Inline кнопки для фільтрації за типом (OnChain / SimpleFlexible)
- Реферальні посилання на OKX (якщо є)

---

## Етап 7: Тестування та валідація

### 7.1 Unit тести

- Створити `yield-data-service/tests/services/test_okx_api.py`:
  - Тест `_generate_signature`
  - Тест парсингу On-chain продуктів (mock відповідь)
  - Тест парсингу Simple Earn продуктів
  - Тест нормалізації

### 7.2 Integration тести

- Створити `yield-data-service/tests/integration/test_okx_integration.py`:
  - Реальний виклик API (sandbox якщо доступний)
  - Тест кешування
  - Тест синхронізації в БД

### 7.3 E2E тестування

- Тест REST endpoints:
  - `curl http://localhost:8000/api/v1/okx/test`
  - `curl http://localhost:8000/api/v1/exchanges/okx/products?limit=5`
  - `curl -X POST http://localhost:8000/api/v1/okx/sync`
- Перевірка БД:
  - Запит кількості продуктів: `SELECT COUNT(*) FROM yield_products WHERE provider = 'OKX';`
  - Перевірка типів: `SELECT product_type, COUNT(*) FROM yield_products WHERE provider = 'OKX' GROUP BY product_type;`

### 7.4 Моніторинг та логи

- Перевірити Prometheus метрики для OKX
- Перевірити логи в `yield-data-service/logs/app.log`
- Налаштувати Grafana dashboard для OKX метрик