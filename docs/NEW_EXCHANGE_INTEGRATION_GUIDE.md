# 🔧 Повна інструкція по інтеграції API нової біржі в EarnAggregator

## 📋 Зміст

1. [Загальна інформація про проект](#загальна-інформація-про-проект)
2. [Архітектура системи](#архітектура-системи)
3. [Що таке Earn продукти](#що-таке-earn-продукти)
4. [Правила отримання даних з API біржі](#правила-отримання-даних-з-api-біржі)
5. [Структура модулів нової біржі](#структура-модулів-нової-біржі)
6. [Покрокова інструкція інтеграції](#покрокова-інструкція-інтеграції)
7. [Інтеграція з Telegram ботом](#інтеграція-з-telegram-ботом)
8. [Валідація та тестування](#валідація-та-тестування)
9. [Моніторинг та підтримка](#моніторинг-та-підтримка)

---

## 🏗️ Загальна інформація про проект

### EarnAggregator - це:

**Мікросервісна платформа** для агрегації даних про пасивний дохід (Yield/Earn продукти) з криптовалютних бірж.

### Основні компоненти:

1. **yield-data-service** - Backend API (FastAPI, PostgreSQL, Redis)
2. **yield-telegram-bot** - Telegram бот для користувачів (Aiogram 3.x)
3. **Моніторинг** - Prometheus + Grafana
4. **Docker** - Контейнеризація всіх сервісів

### Мета проекту:

- Збір даних про Yield Products з бірж (Binance, Bybit, OKX, та інші)
- Агрегація та нормалізація даних з різних джерел
- Надання REST API для доступу до даних
- Telegram бот з багаторівневою навігацією та фільтрами
- Монетизація через реферальні програми

---

## 🏛️ Архітектура системи

### Основні принципи архітектури:

#### 1. **Модульність**

- Кожна біржа має власну ізольовану директорію
- Незалежні компоненти з чіткими інтерфейсами
- Легка заміна та розширення функціональності

#### 2. **Шари архітектури**

```
┌─────────────────┐
│   Telegram Bot  │ ← Клієнтський інтерфейс з багаторівневою навігацією
│   (Aiogram 3.x) │
├─────────────────┤
│  REST API       │ ← FastAPI маршрути
├─────────────────┤
│  Aggregation    │ ← Сервіс агрегації
├─────────────────┤
│  Exchange       │ ← Сервіси бірж (Binance, Bybit, OKX, ...)
│  Services       │
├─────────────────┤
│   Cache Layer   │ ← Redis кешування
├─────────────────┤
│   Database      │ ← PostgreSQL зберігання
├─────────────────┤
│ External APIs   │ ← API бірж (Binance, Bybit, OKX, ...)
└─────────────────┘
```

#### 3. **Архітектура Telegram бота**

##### Сторінки бота та їх функціональність:

**📄 Сторінка 1: Головне меню**

- ТОП 10 продуктів за APY з усіх бірж
- Швидкий огляд по біржам (BTC, ETH, SOL, USDT)
- Навігаційні кнопки для різних типів продуктів

**📄 Сторінка 2: Продукти конкретної біржі**

- Всі продукти однієї біржі з пагінацією (30 продуктів на сторінку)
- Фільтри: тип продукту (Flexible/Fixed), APY діапазон
- Сортування: за популярністю, APY (зростання/спадання)

**📄 Сторінка 3: Flexible продукти з усіх бірж**

- Таблиця всіх Flexible продуктів (Продукт | Біржа | APY)
- Фільтри: конкретний продукт, конкретна біржа
- Сортування: за APY (зростання/спадання), популярністю
- Пагінація (30 продуктів на сторінку)

**📄 Сторінка 5: Продукт по всіх біржах**

- Порівняльна таблиця одного продукту на всіх біржах
- Колонки: Біржа, Тип, APY, Період блокування

**📄 Сторінка 6: Продукт на конкретній біржі**

- Детальна інформація про продукт на одній біржі

##### Навігація та стан:

- **FSM (Finite State Machine)** для керування станом користувача
- **FilterStateManager** для збереження фільтрів
- **Paginator** для пагінації великих списків
- **Inline keyboards** для інтерактивних кнопок

#### 3. **Структура директорій**

```
yield-data-service/
├── app/
│   ├── api/routes.py           # FastAPI маршрути
│   ├── services/
│   │   ├── exchanges/          # 🔴 ОСНОВНА ДИРЕКТОРІЯ ДЛЯ БІРЖ
│   │   │   ├── registry.py     # Реєстр бірж
│   │   │   ├── base_exchange.py # Базовий клас API клієнтів
│   │   │   ├── base_service.py  # Базовий клас сервісів
│   │   │   ├── binance/        # Біржа Binance
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py      # API клієнт
│   │   │   │   ├── service.py  # Бізнес логіка
│   │   │   │   └── models.py   # Pydantic моделі
│   │   │   └── bybit/          # Біржа Bybit (аналогічно)
│   │   └── aggregation_service.py # Сервіс агрегації
│   ├── db/                     # База даних
│   ├── models/                 # Pydantic моделі
│   └── config.py               # Конфігурація
```

#### 4. **Потік даних**

```
1. Користувач → Telegram бот
2. Telegram бот → yield-data-service API
3. API → Aggregation Service
4. Aggregation Service → Exchange Registry
5. Exchange Registry → Конкретний Exchange Service
6. Exchange Service → API клієнт біржі
7. API клієнт → External API біржі
8. Отримання даних ← Нормалізація ← Кешування ← Збереження в БД
9. Повернення результату в зворотньому порядку
```

---

## 💰 Що таке Earn продукти

### Типи Earn продуктів:

#### 1. **Flexible (Гнучкі) продукти**

- **Особливості**: Можна вилучити кошти в будь-який час без штрафів
- **APY**: Зазвичай нижчий ніж у Fixed продуктів
- **Термін**: Немає фіксованого терміну
- **Ризик**: Мінімальний (як заощадження)
- **Приклади**: Binance Flexible Savings, Bybit FlexibleSaving

#### 2. **Fixed (Фіксовані) продукти**

- **Особливості**: Кошти заблоковані на фіксований термін
- **APY**: Зазвичай вищий ніж у Flexible продуктів
- **Термін**: Від 7 днів до 2+ років
- **Ризик**: Мінімальний (гарантований дохід)
- **Приклади**: Binance Locked Savings, Bybit OnChain Fixed

#### 3. **Staking продукти**

- **Особливості**: Делегування токенів валідаторам
- **APY**: Варіюється залежно від мережі
- **Термін**: Зазвичай гнучкий або з мінімальним періодом
- **Ризик**: Залежить від мережі (від низького до високого)
- **Приклади**: Ethereum Staking, Cosmos Staking

### Обов'язкові поля для кожного продукту:

| Поле               | Тип        | Опис                              | Приклад                       |
| ------------------ | ---------- | --------------------------------- | ----------------------------- |
| `id`               | string     | Унікальний ідентифікатор продукту | `"binance_flex_BTC001"`       |
| `symbol`           | string     | Символ криптовалюти               | `"BTC"`, `"ETH"`, `"USDT"`    |
| `name`             | string     | Назва продукту                    | `"Bitcoin Flexible Savings"`  |
| `provider`         | string     | Назва біржі                       | `"Binance"`, `"Bybit"`        |
| `apy`              | float      | Річна відсоткова дохідність       | `2.5`, `15.7`                 |
| `min_amount`       | float/null | Мінімальна сума для участі        | `0.001`, `10.0`               |
| `max_amount`       | float/null | Максимальна сума                  | `1000.0`, `null`              |
| `lock_period_days` | int        | Термін блокування (дні)           | `0` (Flexible), `45` (Fixed)  |
| `product_type`     | string     | Тип продукту                      | `"Flexible"`, `"Fixed"`       |
| `is_active`        | boolean    | Чи активний продукт               | `true`, `false`               |
| `risk_level`       | string     | Рівень ризику                     | `"Low"`, `"Medium"`, `"High"` |

### Додаткові поля (опціональні):

| Поле          | Тип    | Опис                                |
| ------------- | ------ | ----------------------------------- |
| `description` | string | Детальний опис продукту             |
| `website_url` | string | Посилання на продукт на сайті біржі |
| `category`    | string | Категорія продукту в API біржі      |
| `raw_data`    | dict   | Сирі дані з API для діагностики     |

---

## 📊 Правила отримання даних з API біржі

### Загальні правила для всіх бірж:

#### 1. **API Endpoints**

- Використовувати тільки **офіційні API** біржі
- Перевірити **документацію** на наявність Earn/Staking продуктів
- Визначити **authentication** (якщо потрібна): API Key/Secret, OAuth, тощо

#### 2. **Rate Limits**

- Дотримуватися **rate limits** біржі
- Реалізувати **exponential backoff** при помилках
- Використовувати **кешування** для зменшення навантаження

#### 3. **Обробка помилок**

- **Graceful degradation**: Якщо API недоступне - використовувати кеш/БД
- **Retry logic**: Повторні спроби при тимчасових помилках
- **Logging**: Детальне логування всіх помилок та відповідей API

#### 4. **Нормалізація даних**

- **Стандартизація**: Всі продукти приводити до єдиного формату
- **Валідація**: Перевірка обов'язкових полів
- **Очистка**: Видалення невалідних або застарілих продуктів

### Специфічні правила для Earn продуктів:

#### 1. **Визначення типів продуктів**

**Flexible продукти:**

- `lock_period_days = 0`
- `product_type = "Flexible"`
- Можна вилучити кошти в будь-який час

**Fixed продукти:**

- `lock_period_days > 0` (конкретна кількість днів)
- `product_type = "Fixed"`
- Кошти заблоковані на термін

#### 2. **APY (Annual Percentage Yield)**

- Використовувати **річну** відсоткову ставку
- Перетворювати з інших форматів (щоденна, щомісячна) на річну
- Зберігати як `float` з точністю до 2-4 знаків після коми

#### 3. **Суми (Amounts)**

- `min_amount` - обов'язкове поле (якщо не вказано - `null`)
- `max_amount` - опціональне поле (якщо не обмежено - `null`)
- Використовувати однакові одиниці виміру (звичайно базова валюта)

#### 4. **Статус продуктів**

- Тільки **активні** продукти (`is_active = true`)
- Відфільтровувати продукти зі статусом "Inactive", "Suspended", тощо

#### 5. **Ризик**

- **Low**: Біржові заощадження, стабільні монети
- **Medium**: Стейкінг популярних мереж
- **High**: Стейкінг нових/ризикових мереж

---

## 📁 Структура модулів нової біржі

### Шлях до нової біржі:

```
yield-data-service/app/services/exchanges/{exchange_name}/
├── __init__.py          # Імпорти модулів біржі
├── api.py               # API клієнт біржі
├── service.py           # Бізнес логіка та сервіси
└── models.py            # Pydantic моделі (опціонально)
```

### 1. **api.py - API клієнт біржі**

#### Призначення:

- Безпосередня взаємодія з API біржі
- Формування HTTP запитів
- Обробка відповідей
- Аутентифікація (якщо потрібна)

#### Обов'язкові методи:

```python
class {ExchangeName}API(BaseExchange):
    def __init__(self, api_key: str, api_secret: str):
        # Ініціалізація базового класу з URL біржі

    def get_headers(self) -> Dict[str, str]:
        # Заголовки для API запитів

    async def get_flexible_savings_products(...) -> List[Dict]:
        # Отримання Flexible продуктів

    async def get_locked_savings_products(...) -> List[Dict]:
        # Отримання Fixed продуктів

    async def get_earn_products() -> List[Dict]:
        # Отримання всіх Earn продуктів (агрегація)

    async def get_earn_products_by_asset(symbol: str) -> List[Dict]:
        # Отримання продуктів по конкретному символу
```

#### Додаткові методи (якщо потрібні):

- `_generate_signature()` - для підписаних запитів
- `_make_request()` - успадковується від базового класу
- Специфічні методи для конкретної біржі

### 2. **service.py - Бізнес логіка**

#### Призначення:

- Оркестрація роботи з API клієнтом
- Кешування даних
- Синхронізація з базою даних
- Перевірка здоров'я сервісу

#### Обов'язкові методи:

```python
class {ExchangeName}Service(BaseExchangeService):
    async def initialize(self):
        # Ініціалізація API клієнта

    async def get_products_from_api(symbol=None) -> List[Dict]:
        # Отримання продуктів з API

    async def get_products_with_cache(symbol=None) -> List[Dict]:
        # Отримання з кешу або API

    async def sync_products_to_db(symbol=None) -> Dict:
        # Синхронізація в базу даних

    async def test_connection() -> Dict:
        # Тест підключення до API

    async def get_health_status() -> Dict:
        # Статус здоров'я сервісу
```

### 3. **models.py - Pydantic моделі** (опціонально)

#### Призначення:

- Валідація даних з API біржі
- Типізація відповідей
- Документація структури даних

#### Структура:

```python
from pydantic import BaseModel

class {ExchangeName}FlexibleProduct(BaseModel):
    # Поля для Flexible продуктів

class {ExchangeName}FixedProduct(BaseModel):
    # Поля для Fixed продуктів
```

### 4. \***\*init**.py - Імпорти\*\*

#### Структура:

```python
from .api import {ExchangeName}API
from .service import {ExchangeName}Service
from .models import {ExchangeName}FlexibleProduct, {ExchangeName}FixedProduct

__all__ = [
    "{ExchangeName}API",
    "{ExchangeName}Service",
    "{ExchangeName}FlexibleProduct",
    "{ExchangeName}FixedProduct"
]
```

---

## ⚠️ КРИТИЧНИЙ ЧЕК-ЛИСТ ІНТЕГРАЦІЇ

### 🔴 ОБОВ'ЯЗКОВО ПЕРЕВІРИТИ ПІСЛЯ КОЖНОЇ ІНТЕГРАЦІЇ

Після реалізації всіх компонентів нової біржі **ОБОВ'ЯЗКОВО** виконайте цей чек-лист. Пропуск будь-якого пункту призведе до неработоздатності інтеграції (як у випадку з Gate.io).

#### 1. **API Routes - Валідація бірж** 🔴 КРИТИЧНО

```python
# В yield-data-service/app/api/routes.py перевірити 3 місця:

# Місце 1: ~рядок 1036 - get_exchanges endpoint
if exchange_lower not in ["binance", "bybit", "okx", "mexc", "{exchange_name}"]:

# Місце 2: ~рядок 1663 - get_exchanges_popular endpoint
if exchange_lower not in ["binance", "bybit", "okx", "mexc", "{exchange_name}"]:

# Місце 3: ~рядок 1743 - get_exchange_products_sorted_by_popularity endpoint
if exchange_lower not in ["binance", "bybit", "okx", "mexc", "gate", "bitget", "kraken", "{exchange_name}"]:

# Повідомлення про помилку теж треба оновити:
detail=f"Непідтримувана біржа '{{exchange}}'. Доступні: binance, bybit, okx, mexc, gate, bitget, kraken, {exchange_name}"
```

**⚠️ КРИТИЧНО ВАЖЛИВО:** Команди `/all_{exchange}_products` використовують endpoint `/exchanges/{exchange}/popular`. Якщо нова біржа не додана до всіх 3 місць валідації, команда буде повертати `400 Bad Request` з повідомленням "Непідтримувана біржа".

#### 2. **Provider Mapping - Назви бірж** 🔴 КРИТИЧНО

```python
# В yield-data-service/app/api/routes.py перевірити 2 місця:

# Місце 1: ~рядок 1670 - get_exchanges_popular endpoint
provider_mapping = {{
    'binance': 'Binance',
    'bybit': 'Bybit',
    'okx': 'OKX',
    'mexc': 'MEXC',
    '{exchange_name}': '{ExchangeName}'  # Додати нову біржу
}}

# Місце 2: ~рядок 1770 - get_exchange_products_sorted_by_popularity endpoint
provider_mapping = {{
    'binance': 'Binance',
    'bybit': 'Bybit',
    'okx': 'OKX',
    'mexc': 'MEXC',
    'gate': 'Gate.io',
    'bitget': 'bitget',
    'kraken': 'Kraken',
    '{exchange_name}': '{ExchangeName}'  # Додати нову біржу
}}

# В yield-telegram-bot/bot/handlers/filtered_products.py ~рядок 99
provider_mapping = {{
    'binance': 'Binance',
    'bybit': 'Bybit',
    'okx': 'OKX',
    '{exchange_name}': '{ExchangeName}'  # Додати нову біржу
}}
```

**⚠️ КРИТИЧНО ВАЖЛИВО:** Кожен маршрут з `/exchanges/{exchange}/...` має власний provider_mapping. Якщо не додати нову біржу до всіх mapping, продукти не будуть знайдені в базі даних.

#### 3. **Aggregation Service - Джерела даних** 🔴 КРИТИЧНО

```python
# В yield-data-service/app/services/aggregation_service.py

# Додати в DataSource enum:
API_{EXCHANGE_NAME} = "api_{exchange_name}"

# Додати в fallback_chain:
DataSource.API_{EXCHANGE_NAME},

# Додати в метод _get_exchange_data:
elif source == DataSource.API_{EXCHANGE_NAME}:
    from app.services.exchanges.{exchange_name}.service import {ExchangeName}Service
    service = {ExchangeName}Service()
    await service.initialize()
    data = await service.get_products_with_cache(symbol)
```

#### 4. **Exchange Registry - Реєстрація сервісів**

```python
# В yield-data-service/app/services/exchanges/registry.py

# Додати до AVAILABLE_EXCHANGES:
AVAILABLE_EXCHANGES = ["binance", "bybit", "okx", "mexc", "{exchange_name}"]

# Зареєструвати сервіс в реєстрі
```

#### 5. **Telegram Bot - Списки бірж** 🔴 КРИТИЧНО

```python
# В yield-telegram-bot/bot/handlers/callback_handlers.py
AVAILABLE_EXCHANGES = ["binance", "bybit", "okx", "mexc", "{exchange_name}"]

# В yield-telegram-bot/bot/handlers/main_menu.py
exchanges = ["binance", "bybit", "okx", "mexc", "{exchange_name}"]

# REFERRAL_URLS теж оновити:
REFERRAL_URLS = {{
    "binance": "https://accounts.binance.com/register?ref=YOUR_REF",
    "bybit": "https://www.bybit.com/invite?ref=YOUR_REF",
    "okx": "https://www.okx.com/join/YOUR_REF",
    "mexc": "https://www.mexc.com/register?inviteCode=YOUR_REF",
    "{exchange_name}": "https://www.{exchange_name}.com/ref/YOUR_REF",
}}
```

#### 6. **Docker Compose - Змінні середовища**

```yaml
# В docker-compose.yml додати змінні:
environment:
  - GATE_API_KEY=${{GATE_API_KEY}}
  - GATE_API_SECRET=${{GATE_API_SECRET}}

# І додати env_file:
env_file:
  - .env
```

#### 6. **Telegram Bot - Регістр назв бірж** 🔴 КРИТИЧНО

```python
# В yield-telegram-bot/bot/handlers/exchange_products.py перевірити:

# ❌ НЕПРАВИЛЬНО: provider.title() перетворює "kucoin" на "Kucoin"
data = await api_client.get_exchanges_popular(exchange=provider.title(), limit=1000)

# ✅ ПРАВИЛЬНО: завжди використовувати provider.lower()
data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=1000)

# Це важливо тому що API endpoints очікують назви бірж малими літерами
```

#### 7. **Тестування після інтеграції** ✅

```bash
# 1. Перевірити API endpoint
curl "http://localhost:8000/api/v1/exchanges?exchange={exchange_name}&limit=3"

# 2. Перевірити популярні продукти (використовуються в /all_{exchange}_products)
curl "http://localhost:8000/api/v1/exchanges/{exchange_name}/popular?limit=5"

# 3. Перевірити Telegram bot
curl "http://localhost:8000/api/v1/telegram/exchanges/{exchange_name}/products?limit=3"

# 4. Перевірити логи
docker-compose logs yield-api | grep -i {exchange_name}

# 5. Перевірити базу даних
# SELECT COUNT(*) FROM yield_products WHERE provider = '{ExchangeName}';
```

### 🚨 ПОМИЛКИ, ЯКІ ТРЕБА УНИКНУТИ

#### ❌ **Найпоширеніші помилки (з досвіду Gate.io та KuCoin):**

1. **"Непідтримувана біржа"** - не додали до списків валідації в routes.py
2. **"Provider mapping не знайдено"** - різні формати назв провайдерів
3. **"Exchange not in aggregation"** - не додали до DataSource enum
4. **"Bot shows 'error loading'"** - не оновили Telegram bot handlers
5. **"API keys not found"** - не додали змінні середовища до Docker
6. **"/all\_{exchange}\_products не працює"** - проблеми з /exchanges/{exchange}/popular endpoint (KuCoin case)

#### ✅ **Як уникнути помилок:**

- **Завжди виконуйте чек-лист після інтеграції**
- **Тестуйте API endpoints окремо перед Telegram ботом**
- **Перевіряйте логи на наявність помилок**
- **Не поспішайте з деплоєм - протестуйте локально**

---

## 🚀 Покрокова інструкція інтеграції

### ⚠️ ВАЖЛИВО: ПРІОРИТЕТИ ІНТЕГРАЦІЇ

#### 🔴 **Критичні кроки (зробити ПЕРШИМИ):**

1. **API Routes валідація** - без цього система відхилятиме запити
2. **Provider mapping** - без цього дані не знайдуться в БД
3. **Aggregation Service** - без цього дані не агрегується
4. **Docker змінні** - без цього API ключі не завантажаться

#### 🟡 **Важливі кроки:**

5. **Telegram bot handlers** - без цього бот показуватиме помилки
6. **Exchange registry** - без цього сервіс не зареєструється

#### 🟢 **Допоміжні кроки:**

7. **Тестування** - завжди робити після основних кроків
8. **Документація** - оновити після успішного тестування

---

### Крок 1: Підготовка

#### 1.1 Дослідження API біржі

- Ознайомитися з **офіційною документацією**
- Знайти **Earn/Staking endpoints**
- Визначити **authentication** метод
- Перевірити **rate limits** та **response formats**

#### 1.2 Створення директорії

```bash
# Створити директорію для нової біржі
mkdir -p yield-data-service/app/services/exchanges/{exchange_name}

# Створити базові файли
touch yield-data-service/app/services/exchanges/{exchange_name}/__init__.py
touch yield-data-service/app/services/exchanges/{exchange_name}/api.py
touch yield-data-service/app/services/exchanges/{exchange_name}/service.py
touch yield-data-service/app/services/exchanges/{exchange_name}/models.py
```

#### 1.3 Додавання конфігурації

```bash
# В .env додати API ключі (якщо потрібні)
{EXCHANGE_NAME}_API_KEY=your_api_key
{EXCHANGE_NAME}_API_SECRET=your_api_secret
```

### Крок 2: Реалізація API клієнта (api.py)

#### 2.1 Базова структура

```python
"""
Інтеграція з {ExchangeName} API для отримання Earn продуктів.

{ExchangeName} надає наступні типи Earn продуктів:
- {Опис продуктів біржі}
"""

from typing import List, Dict, Optional, Any
from ..base_exchange import BaseExchange
from app.utils.logger import logger

class {ExchangeName}API(BaseExchange):
    """
    Клієнт для роботи з {ExchangeName} API.

    {Опис особливостей API}
    """

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://api.{exchange_name}.com"  # URL біржі
        )

    def get_headers(self) -> Dict[str, str]:
        """Заголовки для API запитів."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    # Додати специфічні методи аутентифікації якщо потрібні
    # def _generate_signature(self, params: Dict[str, Any]) -> str:
    #     ...

    async def get_flexible_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Отримання Flexible Earn продуктів.
        """
        try:
            # API endpoint для Flexible продуктів
            path = "/v1/earn/flexible"  # Замінити на реальний

            params = {"page": current, "limit": size}
            if asset:
                params["asset"] = asset

            logger.info(f"[{self.__class__.__name__}] Запит Flexible продуктів{f' для {asset}' if asset else ''}")

            # Виклик API
            data = await self._make_request("GET", path, params=params)

            products = []
            items = data.get("data", {}).get("products", [])

            for item in items:
                # Парсинг APY
                apy = float(item.get("apy", 0))

                product = {
                    "id": f"{exchange_name}_flex_{item.get('id', '')}",
                    "symbol": item.get("symbol", ""),
                    "name": f"{item.get('symbol', '')} Flexible Savings",
                    "provider": "{ExchangeName}",
                    "apy": apy,
                    "min_amount": float(item.get("min_amount", 0)),
                    "lock_period_days": 0,  # Flexible завжди 0
                    "product_type": "Flexible",
                    "is_active": item.get("status") == "active",
                    "description": item.get("description", ""),
                    "website_url": f"https://www.{exchange_name}.com/earn",
                    "raw_data": item
                }
                products.append(product)

            logger.info(f"[{self.__class__.__name__}] Отримано {len(products)} Flexible продуктів")
            return products

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Помилка отримання Flexible: {e}")
            return []

    async def get_locked_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Отримання Fixed Earn продуктів.
        """
        try:
            # API endpoint для Fixed продуктів
            path = "/v1/earn/fixed"  # Замінити на реальний

            params = {"page": current, "limit": size}
            if asset:
                params["asset"] = asset

            logger.info(f"[{self.__class__.__name__}] Запит Fixed продуктів{f' для {asset}' if asset else ''}")

            data = await self._make_request("GET", path, params=params)

            products = []
            items = data.get("data", {}).get("products", [])

            for item in items:
                apy = float(item.get("apy", 0))
                lock_days = int(item.get("lock_period", 0))

                product = {
                    "id": f"{exchange_name}_fixed_{item.get('id', '')}",
                    "symbol": item.get("symbol", ""),
                    "name": f"{item.get('symbol', '')} Fixed Savings ({lock_days} days)",
                    "provider": "{ExchangeName}",
                    "apy": apy,
                    "min_amount": float(item.get("min_amount", 0)),
                    "lock_period_days": lock_days,
                    "product_type": "Fixed",
                    "is_active": item.get("status") == "active",
                    "description": f"Fixed savings for {item.get('symbol', '')}",
                    "website_url": f"https://www.{exchange_name}.com/earn",
                    "raw_data": item
                }
                products.append(product)

            logger.info(f"[{self.__class__.__name__}] Отримано {len(products)} Fixed продуктів")
            return products

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Помилка отримання Fixed: {e}")
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Отримання всіх Earn продуктів з агрегацією.
        """
        all_products = []

        try:
            logger.info(f"[{self.__class__.__name__}] Початок отримання всіх Earn продуктів")

            # Отримання Flexible продуктів
            flexible_products = await self.get_flexible_savings_products()
            all_products.extend(flexible_products)
            logger.info(f"[{self.__class__.__name__}] ✅ Отримано {len(flexible_products)} Flexible продуктів")

            # Отримання Fixed продуктів
            fixed_products = await self.get_locked_savings_products()
            all_products.extend(fixed_products)
            logger.info(f"[{self.__class__.__name__}] ✅ Отримано {len(fixed_products)} Fixed продуктів")

            # Нормалізація продуктів
            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(f"[{self.__class__.__name__}] Помилка нормалізації продукту: {norm_error}")
                    normalized_products.append(product)

            logger.info(f"[{self.__class__.__name__}] ✅ Агреговано {len(normalized_products)} Earn продуктів")
            return normalized_products

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Отримання Earn продуктів для конкретного активу.
        """
        all_products = []

        try:
            # Отримання продуктів для конкретного активу
            flexible_products = await self.get_flexible_savings_products(asset=asset)
            fixed_products = await self.get_locked_savings_products(asset=asset)

            all_products.extend(flexible_products)
            all_products.extend(fixed_products)

            # Нормалізація
            normalized_products = []
            for product in all_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)

            logger.info(f"[{self.__class__.__name__}] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Помилка фільтрації продуктів для {asset}: {e}")
            return []
```

#### 2.2 Адаптація під конкретну біржу

- **Замінити** всі `{ExchangeName}`, `{exchange_name}` на реальні назви
- **Перевірити** API endpoints та параметри
- **Адаптувати** парсинг відповідей під формат API біржі
- **Додати** специфічну аутентифікацію якщо потрібна

### Крок 3: Реалізація сервісу (service.py)

#### 3.1 Базова структура

```python
"""
Сервіс для роботи з {ExchangeName} Earn продуктами.

Інкапсулює логіку взаємодії з {ExchangeName}API та кешуванням.
"""

from typing import List, Dict, Optional, Any
from app.config import settings
from app.utils.logger import logger
from ..base_service import BaseExchangeService
from .api import {ExchangeName}API

class {ExchangeName}Service(BaseExchangeService):
    """
    Сервіс для роботи з продуктами {ExchangeName} Earn.

    Інкапсулює логіку взаємодії з {ExchangeName}API та кешуванням.
    """

    def __init__(self):
        super().__init__(exchange_name="{exchange_name}")
        self.api_client: Optional[{ExchangeName}API] = None

    async def initialize(self):
        """Ініціалізація {ExchangeName} API клієнта."""
        api_key = settings.{EXCHANGE_NAME}_API_KEY
        api_secret = settings.{EXCHANGE_NAME}_API_SECRET

        # Перевірка наявності ключів (якщо потрібні)
        if not api_key or not api_secret:
            logger.warning(f"⚠️ {ExchangeName} API ключі не налаштовані. Сервіс працюватиме в обмеженому режимі.")

        self.api_client = {ExchangeName}API(api_key or "", api_secret or "")
        logger.info(f"✅ {ExchangeName}Service ініціалізовано.")

    async def get_products_from_api(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримання продуктів безпосередньо з {ExchangeName} API.
        """
        if not self.api_client:
            logger.error(f"❌ {ExchangeName} API клієнт не ініціалізовано.")
            return []

        if symbol:
            return await self.api_client.get_earn_products_by_asset(asset=symbol)
        else:
            return await self.api_client.get_earn_products()

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тест підключення до {ExchangeName} API.
        """
        if not self.api_client:
            return {"status": "error", "message": f"{ExchangeName} API клієнт не ініціалізовано."}

        start_time = datetime.now()
        try:
            # Спробувати отримати невелику кількість продуктів
            products = await self.api_client.get_flexible_savings_products(size=1)
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            if products is not None:
                return {
                    "status": "success",
                    "message": f"Підключення до {ExchangeName} API успішне",
                    "response_time_ms": duration_ms,
                    "products_found": len(products)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Не вдалося отримати дані з {ExchangeName} API",
                    "response_time_ms": duration_ms
                }

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            return {
                "status": "error",
                "message": f"Помилка підключення до {ExchangeName} API: {e}",
                "response_time_ms": duration_ms
            }
```

#### 3.2 Адаптація сервісу

- **Замінити** всі плейсхолдери на реальні назви
- **Налаштувати** конфігурацію API ключів
- **Адаптувати** логіку тестування підключення

### Крок 4: Реалізація моделей (models.py) - опціонально

```python
"""
Pydantic моделі для {ExchangeName} API відповідей.
"""

from pydantic import BaseModel, Field
from typing import Optional

class {ExchangeName}FlexibleProduct(BaseModel):
    """Модель для Flexible продуктів {ExchangeName}."""
    product_id: str
    symbol: str
    apy: float = Field(..., description="Річна відсоткова дохідність")
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    status: str = Field(..., description="Статус продукту")

class {ExchangeName}FixedProduct(BaseModel):
    """Модель для Fixed продуктів {ExchangeName}."""
    product_id: str
    symbol: str
    apy: float
    lock_period: int = Field(..., description="Термін блокування в днях")
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    status: str
```

### Крок 5: Налаштування імпортів (**init**.py)

```python
"""
Імпорти для модуля {exchange_name}.
"""

from .api import {ExchangeName}API
from .service import {ExchangeName}Service
from .models import {ExchangeName}FlexibleProduct, {ExchangeName}FixedProduct

__all__ = [
    "{ExchangeName}API",
    "{ExchangeName}Service",
    "{ExchangeName}FlexibleProduct",
    "{ExchangeName}FixedProduct"
]
```

### Крок 6: Реєстрація біржі в системі

#### 6.1 Додавання до aggregation_service.py

```python
# В app/services/aggregation_service.py додати підтримку нової біржі

# В класі DataSource додати:
API_{EXCHANGE_NAME} = "api_{exchange_name}"

# В fallback_chain додати:
DataSource.API_{EXCHANGE_NAME},

# В методі _get_exchange_data додати:
elif source == DataSource.API_{EXCHANGE_NAME}:
    from app.services.exchanges.{exchange_name}.service import {ExchangeName}Service
    service = {ExchangeName}Service()
    await service.initialize()
    data = await service.get_products_with_cache(symbol)
```

#### 6.2 Додавання API endpoints

```python
# В app/api/routes.py додати нові маршрути

@router.get("/api/v1/{exchange_name}/test")
async def test_{exchange_name}_connection():
    """Тест підключення до {ExchangeName} API."""
    # Реалізація тесту

@router.get("/api/v1/{exchange_name}/products")
async def get_{exchange_name}_products():
    """Отримання продуктів {ExchangeName}."""
    # Реалізація отримання продуктів

@router.post("/api/v1/{exchange_name}/sync")
async def sync_{exchange_name}_products():
    """Синхронізація продуктів {ExchangeName} в БД."""
    # Реалізація синхронізації
```

**⚠️ КРИТИЧНО ВАЖЛИВО:** Також потрібно оновити існуючий маршрут `/exchanges/{exchange}/popular` для нової біржі. Цей endpoint використовується командами `/all_{exchange}_products` в Telegram боті.

```python
# В routes.py знайти функцію get_exchange_products_sorted_by_popularity (~рядок 1743)

# Додати нову біржу до списку валідації:
if exchange_lower not in ["binance", "bybit", "okx", "mexc", "gate", "bitget", "kraken", "{exchange_name}"]:

# Додати до provider_mapping цієї функції:
provider_mapping = {{
    'binance': 'Binance',
    'bybit': 'Bybit',
    'okx': 'OKX',
    'mexc': 'MEXC',
    'gate': 'Gate.io',
    'bitget': 'bitget',
    'kraken': 'Kraken',
    '{exchange_name}': '{ExchangeName}'  # Додати нову біржу
}}
```

#### 6.3 Додавання до Telegram бота

##### 6.3.1 API Client (`yield-telegram-bot/bot/services/api_client.py`)

```python
# Додати методи для нової біржі

async def get_{exchange_name}_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
    """Отримання продуктів {ExchangeName}."""
    params = {}
    if limit:
        params["limit"] = limit
    return await self._get(f"/api/v1/exchanges/{exchange_name}/products", params=params)

async def get_{exchange_name}_popular(self, limit: Optional[int] = None) -> Dict[str, Any]:
    """Отримання популярних продуктів {ExchangeName}."""
    params = {}
    if limit:
        params["limit"] = limit
    return await self._get(f"/api/v1/exchanges/{exchange_name}/popular", params=params)
```

##### 6.3.2 Оновлення головного меню (`yield-telegram-bot/bot/handlers/main_menu.py`)

**Додати біржу до списку для відображення:**

```python
# В _format_exchanges_quick_view додати нову біржу
exchanges = ["binance", "bybit", "okx", "{exchange_name}"]
```

**Додати реферальне посилання:**

```python
# В REFERRAL_URLS додати
REFERRAL_URLS = {
    "binance": "https://accounts.binance.com/register?ref=YOUR_REF",
    "bybit": "https://www.bybit.com/invite?ref=YOUR_REF",
    "okx": "https://www.okx.com/join/YOUR_REF",
    "{exchange_name}": "https://www.{exchange_name}.com/ref/YOUR_REF",
}
```

##### 6.3.3 Оновлення обробників продуктів біржі (`yield-telegram-bot/bot/handlers/exchange_products.py`)

**Додати біржу до списку розпізнаваних:**

```python
# В show_all_exchange_products_command додати
if provider not in ["binance", "bybit", "okx", "{exchange_name}"]:
    await message.answer(f"❌ Невідома біржа '{provider}'. Доступні біржі: binance, bybit, okx, {exchange_name}")
    return
```

**⚠️ КРИТИЧНО ВАЖЛИВО:** Перевірити, що виклики API використовують правильний регістр назв бірж:

```python
# ❌ НЕПРАВИЛЬНО: provider.title() може перетворити "kucoin" на "Kucoin"
data = await api_client.get_exchanges_popular(exchange=provider.title(), limit=1000)

# ✅ ПРАВИЛЬНО: завжди використовувати provider.lower()
data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=1000)
```

Це важливо тому що API endpoints очікують назви бірж малими літерами. Неправильний регістр призведе до помилки "Непідтримувана біржа".

##### 6.3.4 Оновлення callback handlers (`yield-telegram-bot/bot/handlers/callback_handlers.py`)

**Додати біржу до списку доступних:**

```python
AVAILABLE_EXCHANGES = ["binance", "bybit", "okx", "{exchange_name}"]
```

##### 6.3.5 Оновлення клавіатур фільтрів (`yield-telegram-bot/bot/keyboards/filters.py`)

Нові біржі автоматично підтримуються через існуючі функції клавіатур, оскільки вони використовують динамічні списки.

##### 6.3.6 Додавання команд до бота

Після додавання API методів, бот автоматично підтримує команди:

- `/all_{exchange_name}_products` - всі продукти біржі
- Фільтри та сортування працюють автоматично
- Реферальні посилання відображаються в огляді бірж

---

## 📱 Інтеграція з Telegram ботом

### Детальна інформація про відображення продуктів у Telegram боті

### Загальні принципи відображення

#### 1. **Форматування таблиць**

Всі таблиці використовують monospace шрифт (`<pre>` тег) для вирівнювання колонок:

```python
# Структура таблиці
result = "<pre>"
result += "Заголовок1  Заголовок2  Заголовок3\n"
result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
result += f"{col1} {col2} {col3}\n"
result += "</pre>"
```

#### 2. **Адаптивне форматування APY**

```python
def format_apy(apy: float, width: int = 6) -> str:
    if apy >= 1:
        return f"{apy:.1f}%".rjust(width)      # 3.2%
    elif apy >= 0.1:
        return f"{apy:.2f}%".rjust(width)      # 0.85%
    elif apy >= 0.01:
        return f"{apy:.3f}%".rjust(width)      # 0.085%
    else:
        return f"{apy:.4f}%".rjust(width)      # 0.0085%
```

#### 3. **Пагінація**

- **Розмір сторінки**: 30 продуктів
- **Кнопки навігації**: "⬅️ Попередня", "1/5", "Наступна ➡️"
- **Збереження фільтрів**: при зміні сторінки фільтри зберігаються

### Сторінка 1: Головне меню

#### Відображення топ продуктів

```python
# ТОП 10 продуктів з усіх бірж
text = "🔥 <b>ТОП 10 за APY</b>\n\n"
text += "<pre>"
text += "№  Продукт  Біржа     APY    Тип\n"
text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

for i, product in enumerate(top_products[:10], 1):
    symbol = product["symbol"][:7].ljust(7)
    provider = product["provider"][:9].ljust(9)
    apy = format_apy(product["apy"])
    type_str = "Flex" if product["lock_period_days"] == 0 else f"{product['lock_period_days']}d"
    type_str = type_str.ljust(4)[:4]

    text += f"{i:2d} {symbol} {provider} {apy} {type_str}\n"
```

#### Швидкий огляд по біржам

Для кожної біржі відображається по 4 пріоритетні криптовалюти (BTC, ETH, SOL, USDT):

```
Binance перейти ↗️
📊 BTC 0.020% • ETH 1.3% • SOL 2.3% • USDT 2.1%
Показати: /all_binance_products
```

### Сторінка 2: Продукти конкретної біржі

#### Формат таблиці

```python
# Таблиця продуктів біржі з пагінацією
text = f"🏦 Всі продукти біржі {exchange.title()}\n\n"

# Активні фільтри
filters_display = await FilterStateManager.get_filters_display(state)
text += filters_display + "\n\n"

# Таблиця
table_text = format_exchange_product_table(products, page, items_per_page)
text += table_text
```

#### Структура таблиці

```
№  Продукт  APY     Тип       Період
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1  BTC      3.25%   Flexible  —
2  ETH      5.85%   Locked    30d
3  SOL      4.15%   Flexible  —
```

#### Фільтри та сортування

**Тип продукту**: Flexible/Locked
**APY діапазон**: від X% до Y%
**Сортування**:

- ⭐ Популярність (за популярністю монети)
- 📈 APY (спадання)
- 📉 APY (зростання)

### Сторінка 3: Flexible продукти з усіх бірж

#### Формат таблиці

```
⚡ Flexible Products — усі біржі
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Фільтри: 🪙 BTC • 🏦 Binance • 📊 APY (спадання)

Продукт  Біржа     APY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BTC      Binance   3.2%
ETH      Bybit     5.8%
SOL      OKX       4.1%

📊 Показано: 30 з 150 продуктів (сторінка 1/5)
```

#### Фільтри

- **🪙 Продукт**: вибір конкретної криптовалюти
- **🏦 Біржа**: фільтр по конкретній біржі
- **♻️ Скинути фільтри**: очищення всіх фільтрів

#### Сортування

- **📊 Сортувати**: вибір методу сортування
  - 📈 APY ↓ (спадання)
  - 📉 APY ↑ (зростання)
  - ⭐ Популярність

### Сторінка 5: Продукт по всіх біржах

#### Формат порівняльної таблиці

```
💳 BTC — усі доступні біржі
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Пропозиції по продукту BTC

Біржа    Тип       APY     Період
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bybit    Flexible  3.2%    —
Binance  Locked    6.1%    45d
OKX      Flexible  2.8%    —
```

### Фільтри та сортування

#### Типи фільтрів

1. **Продукт (символ)**: BTC, ETH, SOL, USDT, etc.
2. **Біржа (провайдер)**: Binance, Bybit, OKX, etc.
3. **Тип продукту**: Flexible/Locked
4. **APY діапазон**: від X% до Y%

#### Методи сортування

1. **Популярність**: за популярністю монети (CoinGecko ranking)
2. **APY (спадання)**: від вищого до нижчого APY
3. **APY (зростання)**: від нижчого до вищого APY

#### Стан фільтрів

```python
# Структура збереження фільтрів
filters = {
    "product": "BTC",        # символ криптовалюти
    "exchange": "binance",   # назва біржі
    "type": "flexible",      # тип продукту
    "apy_min": 1.0,          # мінімальний APY
    "apy_max": 10.0,         # максимальний APY
    "sort_by": "apy_desc"    # метод сортування
}
```

### Інтеграція нової біржі в відображення

Після додавання нової біржі до системи:

1. **Головна сторінка** автоматично включить нову біржу в огляд
2. **Команди** `/all_{exchange_name}_products` працюватимуть
3. **Фільтри** автоматично включать нову біржу
4. **Сортування** працюватиме для продуктів нової біржі
5. **Реферальні посилання** відображатимуться в огляді

#### Автоматична підтримка

Нова біржа автоматично підтримується в:

- Головному меню (огляд по біржам)
- Фільтрах вибору біржі
- Командах `/all_{exchange}_products`
- Порівняльних таблицях
- Статистиці та аналітиці

### Крок 7: Оновлення конфігурації

#### 7.1 Додавання до .env

```bash
# Додати API ключі для нової біржі
{EXCHANGE_NAME}_API_KEY=your_api_key_here
{EXCHANGE_NAME}_API_SECRET=your_api_secret_here
```

#### 7.2 Додавання до settings

```python
# В app/config.py додати поля для нової біржі
{exchange_name}_api_key: Optional[str] = Field(default=None, description="{ExchangeName} API Key")
{exchange_name}_api_secret: Optional[str] = Field(default=None, description="{ExchangeName} API Secret")
```

---

## ✅ Валідація та тестування

### 1. **Unit тестування**

#### Тестування API клієнта:

```python
# tests/services/test_{exchange_name}_integration.py

async def test_{exchange_name}_api_connection():
    """Тест підключення до {ExchangeName} API."""
    api = {ExchangeName}API("test_key", "test_secret")
    result = await api.test_connection()
    assert result["status"] == "success"

async def test_{exchange_name}_flexible_products():
    """Тест отримання Flexible продуктів."""
    api = {ExchangeName}API("test_key", "test_secret")
    products = await api.get_flexible_savings_products()
    assert isinstance(products, list)
    for product in products:
        assert "symbol" in product
        assert "apy" in product
        assert product["lock_period_days"] == 0

async def test_{exchange_name}_fixed_products():
    """Тест отримання Fixed продуктів."""
    api = {ExchangeName}API("test_key", "test_secret")
    products = await api.get_locked_savings_products()
    assert isinstance(products, list)
    for product in products:
        if product["lock_period_days"] > 0:
            assert product["product_type"] == "Fixed"
```

#### Тестування сервісу:

```python
# tests/services/test_{exchange_name}_service.py

async def test_{exchange_name}_service_initialization():
    """Тест ініціалізації сервісу."""
    service = {ExchangeName}Service()
    await service.initialize()
    assert service.api_client is not None

async def test_{exchange_name}_health_check():
    """Тест перевірки здоров'я."""
    service = {ExchangeName}Service()
    await service.initialize()
    health = await service.get_health_status()
    assert health["status"] in ["healthy", "degraded"]
```

### 2. **Інтеграційне тестування**

#### Тест API endpoints:

```bash
# Тест health check
curl http://localhost:8000/api/v1/{exchange_name}/test

# Тест отримання продуктів
curl "http://localhost:8000/api/v1/exchanges/{exchange_name}/products?limit=5"

# ⚠️ КРИТИЧНО ВАЖЛИВО: Тест популярних продуктів (використовується в /all_{exchange}_products)
curl "http://localhost:8000/api/v1/exchanges/{exchange_name}/popular?limit=5"

# Тест синхронізації
curl -X POST "http://localhost:8000/api/v1/{exchange_name}/sync"
```

#### Тест бази даних:

```sql
-- Перевірка кількості продуктів
SELECT COUNT(*) FROM yield_products WHERE provider = '{ExchangeName}';

-- Перевірка типів продуктів
SELECT product_type, COUNT(*) FROM yield_products
WHERE provider = '{ExchangeName}'
GROUP BY product_type;

-- Перевірка активних продуктів
SELECT symbol, apy, lock_period_days FROM yield_products
WHERE provider = '{ExchangeName}' AND is_active = true
ORDER BY apy DESC LIMIT 10;
```

### 3. **Функціональне тестування**

#### Тест через Telegram бот:

1. Відправити команду `/all_{exchange_name}_products`
2. Перевірити що бот повертає список продуктів (не показує "❌ Помилка відображення продуктів")
3. Перевірити пагінацію (якщо більше 50 продуктів)
4. Перевірити сортування за популярністю

**⚠️ Якщо команда `/all_{exchange_name}_products` показує помилку:**

- Перевірити логи на `Client error '400 Bad Request'` для `/exchanges/{Exchange}/popular`
- Перевірити що біржа додана до всіх 3 місць валідації в routes.py
- Перевірити що provider_mapping містить нову біржу
- Перевірити що Telegram бот використовує `provider.lower()` в API викликах

#### Тест агрегації:

```bash
# Тест агрегації
curl "http://localhost:8000/api/v1/aggregation/test?strategy=comprehensive&limit=10"
```

---

## 📊 Моніторинг та підтримка

### 1. **Метрики для моніторингу**

#### Prometheus метрики:

```python
# В service.py додати метрики
from app.utils.metrics import EXTERNAL_API_CALLS, API_RESPONSE_TIME

# В методі get_products_with_cache:
EXTERNAL_API_CALLS.labels(exchange="{exchange_name}").inc()
API_RESPONSE_TIME.labels(exchange="{exchange_name}").observe(response_time)
```

#### Grafana dashboards:

- API Response Time для {ExchangeName}
- Кількість помилок API
- Кількість продуктів в БД
- Hit Rate кешу

### 2. **Логування**

#### Структура логів:

```python
# Інформаційні логи
logger.info(f"[{ExchangeName}] Отримано {len(products)} продуктів")

# Попередження
logger.warning(f"[{ExchangeName}] API rate limit досягнуто, пауза {backoff_time}s")

# Помилки
logger.error(f"[{ExchangeName}] Помилка API: {e}", exc_info=True)
```

#### Логи для моніторингу:

- Кількість отриманих продуктів
- Час відповіді API
- Кількість помилок
- Rate limit події

### 3. **Обробка помилок**

#### Graceful degradation:

```python
try:
    # Спроба отримати з API
    products = await self.api_client.get_earn_products()
except Exception as e:
    logger.error(f"API недоступний: {e}")
    # Fallback до кешу/БД
    products = await self.get_cached_products()
```

#### Retry logic:

```python
for attempt in range(self.max_retry_attempts):
    try:
        return await self._make_request(...)
    except Exception as e:
        if attempt == self.max_retry_attempts - 1:
            raise
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 4. **Оновлення та підтримка**

#### Регулярні завдання:

1. **Щоденна синхронізація** продуктів
2. **Моніторинг API** на зміни в структурі
3. **Оновлення документації** при змінах API
4. **Тестування** нових функцій API

#### Процедура оновлення:

```bash
# 1. Зупинити сервіс
docker-compose stop yield-api

# 2. Оновити код
git pull origin main

# 3. Перевірити API біржі на зміни
curl https://api.{exchange_name}.com/v1/earn/docs

# 4. Оновити код якщо потрібно
# vim app/services/exchanges/{exchange_name}/api.py

# 5. Запустити тести
docker-compose run --rm yield-api pytest tests/services/test_{exchange_name}_*

# 6. Перезапустити сервіс
docker-compose up -d yield-api
```

---

## 🎯 Підсумок інтеграції

### ✅ Що буде реалізовано після інтеграції нової біржі:

1. **Новий API клієнт** з підтримкою всіх Earn продуктів біржі
2. **Сервісний шар** з кешуванням та синхронізацією в БД
3. **REST API endpoints** для нової біржі
4. **Telegram бот інтеграція** з багаторівневою навігацією
5. **Моніторинг та метрики** для нової біржі
6. **Тестове покриття** для всіх компонентів

### 📱 Інтеграція з Telegram ботом:

#### Автоматична підтримка після додавання:

**📄 Сторінка 1 (головне меню):**

- Нова біржа з'явиться в огляді з 4 пріоритетними монетами
- Реферальне посилання буде відображатися
- Команда `/all_{exchange}_products` стане доступною

**📄 Сторінка 2 (продукти біржі):**

- Повна підтримка фільтрів: тип продукту, APY діапазон
- Сортування: популярність, APY (зростання/спадання)
- Пагінація з 30 продуктів на сторінку

**📄 Сторінка 3 (Flexible продукти):**

- Продукти нової біржі включені в загальну таблицю
- Підтримка фільтрів по біржі та продукту
- Сортування працює для всіх бірж одночасно

**📄 Сторінка 5 (порівняння продукту):**

- Нова біржа включена в порівняльні таблиці
- Відображення всіх типів продуктів біржі

#### Команди бота:

- `/all_{exchange_name}_products` - всі продукти біржі
- `/yield {symbol}` - пошук продуктів по символу
- `/top` - топ продукти з усіх бірж

#### Фільтри та сортування:

- **Продукт**: вибір конкретної криптовалюти
- **Біржа**: фільтр по конкретній біржі
- **Тип**: Flexible/Locked продукти
- **APY**: діапазон відсоткових ставок
- **Сортування**: популярність, APY ↑/↓

### 📈 Переваги нової інтеграції:

- **Розширення екосистеми**: Додаткові продукти для користувачів
- **Конкуренція**: Порівняння ставок між біржами
- **Монетизація**: Реферальні посилання на нову біржу
- **Надійність**: Резервні джерела даних
- **Багаторівнева навігація**: 5+ сторінок з різними режимами перегляду

### 🔄 Наступні кроки після інтеграції:

1. **Тестування в production**
2. **Моніторинг стабільності**
3. **Оптимізація продуктивності**
4. **Додавання нових бірж** за аналогією
5. **Реалізація додаткових сторінок** (Locked продукти, детальні порівняння)

---

## 🔧 TROUBLESHOOTING: Виправлення поширених проблем

### 🚨 **Критичні помилки інтеграції (з досвіду Gate.io)**

#### 1. **"Непідтримувана біржа" в API**

**Симптоми:**

- API повертає `400 Bad Request` з повідомленням "Непідтримувана біржа"
- Telegram бот показує "помилка завантаження"

**Причина:**
Не додано нову біржу до списків валідації в `routes.py`

**Виправлення:**

```python
# В yield-data-service/app/api/routes.py знайти 2 місця:
if exchange_lower not in ["binance", "bybit", "okx", "mexc"]:  # Додати вашу біржу
```

#### 2. **API ключі не завантажуються**

**Симптоми:**

- Логи показують "API ключі для {exchange} не налаштовані"
- API повертає помилки аутентифікації

**Причина:**
Не додано змінні середовища до Docker Compose

**Виправлення:**

```yaml
# В docker-compose.yml додати:
env_file:
  - .env

environment:
  - {EXCHANGE_NAME}_API_KEY=${{{EXCHANGE_NAME}_API_KEY}}
  - {EXCHANGE_NAME}_API_SECRET=${{{EXCHANGE_NAME}_API_SECRET}}
```

#### 3. **"Provider mapping не знайдено"**

**Симптоми:**

- API працює, але повертає пусті результати
- Помилки в логах про mapping провайдерів

**Причина:**
Різні формати назв провайдерів в різних частинах системи

**Виправлення:**

```python
# Синхронізувати назви в:
# yield-data-service/app/api/routes.py
# yield-telegram-bot/bot/handlers/filtered_products.py

provider_mapping = {
    '{exchange_name}': '{ExchangeName}',  # Додати консистентну назву
}
```

#### 4. **Telegram бот показує "error loading"**

**Симптоми:**

- API працює нормально
- Але бот показує помилки завантаження для нової біржі

**Причина:**
Не оновлено списки бірж в Telegram bot handlers

**Виправлення:**

```python
# В yield-telegram-bot/bot/handlers/callback_handlers.py
AVAILABLE_EXCHANGES = ["binance", "bybit", "okx", "mexc", "{exchange_name}"]

# В yield-telegram-bot/bot/handlers/main_menu.py
exchanges = ["binance", "bybit", "okx", "mexc", "{exchange_name}"]
```

#### 4.1 **Команда /all\_{exchange}\_products повертає "Помилка відображення продуктів"**

**Симптоми:**

- API працює нормально
- Але команда `/all_kucoin_products` показує "❌ Помилка відображення продуктів"
- Логи показують `Client error '400 Bad Request' for url 'http://yield-api:8000/api/v1/exchanges/Kucoin/popular'`

**Причина:**
Команди `/all_{exchange}_products` використовують endpoint `/exchanges/{exchange}/popular`, але:

1. Нова біржа не додана до валідації цього endpoint
2. provider_mapping відсутній для цього endpoint
3. Telegram бот використовує неправильний регістр (`provider.title()` замість `provider.lower()`)

**Виправлення:**

```python
# 1. Додати біржу до валідації в routes.py (~рядок 1763)
if exchange_lower not in ["binance", "bybit", "okx", "mexc", "gate", "bitget", "kraken", "kucoin"]:

# 2. Додати до provider_mapping (~рядок 1770)
provider_mapping = {{
    'binance': 'Binance',
    'bybit': 'Bybit',
    'okx': 'OKX',
    'mexc': 'MEXC',
    'gate': 'Gate.io',
    'bitget': 'bitget',
    'kraken': 'Kraken',
    'kucoin': 'KuCoin'  # Додати нову біржу
}}

# 3. Виправити регістр в Telegram боті (~рядок 102)
data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=1000)
```

#### 5. **HTTP 404 на API endpoints біржі**

**Симптоми:**

- API клієнт створений, але повертає 404 помилки
- Логи показують неправильні URL

**Причина:**
Неправильний base_url або шлях до endpoint

**Виправлення:**

```python
# Перевірити в api.py:
def __init__(self, api_key: str, api_secret: str):
    super().__init__(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://api.{exchange_name}.com"  # Правильний base URL
    )

# Перевірити endpoint paths:
async def get_flexible_savings_products(self):
    path = "earn/flexible"  # Правильний шлях БЕЗ /api/v4/
```

#### 6. **Невідповідність структури API відповідей**

**Симптоми:**

- API повертає дані, але парсинг падає з KeyError
- Логи показують помилки парсингу

**Причина:**
Структура JSON відповіді біржі відрізняється від очікуваної

**Виправлення:**

```python
# Спочатку протестувати API окремо:
response = requests.get("https://api.{exchange_name}.com/v1/earn/products")
print(response.json())  # Подивитися реальну структуру

# Потім адаптувати парсинг в api.py:
item.get("apy", 0)  # Замінити на правильні ключі
```

### 🛠️ **Швидка діагностика**

#### **Крок 1: Перевірити логи**

```bash
# Логи API сервісу
docker-compose logs yield-api | grep -i {exchange_name}

# Логи Telegram бота
docker-compose logs telegram-bot | grep -i {exchange_name}
```

#### **Крок 2: Тестувати API окремо**

```bash
# Тестувати API endpoint
curl "http://localhost:8000/api/v1/exchanges?exchange={exchange_name}&limit=3"

# Тестувати health check
curl "http://localhost:8000/api/v1/{exchange_name}/test"
```

#### **Крок 3: Перевірити конфігурацію**

```bash
# Перевірити змінні середовища
docker-compose exec yield-api env | grep {EXCHANGE_NAME}

# Перевірити базу даних
docker-compose exec postgres psql -U postgres -d earn_aggregator -c "SELECT COUNT(*) FROM yield_products WHERE provider = '{ExchangeName}';"
```

#### **Крок 4: Виконати критичний чек-лист**

Повернутися до [Критичного чек-листа інтеграції](#️-критичний-чек-лист-інтеграції) і перевірити кожен пункт.
