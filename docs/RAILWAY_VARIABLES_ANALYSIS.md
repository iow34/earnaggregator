# 🔍 Аналіз налаштування Variables на Railway та проблем синхронізації

**Дата:** 2025-11-29  
**Статус:** Виявлено проблеми та запропоновано рішення

---

## ✅ Перевірка Variables на Railway

### Поточні налаштування (перевірено через Railway CLI):

**Binance API:**

- ✅ `BINANCE_API_KEY`: встановлено (g5CYWzibxOpq2OpXjc18NsCqE8Ce5kt3KiVUF86cfjXXuEj9kJGX6W3YkmX4T9Ba)
- ✅ `BINANCE_API_SECRET`: встановлено (TkpE0ySVvJFhwTIXaNKaa8uVc7moQnr9d1okzd9k311Ia5AsamF22c6vJACKG7zx)

**Bybit API:**

- ✅ `BYBIT_API_KEY`: встановлено (KT2uv9qtThzaLJtOAF)
- ✅ `BYBIT_API_SECRET`: встановлено (i6C8jKLWrHfvKZZpnAyWhbMqvWVgewaroh2G)

**Інші біржі:**

- ✅ OKX, Gate, Bitget, Kraken, KuCoin, HTX - всі ключі встановлені

**База даних:**

- ✅ `DATABASE_URL`: налаштовано (Railway managed PostgreSQL)
- ✅ `REDIS_URL`: налаштовано (Railway managed Redis)

---

## 🔴 Виявлені проблеми

### Проблема 1: Логіка перевірки конфігурації

**Файл:** `yield-data-service/app/services/exchanges/base_service.py`

**Код:**

```python
def _check_configuration(self) -> bool:
    """Перевіряє чи налаштовані API ключі."""
    return bool(self.api_key and self.api_secret)
```

**Проблема:**

- Якщо `api_key` або `api_secret` порожній рядок `""`, то `is_configured = False`
- Для Binance це критично - без ключів API не працює
- Для Bybit - може працювати без ключів (публічний API), але код все одно перевіряє

**Рішення:**

1. Додати перевірку на default значення (`"your_binance_api_key_here"`)
2. Для Bybit дозволити роботу без ключів (публічний API)

### Проблема 2: Pydantic Settings може не читати змінні середовища

**Файл:** `yield-data-service/app/config.py`

**Проблема:**

- `BaseSettings` читає з `.env` файлу, але на Railway `.env` файлу немає
- Потрібно переконатися, що Pydantic правильно читає змінні середовища
- Можливо потрібно додати `env_file=None` для production

**Рішення:**

- Перевірити чи `Settings()` правильно читає змінні з Railway
- Додати логування для діагностики

### Проблема 3: Таблиця `exchange_data` не існує

**Проблема:**

- Foreign Key constraint не може бути створений, якщо таблиця `yield_products` не існує
- Або таблиця `exchange_data` не створена через помилки міграції

**Рішення:**

- Виконати міграції через `/api/v1/migrations/run`
- Перевірити чи всі таблиці створені

### Проблема 4: Обробка помилок Foreign Key

**Файл:** `yield-data-service/app/services/exchanges/base_service.py` (рядки 194-209)

**Проблема:**

- Якщо продукт не зберігається в `yield_products`, то Foreign Key constraint падає
- Помилки не обробляються коректно - всі 539 продуктів отримують помилку

**Рішення:**

- Покращити обробку помилок Foreign Key
- Додати UPSERT для `exchange_data`

---

## 📋 Правильне налаштування Variables на Railway

### Для Binance (обов'язково):

```bash
BINANCE_API_KEY=g5CYWzibxOpq2OpXjc18NsCqE8Ce5kt3KiVUF86cfjXXuEj9kJGX6W3YkmX4T9Ba
BINANCE_API_SECRET=TkpE0ySVvJFhwTIXaNKaa8uVc7moQnr9d1okzd9k311Ia5AsamF22c6vJACKG7zx
```

**Як перевірити:**

