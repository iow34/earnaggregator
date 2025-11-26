# Технічне завдання — Інтеграція MEXC Savings (Flexible та Locked Savings) в EarnAggregator

## 🎯 Мета інтеграції

Імплементувати у **yield-data-service** інтеграцію з MEXC для отримання та синхронізації продуктів типу **Flexible Savings** та **Locked Savings** (також відомі як Simple Earn). Підтримати отримання всіх доступних продуктів для цих категорій.

### Ключові результати інтеграції:

- Отримання повного переліку активних Flexible та Locked Savings продуктів з MEXC
- Агрегація даних з усіх доступних криптовалют (BTC, ETH, USDT, SOL та інші)
- Інтеграція в існуючу архітектуру з підтримкою кешування, fallback та моніторингу
- Відображення продуктів MEXC у Telegram боті з фільтрами та сортуванням
- Монетизація через реферальну програму MEXC

---

## 📚 Джерела та документація

### 2.1 Офіційна документація MEXC

**Основні джерела:**

- **MEXC API v3 документація**: https://www.mexc.com/api-docs/spot-v3/introduction
- **MEXC API GitHub репозиторій**: https://github.com/mexcdevelop/mexc-api-sdk
- **MEXC API документація (GitHub Pages)**: https://mexcdevelop.github.io/apidocs/spot_v3_en/

**ВАЖЛИВО:** MEXC офіційно припинила підтримку V2 API. Використовувати тільки V3 API.

### 2.2 MEXC Savings — продуктова інформація

**Офіційні статті MEXC:**

- **Understanding MEXC Savings**: https://www.mexc.com/learn/article/understanding-mexc-savings/1
- **How to Participate in Staking & Earning**: https://blog.mexc.com/how-to-participant-in-staking-and-earn-by-holdings/
- **MEXC Earn продукти**: https://www.mexc.com/staking

**Ключова інформація про продукти:**

- **Flexible Savings**: немає періоду блокування, можна вивести в будь-який час, APY нижчий
- **Locked Savings** (Simple Earn): блокування на фіксований термін (7, 30, 60, 90 днів), APY вищий
- **Мінімальні суми**: варіюються по токенах (наприклад, 10 XRP, 5 CORE, 0.001 BTC)
- **Розрахунок доходу**: щоденний, формула: `Daily Yield = Amount × APY / 365`

## 🎯 Обсяги інтеграції

###  Що має бути реалізовано

**Охоплення:**
- Всі доступні токени з Flexible Savings (мінімум 25+ токенів)
- Поля: symbol (токен), APY (річна ставка), мінімальна/максимальна сума, статус

**⚠️ ВАЖЛИВО:**

