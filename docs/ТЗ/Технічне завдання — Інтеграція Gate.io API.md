# Технічне завдання — Інтеграція Gate.io Earn Products (Flexible та Fixed Savings) в EarnAggregator


## 🎯 Мета інтеграції

Імплементувати у **yield-data-service** інтеграцію з Gate.io для отримання та синхронізації продуктів типу **Flexible Savings** (також відомі як Uni Lend Flexible) та **Fixed Savings** (Fixed-term deposits). Підтримати отримання всіх доступних продуктів з цих категорій, нормалізувати дані в уніфікований формат EarnAggregator і забезпечити надійну роботу з урахуванням rate limits, помилок та моніторингу.

### Ключові результати інтеграції:

- Отримання повного переліку активних Flexible та Fixed Savings продуктів з Gate.io
- Агрегація даних з усіх доступних криптовалют (100+ токенів)
- Інтеграція в існуючу архітектуру з підтримкою кешування, fallback та моніторингу
- Відображення продуктів Gate.io у Telegram боті з фільтрами та сортуванням
- Монетизація через реферальну програму Gate.io

---

## 📝 Загальні вимоги

### 1.1 Обов'язкові технічні вимоги

- **API ключі** зберігаються виключно у файлі `.env` в кореневій директорії проекту (змінні: `GATE_API_KEY`, `GATE_API_SECRET`)
- Інтеграція повинна відповідати архітектурі EarnAggregator: окрема директорія `app/services/exchanges/gate/` з файлами `api.py`, `service.py`, `models.py`, `__init__.py`
- Всі зовнішні HTTP виклики через центральний метод `_make_request` з підтримкою backoff/retry, логування, метрик
- Graceful degradation: при недоступності API використовувати кеш/БД з відповідним статусом (degraded)

### 1.2 Стандарти проекту

- Модульна архітектура з чіткими інтерфейсами
- Використання базових класів `BaseExchange` та `BaseExchangeService`
- Підтримка Prometheus метрик для моніторингу
- Структуроване логування з рівнями (INFO, WARNING, ERROR)
- Валідація всіх вхідних та вихідних даних

### 1.3 Вимоги до даних

- Підтримка мінімум 50+ токенів (згідно з актуальним переліком Gate.io Earn)
- APY діапазон: від 0.5% до 20% (з урахуванням промо-кампаній до 499%)
- Типи продуктів: Flexible (lock_period_days = 0) та Fixed (lock_period_days > 0)
- Збереження сирих даних (raw_data) для діагностики

---

## 📚 Джерела та документація

### 2.1 Офіційна документація Gate.io

**Основні джерела:**

- **Gate.io API v4 документація**: https://www.gate.com/docs/developers/apiv4/en/
- **Gate.io API GitHub репозиторій**: https://github.com/gateio/gateapi-python
- **Gate.io Python SDK**: https://pypi.org/project/gate-api/
- **Gate.io OpenAPI Specification**: https://github.com/gateio/gateapi-v4

**ВАЖЛИВО:** Gate.io використовує API v4 (відмінну від v2). Використовувати тільки v4.

### 2.2 Gate.io Earn продукти — продуктова інформація

**Офіційні сторінки Gate.io:**

- **Simple Earn** (Flexible & Fixed): https://www.gate.com/simple-earn
- **HODL & Earn**: https://www.gate.com/hodl (стара назва Flexible Staking)
- **Gate Learn — Simple Earn Guide**: https://www.gate.com/learn/articles/simple-earn/

**Ключова інформація про продукти:**

- **Flexible Savings (Uni Lend)**: немає періоду блокування, можна вивести в будь-який час, APY змінний
- **Fixed Savings**: блокування на фіксований термін (7, 15, 30, 60, 90 днів), APY вищий та фіксований
- **Мінімальні суми**: варіюються по токенах (наприклад, 0.001 BTC, 0.01 ETH, 1 USDT)
- **Розрахунок доходу**: щоденний, формула: `Daily Interest = Amount × APY / 365`
- **Auto-renew**: підтримка автоматичного продовження для Fixed продуктів

### 2.3 Технічні приклади та SDK

**Python SDK:**

- **Офіційний SDK**: `pip install gate-api`
- **Встановлення**: https://github.com/gateio/gateapi-python
- **Документація SDK**: https://gate-api.github.io/gateapi-python/