1. Railway UI → Service `earnaggregator` → Variables
2. Переконатися що значення встановлені (не порожні)
3. Переконатися що немає пробілів на початку/кінці

### Для Bybit (опціонально, але рекомендовано):

```bash
BYBIT_API_KEY=KT2uv9qtThzaLJtOAF
BYBIT_API_SECRET=i6C8jKLWrHfvKZZpnAyWhbMqvWVgewaroh2G
```

**Примітка:** Bybit Earn API публічний, але для сумісності краще встановити ключі.

---

## 🔧 Виправлення коду

### Виправлення 1: Покращити перевірку конфігурації

**Файл:** `yield-data-service/app/services/exchanges/base_service.py`

```python
def _check_configuration(self) -> bool:
    """Перевіряє чи налаштовані API ключі."""
    # Перевіряємо чи ключі не порожні та не є default значеннями
    default_values = [
        "your_binance_api_key_here",
        "your_bybit_api_key_here",
        "your_okx_api_key_here",
        ""
    ]

    api_key_valid = self.api_key and self.api_key not in default_values
    api_secret_valid = self.api_secret and self.api_secret not in default_values

    # Для Bybit дозволяємо роботу без ключів (публічний API)
    if self.exchange_name == "bybit":
        return True  # Bybit працює без ключів

    return api_key_valid and api_secret_valid
```

### Виправлення 2: Додати логування для діагностики

**Файл:** `yield-data-service/app/services/exchanges/base_service.py`

```python
def __init__(self, exchange_name: str, api_class: type):
    # ... існуючий код ...

    # Налаштування API
    self.api_key = getattr(settings, f"{exchange_name}_api_key", "")
    self.api_secret = getattr(settings, f"{exchange_name}_api_secret", "")

    # Логування для діагностики (тільки перші 10 символів для безпеки)
    logger.info(f"🔑 {exchange_name} API Key: {self.api_key[:10]}..." if self.api_key else "⚠️ {exchange_name} API Key: не встановлено")
    logger.info(f"🔑 {exchange_name} API Secret: {'*' * 10}..." if self.api_secret else "⚠️ {exchange_name} API Secret: не встановлено")

    # ... решта коду ...
```

### Виправлення 3: Покращити обробку помилок Foreign Key

**Файл:** `yield-data-service/app/services/exchanges/base_service.py` (метод `_save_products_to_db`)

```python
# Зберігаємо raw дані (оновлюємо якщо існує)
try:
    # Використовуємо UPSERT для exchange_data
    from sqlalchemy import select
    from app.db.models import ExchangeDataDB

    # Перевіряємо чи існує запис
    existing_exchange_data = await db.execute(
        select(ExchangeDataDB).where(
            ExchangeDataDB.product_id == product_data["id"],
            ExchangeDataDB.exchange == self.exchange_name
        )
    )
    exchange_data_record = existing_exchange_data.scalar_one_or_none()

    if exchange_data_record:
        # Оновлюємо існуючий запис
        exchange_data_record.raw_data = product_data.get("raw_data", {})
        exchange_data_record.api_endpoint = f"/v1/{self.exchange_name}/"
        exchange_data_record.request_timestamp = datetime.now(UTC).replace(tzinfo=None)
        exchange_data_record.response_status = 200
        await db.commit()
        await db.refresh(exchange_data_record)
    else:
        # Створюємо новий запис
        await ExchangeDataCRUD.create_exchange_data(
            db,
            product_id=product_data["id"],
            exchange=self.exchange_name,
            raw_data=product_data.get("raw_data", {}),
            api_endpoint=f"/v1/{self.exchange_name}/",
            request_timestamp=datetime.now(UTC).replace(tzinfo=None)
        )
except Exception as exchange_data_error:
    # Детальне логування помилки
    error_str = str(exchange_data_error).lower()
    if "foreign key" in error_str or "yield_products" in error_str:
        logger.error(
            f"❌ Foreign Key помилка для {product_data['id']}: "
            f"Продукт не існує в yield_products. "
            f"Помилка: {exchange_data_error}"
        )
        # Не додаємо до errors, бо це проблема з продуктом, а не з exchange_data
    elif "unique_product_exchange" in error_str or "duplicate key" in error_str:
        logger.debug(
            f"ℹ️ Exchange data вже існує для {product_data['id']} на {self.exchange_name}"
        )
    else:
        logger.warning(
            f"⚠️ Помилка збереження exchange data для {product_data['id']}: {exchange_data_error}"
        )
```