Після детального аналізу офіційної документації MEXC API v3 (https://www.mexc.com/api-docs/spot-v3/) виявлено, що **MEXC НЕ надає публічного REST API для отримання списку Savings/Earn продуктів**.

**Документація MEXC API включає тільки:**

- Spot trading endpoints (ордери, баланси, історія)
- Market data endpoints (ціни, тікери, orderbook)
- Wallet endpoints (депозити, виведення, трансфери)
- Account endpoints (інформація про акаунт, комісії)

**Savings/Staking операції доступні тільки через:**

- Веб-інтерфейс MEXC: https://www.mexc.com/staking
- Мобільний додаток MEXC
- Можливо через приватний API для institutional partners

###  Альтернативні підходи до отримання даних

**Опис:**

1. **Ручне внесення базових продуктів** з веб-інтерфейсу MEXC (одноразово)
2. **Використання CoinMarketCap API** для доповнення даних APY (якщо доступно)
3. **Періодичне оновлення вручну** (наприклад, раз на тиждень)

**Переваги:**
- Легальний підхід
- Стабільність даних
- Можливість валідації
- Відповідає Terms of Service

### Структура даних для Manual Entry

**Формат для ручного внесення (JSON):**

```json
{
  "exchange": "MEXC",
  "product_type": "Flexible",
  "symbol": "BTC",
  "apy": 2.5,
  "min_amount": 0.001,
  "max_amount": null,
  "lock_period_days": 0,
  "status": "active",
  "last_updated": "2025-10-30T12:00:00Z"
}
```

**Джерела для ручного збору:**

- MEXC Staking Page: https://www.mexc.com/staking
- MEXC Support Articles: https://www.mexc.com/support
- MEXC Blog (announcements): https://blog.mexc.com/

### 6.4 Mapping полів MEXC → EarnAggregator

**Для ручного внесення даних:**

| Джерело (MEXC Web UI) | Поле EarnAggregator | Приклад значення |
|-----------------------|---------------------|------------------|
| Назва токену | `symbol` | "BTC", "ETH", "USDT" |
| APY (відсоток) | `apy` | `2.5`, `15.7` |
| Min. Amount | `min_amount` | `0.001`, `10.0` |
| Max. Amount (якщо є) | `max_amount` | `1000.0` або `null` |
| Період (днів) | `lock_period_days` | `0` (Flexible), `30` (Locked 30 days) |
| Тип | `product_type` | "Flexible", "Locked" |
| Статус | `is_active` | `true` / `false` |

**Генеровані поля:**

- `id`: `mexc_flexible_BTC` або `mexc_locked_BTC_30`
- `name`: "BTC Flexible Savings" або "BTC Locked 30 days"
- `provider`: "MEXC"
- `risk_level`: "Low" (Flexible), "Low" або "Medium" (Locked)
- `website_url`: `https://www.mexc.com/staking`

**Моніторинг змін:**

- Щотижнева перевірка MEXC API documentation на зміни
- Підписка на MEXC API Telegram Group для анонсів
- Моніторинг GitHub MEXC SDK на нові функції

---

## 🔄 Нормалізація та збереження даних

### Процес нормалізації

**Крок 1: Отримання сирих даних**

- Джерело: ручне внесення або майбутнє API
- Формат: JSON з полями MEXC

**Крок 2: Валідація**

- Перевірка обов'язкових полів: symbol, apy, product_type
- Валідація типів даних (float для APY, int для lock_period_days)
- Перевірка статусу (тільки active продукти)

**Крок 3: Трансформація**

- Генерація унікального ID
- Конвертація APY (якщо потрібно)
- Додавання метаданих (provider, website_url)
- Визначення risk_level на основі типу

**Крок 4: Збереження**

- Upsert в PostgreSQL (оновлення існуючих або створення нових)
- Збереження raw_data для аудиту
- Timestamp останнього оновлення

###  Формула конвертації APY

**Якщо APY у дробовому форматі (0.05):**

```
apy_percent = apy_decimal * 100
# Приклад: 0.05 → 5.0%
```

**Якщо APY вже у відсотках (5.0):**

```
apy_percent = apy_value
# Без змін
```

**Точність:** 1-2 знаки після коми (5.0%, 5.85%)

###  Правила для min_amount / max_amount

- **min_amount**: float або null
  - Якщо MEXC вказує "Min 0.001 BTC" → `0.001`
  - Якщо не вказано → `null`
- **max_amount**: float або null
  - Для Flexible зазвичай `null` (без ліміту)
  - Для Locked може бути ліміт: "Max 10,000 USDT" → `10000.0`

###  Генерація унікального ID

**Формат:**

- Flexible: `mexc_flexible_{symbol}`
  - Приклад: `mexc_flexible_BTC`, `mexc_flexible_ETH`
- Locked: `mexc_locked_{symbol}_{days}`
  - Приклад: `mexc_locked_BTC_30`, `mexc_locked_USDT_90`

**Правило унікальності:**

Один символ може мати кілька Locked продуктів з різними термінами (30, 60, 90 днів), тому термін включається в ID.

###  Збереження в БД (PostgreSQL)

**Таблиця:** `yield_products`

**SQL операція:** `INSERT ... ON CONFLICT (id) DO UPDATE`

**Поля для оновлення:**

- `apy` — може змінюватися
- `min_amount` / `max_amount` — можуть змінюватися
- `is_active` — статус продукту
- `updated_at` — timestamp останнього оновлення

**Поля, що НЕ змінюються:**

- `id` — первинний ключ
- `symbol` — символ токену
- `provider` — завжди "MEXC"
- `product_type` — тип продукту
- `lock_period_days` — термін блокування

###  Timestamp та аудит

**Обов'язкові timestamp поля:**

- `created_at` — час першого додавання продукту
- `updated_at` — час останнього оновлення
- `source_updated_at` — час оновлення даних на MEXC (якщо доступно)
- `fetched_at` — локальний timestamp отримання даних


### Архітектура інтеграції (додати після “Мета інтеграції”)

Що додати:

Структуру модуля mexc:

yield-data-service/app/services/exchanges/mexc/
├── __init__.py
├── service.py          # бізнес-логіка ручного додавання продуктів
├── manual_loader.py    # новий модуль для ручного імпорту JSON
├── models.py           # Pydantic моделі для валідації ручних даних
└── templates/          # JSON-шаблони прикладів продуктів

Призначення компонентів:

- service.py — імплементація бізнес-логіки збереження продуктів у БД.
- manual_loader.py — модуль для завантаження JSON-файлів з earn продуктами.
- models.py — Pydantic моделі для валідації структури кожного продукту перед збереженням.
- templates/ — приклади готових JSON-шаблонів для операторів (BTC, ETH, USDT тощо).


### Формат та процедура ручного додавання продуктів

 Місце зберігання JSON

Усі JSON-файли з продуктами MEXC зберігаються в:
/data/manual/mexc/

Кожен файл має назву у форматі:
mexc_earn_YYYY-MM-DD.json
(наприклад: mexc_earn_2025-10-30.json)

Формат JSON
[
  {
    "exchange": "MEXC",
    "product_type": "Flexible",
    "symbol": "BTC",
    "apy": 2.5,
    "min_amount": 0.001,
    "max_amount": null,
    "lock_period_days": 0,
    "status": "active",
    "last_updated": "2025-10-30T12:00:00Z"
  },
  {
    "exchange": "MEXC",
    "product_type": "Locked",
    "symbol": "USDT",
    "apy": 6.0,
    "min_amount": 10.0,
    "max_amount": 5000.0,
    "lock_period_days": 30,
    "status": "active",
    "last_updated": "2025-10-30T12:00:00Z"
  }
]

Кроки оператора при оновленні даних (раз на тиждень / місяць):

1. Перейти на сторінку MEXC Earn
2. Зібрати актуальні дані: символ, APY, мін/макс суми, термін, статус.
3. Заповнити JSON-файл за шаблоном.
4. Розмістити файл у /data/manual/mexc/.
5. Виконати команду:
python manual_loader.py --exchange mexc --file /data/manual/mexc/mexc_earn_YYYY-MM-DD.json


### Опис логіки збереження в БД

Алгоритм оновлення:
- Валідувати JSON через модель MEXCProductModel.

Для кожного продукту:

- Перевірити наявність id у таблиці yield_products.
- Якщо існує — оновити поля apy, is_active, updated_at.
- Якщо не існує — вставити новий запис.
- Логувати результат у mexc_loader.log.

Опис SQL-логіки:
INSERT INTO yield_products (id, symbol, name, provider, apy, min_amount, max_amount,
                            lock_period_days, product_type, is_active, risk_level, website_url, raw_data, created_at, updated_at)
VALUES (...)
ON CONFLICT (id) DO UPDATE
SET apy = EXCLUDED.apy,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();


### Опис CLI-команди для ручного імпорту

Структура команди:
python manage.py import_manual_products --exchange mexc --file ./data/manual/mexc/mexc_earn_latest.json

Параметри:
| Параметр          | Опис                       | Обов’язковий |
| ----------------- | -------------------------- | ------------ |
| `--exchange`      | Назва біржі                | ✅            |
| `--file`          | Шлях до JSON-файлу         | ✅            |
| `--validate-only` | Перевірити без запису в БД | ❌            |


### Моніторинг та логування

Файл логів:

Шлях: /logs/mexc_loader.log

Формат:
[2025-11-05 12:00:01] INFO Imported 50 products (updated: 10, new: 40)
[2025-11-05 12:00:02] WARNING Skipped invalid entry at line 32
[2025-11-05 12:00:03] ERROR Failed to write to DB: duplicate key

Моніторинг у Prometheus (опціонально):

- Метрика: mexc_manual_import_total
- Метрика: mexc_manual_import_errors_total
- Метрика: mexc_products_total


### Оновлення Telegram бота

В main_menu.py додати MEXC у список exchanges = ["binance", "bybit", "okx", "mexc"].

В REFERRAL_URLS додати:
"mexc": "https://www.mexc.com/register?inviteCode=YOUR_REF",

У exchange_products.py — підтримати команду /all_mexc_products.