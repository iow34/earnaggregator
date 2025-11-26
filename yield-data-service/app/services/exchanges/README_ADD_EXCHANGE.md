# Додавання нової біржі в систему EarnAggregator

Цей документ описує процес додавання нової криптобіржі в систему для отримання Earn продуктів.

## 📁 Структура директорій

Для кожної біржі створюється окрема директорія:

```
app/services/exchanges/{exchange_name}/
├── __init__.py          # Імпорти модулів біржі
├── api.py              # API клієнт для роботи з біржею
├── service.py          # Бізнес-логіка сервісу
└── models.py           # Специфічні моделі (опціонально)
```

## 🚀 Швидкий старт

### 1. Створіть директорію біржі

```bash
cd app/services/exchanges
mkdir your_exchange_name
cd your_exchange_name
touch __init__.py api.py service.py models.py
```

### 2. Скопіюйте приклад

Створіть нову директорію для вашої біржі та скопіюйте структуру з існуючої біржі:

```bash
# Приклад: створення нової біржі на основі binance
cp -r binance/* your_exchange_name/
```

### 3. Налаштуйте API клієнт (`api.py`)

```python
class YourExchangeAPI(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://api.your-exchange.com"
        )

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        # Реалізуйте отримання продуктів з API вашої біржі
        pass

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        # Реалізуйте фільтрацію по активу
        pass
```

### 4. Налаштуйте сервіс (`service.py`)

```python
class YourExchangeService(BaseExchangeService):
    def __init__(self):
        super().__init__("your_exchange_name", YourExchangeAPI)

    async def test_connection(self) -> Dict[str, Any]:
        # Реалізуйте тест підключення
        pass

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Реалізуйте нормалізацію даних
        pass
```

### 5. Налаштуйте імпорти (`__init__.py`)

```python
from .api import YourExchangeAPI
from .service import YourExchangeService

__all__ = ["YourExchangeAPI", "YourExchangeService"]
```

### 6. Додайте API ключі в конфігурацію

В `.env` файлі додайте:

```env
YOUR_EXCHANGE_API_KEY=your_api_key_here
YOUR_EXCHANGE_API_SECRET=your_api_secret_here
```

В `config.py` додайте:

```python
your_exchange_api_key: str = os.getenv("YOUR_EXCHANGE_API_KEY", "")
your_exchange_api_secret: str = os.getenv("YOUR_EXCHANGE_API_SECRET", "")
```

## 🔧 Детальна інструкція

### API клієнт (api.py)

Наслідуйте структуру інших бірж:

1. **Успадкуйте BaseExchange**
2. **Реалізуйте get_headers()** - заголовки для API
3. **Реалізуйте get_earn_products()** - отримання всіх продуктів
4. **Використовуйте \_make_request()** для HTTP запитів
5. **Обробляйте помилки** через try/except

### Сервіс (service.py)

Наслідуйте структуру інших сервісів:

1. **Успадкуйте BaseExchangeService**
2. **Перевизначте test_connection()** для тестування API
3. **Перевизначте \_normalize_products()** для нормалізації даних
4. **Використовуйте базові методи** для кешування та збереження

### Моделі (models.py)

Створюйте моделі для специфічних структур даних вашої біржі:

```python
class YourExchangeProduct(BaseModel):
    product_id: str
    asset: str
    apr: float
    status: str
```

## 🔄 Автоматичне завантаження

Після створення всіх файлів біржа автоматично:

1. **Завантажується** реєстром при старті додатку
2. **Доступна** через `exchange_registry.get_exchange_service("your_exchange_name")`
3. **Інтегрується** в агрегацію та API endpoints
4. **Додається** в scheduler для автоматичного оновлення

## 🧪 Тестування нової біржі

### 1. Тест підключення

```bash
curl "http://localhost:8000/api/v1/your_exchange/test"
```

### 2. Отримання продуктів

```bash
curl "http://localhost:8000/api/v1/exchanges?exchange=your_exchange"
```

### 3. Синхронізація в БД

```bash
curl -X POST "http://localhost:8000/api/v1/your_exchange/sync"
```

## 📊 API Endpoints

Після додавання біржі автоматично стають доступні:

- `GET /api/v1/your_exchange/test` - тест підключення
- `GET /api/v1/your_exchange/products` - отримання продуктів
- `POST /api/v1/your_exchange/sync` - синхронізація з БД
- `GET /api/v1/your_exchange/health` - стан сервісу
- `GET /api/v1/exchanges?exchange=your_exchange` - через загальний endpoint

## 🎯 Найкращі практики

### 1. Обробка помилок

```python
try:
    data = await self._make_request("GET", endpoint)
    return data
except Exception as e:
    logger.error(f"[YourExchange] Помилка: {e}")
    return []
```

### 2. Логування

```python
logger.info(f"[YourExchange] Отримано {len(products)} продуктів")
logger.error(f"[YourExchange] Помилка API: {e}")
```

### 3. Нормалізація даних

Переконайтеся що продукти мають всі обов'язкові поля:

```python
{
    "id": "unique_id",
    "symbol": "BTC",
    "name": "BTC Flexible",
    "provider": "YourExchange",
    "apy": 5.2,
    "is_cefi": True,
    "min_amount": 0.001,
    "lock_period_days": 0,
    "is_active": True,
    "website_url": "https://your-exchange.com",
    "description": "Flexible savings",
    "raw_data": {...}
}
```

### 4. Кешування

Використовуйте стандартні ключі кешу:

```python
cache_key = f"exchange:your_exchange:{symbol or 'all'}"
```

## 🔍 Приклади реалізацій

Подивіться на існуючі біржі:

- **Binance**: `binance/` - приклад з підписаними запитами
- **Bybit**: `bybit/` - приклад з публічним API
- **Шаблон**: Використовуйте структуру існуючих бірж (наприклад, `binance/` або `bybit/`) як приклад

## 🚨 Troubleshooting

### Біржа не завантажується

1. Перевірте що всі файли створені
2. Перевірте імпорти в `__init__.py`
3. Перевірте логи при старті додатку

### API помилки

1. Перевірте API ключі в `.env`
2. Перевірте базовий URL в `api.py`
3. Перевірте формат запитів у документації біржі

### Продукти не нормалізуються

1. Перевірте обов'язкові поля в `_normalize_products()`
2. Перевірте типи даних (str, float, int)
3. Перевірте логи помилок нормалізації

## 🎉 Після додавання

Ваша біржа автоматично:

- Інтегрується в агрегацію даних
- З'являється в списку доступних бірж
- Оновлюється автоматично scheduler'ом
- Доступна через Telegram бот
- Моніториться системою

**Привіт! Нова біржа додана в систему! 🎊**