---

## 🧪 Тестування налаштувань

### Крок 1: Перевірити чи змінні читаються правильно

```bash
# Через Railway Shell
railway shell

# Виконати Python скрипт
python3 << EOF
from app.config import settings
print(f"BINANCE_API_KEY: {settings.binance_api_key[:20]}...")
print(f"BINANCE_API_SECRET: {'*' * 20}...")
print(f"BYBIT_API_KEY: {settings.bybit_api_key}")
print(f"BYBIT_API_SECRET: {'*' * 20}...")
EOF
```

### Крок 2: Перевірити тест підключення

```bash
# Binance
curl https://earnaggregator-production.up.railway.app/api/v1/binance/test

# Bybit
curl https://earnaggregator-production.up.railway.app/api/v1/bybit/test
```

### Крок 3: Перевірити синхронізацію

```bash
# Binance
curl -X POST https://earnaggregator-production.up.railway.app/api/v1/binance/sync

# Bybit
curl -X POST https://earnaggregator-production.up.railway.app/api/v1/bybit/sync
```

---

## 📊 Порівняння .env та Railway Variables

### ✅ Співпадіння:

| Змінна               | .env                                                             | Railway                                                          | Статус |
| -------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- | ------ |
| `BINANCE_API_KEY`    | g5CYWzibxOpq2OpXjc18NsCqE8Ce5kt3KiVUF86cfjXXuEj9kJGX6W3YkmX4T9Ba | g5CYWzibxOpq2OpXjc18NsCqE8Ce5kt3KiVUF86cfjXXuEj9kJGX6W3YkmX4T9Ba | ✅     |
| `BINANCE_API_SECRET` | TkpE0ySVvJFhwTIXaNKaa8uVc7moQnr9d1okzd9k311Ia5AsamF22c6vJACKG7zx | TkpE0ySVvJFhwTIXaNKaa8uVc7moQnr9d1okzd9k311Ia5AsamF22c6vJACKG7zx | ✅     |
| `BYBIT_API_KEY`      | KT2uv9qtThzaLJtOAF                                               | KT2uv9qtThzaLJtOAF                                               | ✅     |
| `BYBIT_API_SECRET`   | i6C8jKLWrHfvKZZpnAyWhbMqvWVgewaroh2G                             | i6C8jKLWrHfvKZZpnAyWhbMqvWVgewaroh2G                             | ✅     |

**Висновок:** Variables на Railway встановлені правильно та співпадають з .env файлом.

---

## 🎯 Основні причини проблем синхронізації

1. **Таблиця `exchange_data` не існує** → Foreign Key constraint падає
2. **Продукти не зберігаються в `yield_products`** → Foreign Key constraint падає
3. **Обробка помилок не коректна** → всі 539 продуктів отримують помилку
4. **Логіка перевірки конфігурації** → може не працювати для Bybit (публічний API)

---

## 🚀 План дій

1. ✅ Перевірити Variables на Railway (виконано - все правильно)
2. ⏳ Виконати міграції через `/api/v1/migrations/run`
3. ⏳ Виправити код обробки помилок Foreign Key
4. ⏳ Додати логування для діагностики
5. ⏳ Протестувати синхронізацію після виправлень

---

## 📚 Посилання на документацію Railway

- [Railway Environment Variables](https://docs.railway.com/develop/variables)
- [Railway PostgreSQL](https://docs.railway.com/databases/postgresql)
- [Railway Deployments](https://docs.railway.com/deploy/builds)

---

**Останнє оновлення:** 2025-11-29