**Спільнота та допомога:**

- **Gate.io API Telegram**: https://t.me/gateioapi
- **GitHub Issues**: https://github.com/gateio/gateapi-python/issues
- **Stack Overflow** — приклади аутентифікації Python:
  - https://stackoverflow.com/questions/70285234/how-to-authenticate-with-gate-io-api-v4
  - https://stackoverflow.com/questions/72445891/gate-io-api-signature-verification-failed

**Важливі зауваження з форумів:**

1. Gate.io підпис використовує **HMAC SHA512** (не SHA256 як Binance)
2. Timestamp має бути в Unix секундах (не мілісекундах як в OKX)
3. Підпис формується з: `method + "\n" + url + "\n" + query_string + "\n" + sha512(body) + "\n" + timestamp`
4. Порожній body має бути захешований як порожня строка
5. Заголовки: `KEY`, `Timestamp`, `SIGN` (без префіксу X-)

### 2.4 Обмеження та особливості

**З офіційної документації:**

- Rate limits базуються на UID (User ID) для автентифікованих запитів
- Публічні ендпоїнти обмежені по IP: 200 запитів/10 секунд
- Приватні ендпоїнти: 150-200 запитів/10 секунд (залежить від типу)
- WebSocket connections валідні 24 години
- API ключі можна оновлювати з різними правами (read/write)

---

## 🎯 Обсяги інтеграції

### 3.1 Що має бути реалізовано

#### 3.1.1 Отримання Uni Lend (Flexible Savings) продуктів

**Охоплення:**
- Всі доступні токени з Uni Lend (Flexible) — мінімум 50+ токенів
- Поля: currency (токен), rate (APY річна ставка), min_amount, max_amount, status
- Підтримка пагінації (page + limit)

**API Endpoint:** `GET /api/v4/earn/uni/currencies`

#### 3.1.2 Отримання Fixed Savings продуктів

**Охоплення:**
- Всі доступні токени з Fixed Savings
- Різні терміни блокування: 7, 15, 30, 60, 90 днів
- Поля: currency, rate (APY), lock_days, min_amount, max_amount, auto_renew, status

У документації Gate.io API відсутній відкритий endpoint для Fixed Savings, тому потрібно описати альтернативний механізм.
Якщо API не повертає інформацію по Fixed Savings, дані повинні вноситися вручну раз на тиждень або раз на місяць.
Для цього створюється JSON-файл з актуальними ставками, мінімальними сумами та періодом блокування.
Формат і процедура ручного імпорту — аналогічна до MEXC (див. розділ «Ручне додавання продуктів»).

#### 3.1.3 Нормалізація даних

**Обов'язкові поля для EarnAggregator:**

| Поле Gate.io | Поле EarnAggregator | Тип | Опис |
|--------------|---------------------|-----|------|
| Генерується | `id` | string | Формат: `gate_flexible_{currency}` або `gate_fixed_{currency}_{days}` |
| `currency` | `symbol` | string | Символ криптовалюти (BTC, ETH, USDT) |
| Генерується | `name` | string | Формат: "BTC Flexible Savings" або "BTC Fixed 30 days" |
| "Gate.io" | `provider` | string | Завжди "Gate.io" |
| `rate` | `apy` | float | Річна відсоткова дохідність |
| `min_amount` | `min_amount` | float/null | Мінімальна сума для участі |
| `max_amount` | `max_amount` | float/null | Максимальна сума (часто null) |
| `lock_days` / 0 | `lock_period_days` | int | 0 для Flexible, >0 для Fixed |
| "Flexible" / "Fixed" | `product_type` | string | Тип продукту |
| `status` == "enabled" | `is_active` | boolean | Чи активний продукт |
| Визначається | `risk_level` | string | "Low" для Flexible/Fixed savings |
| Повний об'єкт | `raw_data` | dict | Сирі дані з API для діагностики |

#### 3.1.4 Експорт та синхронізація

- Зберігання у PostgreSQL через існуючі сервіси синхронізації
- Унікальний ID mapping: `gate_flexible_{currency}` або `gate_fixed_{currency}_{days}`
- Оновлення існуючих записів (upsert логіка)
- Збереження timestamp останнього оновлення

### 3.2 Додаткові функції

- Фільтрація за символом токену
- Підтримка auto_renew для Fixed продуктів
- Збереження інформації про lending/borrowing rates
- Обробка різних статусів продуктів (enabled, disabled, sold_out)

---

## 🏗️ Архітектура модуля

### 4.1 Розміщення файлів

```
yield-data-service/app/services/exchanges/gate/
├── __init__.py          # Експорт класів модуля
├── api.py               # API клієнт Gate.io
├── service.py           # Бізнес логіка та оркестрація
└── models.py            # Pydantic моделі (опціонально)
```

### 4.2 Структура api.py — клієнт Gate.io

**Призначення:** Безпосередня взаємодія з Gate.io API v4

**Обов'язкові методи:**

- `__init__(api_key, api_secret)` — ініціалізація з базовим URL
- `get_headers()` — формування HTTP заголовків
- `_generate_signature(method, url, query_string, body, timestamp)` — генерація HMAC SHA512 підпису
- `get_uni_currencies()` — отримання Uni Lend currencies (Flexible)
- `get_uni_currency(currency)` — деталі по конкретній валюті
- `get_all_earn_products()` — агрегація всіх Earn продуктів
- `get_earn_products_by_symbol(symbol)` — фільтрація по токену

**Особливості реалізації:**

- Використовувати метод `_make_request()` від базового класу `BaseExchange`
- Підтримка query parameters та request body
- Обробка помилок з відповідними HTTP кодами
- Логування всіх запитів та відповідей

### 4.3 Структура service.py — бізнес логіка

**Призначення:** Оркестрація роботи з API, кешування, БД

**Обов'язкові методи:**

- `initialize()` — ініціалізація API клієнта з конфігурації
- `get_products_from_api(symbol=None)` — отримання з API
- `get_products_with_cache(symbol=None)` — отримання з кешу або API
- `sync_products_to_db(symbol=None)` — синхронізація в PostgreSQL
- `test_connection()` — перевірка підключення до API
- `get_health_status()` — статус здоров'я сервісу

**Інтеграція з інфраструктурою:**

- Prometheus метрики: `EXTERNAL_API_CALLS`, `API_RESPONSE_TIME`
- Redis кешування з TTL (60 хвилин для Flexible, 120 хвилин для Fixed)
- Graceful degradation при недоступності API

### 4.4 Структура models.py — валідація даних

**Призначення:** Pydantic моделі для валідації (опціонально але рекомендовано)

**Рекомендовані моделі:**

- `GateUniCurrency` — модель для Uni Lend currency
- `GateFlexibleProduct` — модель для Flexible продуктів
- `GateFixedProduct` — модель для Fixed продуктів
- `GateNormalizedProduct` — уніфікована модель після нормалізації

---

## 🔐 Специфіка Gate.io API

### 5.1 Аутентифікація та підпис

**Gate.io використовує 2 параметри:**

1. **API Key** (`GATE_API_KEY`)
2. **API Secret** (`GATE_API_SECRET`)

**ВАЖЛИВО:** Gate.io НЕ має параметру Passphrase (на відміну від OKX)

#### 5.1.1 Алгоритм генерації підпису

**Формула підпису:**

```
message = method + "\n" + request_path + "\n" + query_string + "\n" + hex(SHA512(body)) + "\n" + timestamp
signature = hex(HMAC_SHA512(message, secret_key))
```

**Правила формування підпису:**

1. **Method**: HTTP метод у UPPERCASE (GET, POST, DELETE, PATCH)
2. **Request Path**: шлях без хоста (наприклад: `/api/v4/earn/uni/currencies`)
3. **Query String**: параметри без URL-encode, порядок як в URL (наприклад: `page=1&limit=100`)
4. **Body Hash**: SHA512 hash тіла запиту у hex форматі
   - Для GET запитів без body використовувати hash порожньої строки
   - Порожня строка: `cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e`
5. **Timestamp**: Unix timestamp в секундах (не мілісекундах)
6. **Signature**: HMAC SHA512 у hex форматі (не Base64)

**Приклад генерації (псевдокод):**

```
method = "GET"
path = "/api/v4/earn/uni/currencies"
query = "page=1&limit=100"
body = ""
timestamp = int(time.time())

body_hash = hashlib.sha512(body.encode()).hexdigest()
message = f"{method}\n{path}\n{query}\n{body_hash}\n{timestamp}"
signature = hmac.new(secret.encode(), message.encode(), hashlib.sha512).hexdigest()
```

#### 5.1.2 Обов'язкові HTTP заголовки

**Для автентифікованих запитів:**

- `KEY`: API ключ користувача (без префіксу)
- `Timestamp`: Unix timestamp в секундах
- `SIGN`: Hex-encoded HMAC SHA512 підпис
- `Content-Type`: `application/json`

**ВАЖЛИВО — відмінності від інших бірж:**

- **Binance**: використовує `X-MBX-APIKEY` та HMAC SHA256
- **OKX**: використовує `OK-ACCESS-KEY`, `OK-ACCESS-PASSPHRASE` та ISO 8601 timestamp
- **Gate.io**: використовує `KEY` (без префіксу) та Unix timestamp

#### 5.1.3 Timestamp валідація

**Правила:**

- Різниця між timestamp запиту та серверним часом не може перевищувати **60 секунд**
- Використовувати `int(time.time())` для генерації
- Формат: Unix timestamp в секундах (10 цифр), наприклад: `1730302800`

**При помилці timestamp:**

- HTTP код: `401 Unauthorized`
- Повідомлення: `{"label":"REQUEST_EXPIRED","message":"Request timestamp expired"}`

#### 5.1.4 Особливості підпису (З форумів та GitHub Issues)

**КРИТИЧНО ВАЖЛИВО:**

1. **Query string порядок**: параметри мають бути в тому ж порядку, що і в URL
2. **Порожній body**: для GET запитів використовувати hash порожньої строки
3. **Hex encoding**: підпис у hex форматі (lowercase), не Base64
4. **Newline символи**: `\n` між компонентами message
5. **SHA512 для body та підпису**: використовувати SHA512, не SHA256

**Поширені помилки (з Stack Overflow):**

- Неправильний порядок параметрів в query string
- Використання Base64 замість hex encoding
- Неправильний hash порожнього body
- Відсутність newline символів між компонентами

### 5.2 Base URL та ендпоїнти

**Production Base URL:** `https://api.gateio.ws/api/v4`

**Testnet Base URL:** `https://api-testnet.gateapi.io/api/v4`

**ВАЖЛИВО:** Gate.io має повноцінний **Testnet** для тестування з окремими API ключами.

### 5.3 Особливості роботи з API

#### 5.3.1 HTTP методи

- **GET** — для отримання даних (публічних та приватних)
- **POST** — для створення ресурсів (subscribe, lend)
- **PATCH** — для оновлення ресурсів
- **DELETE** — для видалення ресурсів (cancel, redeem)

#### 5.3.2 Параметри запиту

- **Query string**: для GET запитів параметри в URL
- **Request body**: для POST/PATCH (формат JSON)
- **Пагінація**: `page` (починається з 1) та `limit` (макс 1000, за замовчуванням 100)

#### 5.3.3 Коди відповіді

- **2XX** — успішна операція
- **401** — помилка аутентифікації (неправильний ключ, підпис, timestamp)
- **404** — ресурс не знайдено
- **429** — rate limit досягнуто
- **5XX** — помилка сервера Gate.io (повторити запит)

**Структура помилок:**

```json
{
  "label": "INVALID_CREDENTIALS",
  "message": "Invalid API Key"
}
```

---

## 📊 Контракти API та структури даних

### 6.1 Uni Lend (Flexible Savings) API

#### 6.1.1 Отримання списку currencies

**Endpoint:** `GET /api/v4/earn/uni/currencies`

**Опис:** Повертає список валют доступних для Uni Lend (Flexible Savings)

**Параметри запиту:**

| Параметр | Тип | Обов'язковий | Опис |
|----------|-----|--------------|------|
| `page` | integer | Ні | Номер сторінки (починається з 1, за замовчуванням 1) |
| `limit` | integer | Ні | Кількість записів на сторінку (макс 1000, за замовчуванням 100) |

**Приклад відповіді:**

```json
[
  {
    "currency": "USDT",
    "min_amount": "1",
    "max_amount": "",
    "rate": "0.05",
    "status": "enabled"
  },
  {
    "currency": "BTC",
    "min_amount": "0.001",
    "max_amount": "",
    "rate": "0.02",
    "status": "enabled"
  }
]
```

**Ключові поля:**

- `currency` (string): Назва криптовалюти
- `min_amount` (string): Мінімальна сума для lending
- `max_amount` (string): Максимальна сума (порожня = необмежено)
- `rate` (string): Річна відсоткова ставка у десятковому форматі (0.05 = 5%)
- `status` (string): Статус валюти (`enabled`, `disabled`)

#### 6.1.2 Отримання деталей по конкретній валюті

**Endpoint:** `GET /api/v4/earn/uni/currencies/{currency}`

**Опис:** Повертає детальну інформацію про конкретну валюту

**Параметри:**

- `currency` (path parameter): Назва валюти (BTC, ETH, USDT)

**Приклад відповіді:**

```json
{
  "currency": "USDT",
  "min_amount": "1",
  "max_amount": "",
  "rate": "0.05",
  "rate_list": [
    {
      "days": 0,
      "rate": "0.05"
    }
  ],
  "status": "enabled"
}
```

### 6.2 Fixed Savings API (якщо доступний)

**ВАЖЛИВО:** Gate.io може не мати окремого публічного ендпоїнту для списку всіх Fixed Savings продуктів. Альтернативні підходи:

#### Підхід 1: Використання автентифікованих ендпоїнтів

**Endpoint:** `GET /api/v4/earn/dual/orders` або аналогічні

- Отримання особистих замовлень користувача
- Парсинг типів продуктів та термінів

#### Підхід 2: Парсинг з Uni Lend rate_list

- Деякі валюти в `GET /api/v4/earn/uni/currencies/{currency}` повертають `rate_list` з різними термінами
- Використовувати це для визначення Fixed продуктів

#### Підхід 3: Ручне збирання даних

- Збір інформації з веб-інтерфейсу Gate.io Simple Earn
- Регулярне оновлення через manual JSON файл (як для MEXC)

**Рекомендація:** Спочатку реалізувати Підхід 1 (автентифіковані запити), далі додати Підхід 2 якщо недостатньо даних.

### 6.3 Mapping полів Gate.io → EarnAggregator

**Для Uni Lend (Flexible):**

| Джерело (Gate.io API) | Поле EarnAggregator | Приклад значення |
|-----------------------|---------------------|------------------|
| Генерується | `id` | `gate_flexible_BTC`, `gate_flexible_USDT` |
| `currency` | `symbol` | "BTC", "ETH", "USDT" |
| Генерується | `name` | "BTC Flexible Savings", "USDT Flexible Savings" |
| "Gate.io" | `provider` | "Gate.io" |
| `rate` × 100 | `apy` | `5.0` (якщо rate = 0.05) |
| `min_amount` | `min_amount` | `1.0`, `0.001` |
| `max_amount` або null | `max_amount` | `null` (якщо порожня строка) |
| 0 | `lock_period_days` | `0` (Flexible завжди 0) |
| "Flexible" | `product_type` | "Flexible" |
| `status == "enabled"` | `is_active` | `true` / `false` |
| "Low" | `risk_level` | "Low" |
| Весь об'єкт | `raw_data` | `{...}` |
| `https://www.gate.com/simple-earn` | `website_url` | URL на продукт |

**Для Fixed Savings:**

| Джерело | Поле EarnAggregator | Приклад значення |
|---------|---------------------|------------------|
| Генерується | `id` | `gate_fixed_BTC_30`, `gate_fixed_USDT_90` |
| `currency` | `symbol` | "BTC", "USDT" |
| Генерується | `name` | "BTC Fixed 30 days", "USDT Fixed 90 days" |
| "Gate.io" | `provider` | "Gate.io" |
| `rate` × 100 | `apy` | `6.5` (якщо rate = 0.065) |
| `min_amount` | `min_amount` | `10.0` |
| `max_amount` | `max_amount` | `null` або число |
| `days` / `lock_days` | `lock_period_days` | `30`, `60`, `90` |
| "Fixed" | `product_type` | "Fixed" |
| `status == "enabled"` | `is_active` | `true` / `false` |
| "Low" | `risk_level` | "Low" |
| Весь об'єкт | `raw_data` | `{...}` |

### 6.4 Особливості даних Gate.io

**APY формат:**

- Gate.io повертає `rate` у **десятковому** форматі: `0.05` = 5%
- Потрібна конвертація: `apy = float(rate) * 100`

**Max amount:**

- Порожня строка `""` означає **необмежено** → зберігати як `null`
- Якщо є значення → зберігати як float

**Status values:**

- `enabled`: продукт активний → `is_active = True`
- `disabled`: продукт неактивний → `is_active = False`

**Rate updates:**

- Flexible rates можуть змінюватися **щоденно**
- Fixed rates **фіксовані** на термін блокування
- Зберігати `source_updated_at` для tracking змін

### 6.5 — Ручне додавання Fixed продуктів Gate.io

Забезпечити оновлення інформації про Fixed Savings продукти при відсутності відповідного API, о аналогії з mexc.

Розміщення JSON-файлів має бути в окремій папці в головній папці біржі.

Формат назви файлу:
gate_fixed_earn_YYYY-MM-DD.json

Структура JSON
[
  {
    "exchange": "Gate.io",
    "product_type": "Fixed",
    "symbol": "USDT",
    "apy": 6.5,
    "min_amount": 10,
    "max_amount": null,
    "lock_period_days": 30,
    "status": "active",
    "last_updated": "2025-11-01T12:00:00Z"
  },
  {
    "exchange": "Gate.io",
    "product_type": "Fixed",
    "symbol": "BTC",
    "apy": 4.0,
    "min_amount": 0.001,
    "max_amount": null,
    "lock_period_days": 60,
    "status": "active",
    "last_updated": "2025-11-01T12:00:00Z"
  }
]

Процедура ручного оновлення

Відкрити сторінку Gate.io Simple Earn
.

Зібрати інформацію по активних Fixed продуктах:

токен, APY, термін блокування, мін/макс сума, статус;

Заповнити JSON за шаблоном (можна використати попередній як основу);



---

## 🔄 Нормалізація та збереження даних

### 7.1 Процес нормалізації

**Крок 1: Отримання сирих даних**

- Джерело: Gate.io API `/api/v4/earn/uni/currencies`
- Формат: JSON з полями Gate.io

**Крок 2: Валідація**

- Перевірка обов'язкових полів: currency, rate, status
- Валідація типів даних (string → float для rate та amounts)
- Перевірка статусу (тільки enabled продукти)

**Крок 3: Трансформація**

- Генерація унікального ID
- Конвертація APY: `rate` (0.05) → `apy`

### 7.2 — Алгоритм об’єднання даних (API + Manual)

Що додати:
Gate.io має два джерела:
1️⃣ API — для Flexible продуктів;
2️⃣ JSON (manual) — для Fixed продуктів.

Під час синхронізації модуль повинен:

- Спочатку отримати всі продукти з API (Flexible Savings);
- Потім імпортувати JSON для Fixed Savings;
- Об’єднати обидва списки перед збереженням у БД;
- Видалити дублікати за id (gate_flexible_*, gate_fixed_*).

Приклад послідовності у sync_products_to_db():
get_flexible_from_api()
+ get_fixed_from_json()
→ normalize()
→ save_to_db()

### 8.1 — CLI-команда для ручного імпорту

Описати інтерфейс ручного запуску імпорту для Gate.io.

### 10 — Моніторинг та логування

Що додати:

Лог-файл для імпорту:
/logs/gate_manual_loader.log

Приклад логів:
[2025-11-01 11:00:05] INFO Imported 30 products
[2025-11-01 11:00:07] WARNING Skipped invalid record line 27
[2025-11-01 11:00:08] ERROR DB upsert failed: duplicate id gate_fixed_USDT_30

Prometheus метрики:

- gate_api_calls_total
- gate_manual_import_total
- gate_products_total
- gate_manual_import_errors_total

### 11 — Оновлення Telegram бота

Додати:

додати Gate.io у список бірж:
exchanges = ["binance", "bybit", "okx", "mexc", "gate"]

У REFERRAL_URLS:
"gate": "https://www.gate.com/signup?referralCode=YOUR_REF",

У exchange_products.py:
Додати підтримку команди /all_gate_products для відображення гнучких і фіксованих продуктів.
