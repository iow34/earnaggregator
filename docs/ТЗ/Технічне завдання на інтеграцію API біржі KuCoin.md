# 🔧 Технічне завдання на інтеграцію Earn продуктів біржі KuCoin в EarnAggregator

## 🏗️ Загальна інформація про інтеграцію

### Мета інтеграції:
- Інтегрувати дані про Earn продукти (Savings) з біржі KuCoin в систему EarnAggregator.
- Забезпечити агрегацію Flexible та Fixed продуктів з нормалізацією до єдиного формату.
- Підтримати монетизацію через реферальні посилання KuCoin.
- Інтеграція повинна відповідати загальній архітектурі проекту: модульність, кешування в Redis, зберігання в PostgreSQL, REST API на FastAPI, Telegram бот на Aiogram 3.x.

### Джерела даних:
- Офіційна API документація KuCoin: https://www.kucoin.com/docs-new/rest/earn/get-savings-products.
- Основний ендпоінт для отримання продуктів: GET /api/v3/earn/savings/products/current.

### Вимоги до інтеграції:
- Використовувати тільки офіційне API KuCoin.
- Обробляти аутентифікацію з API key, secret та passphrase.
- Дотримуватися rate limits: 10 запитів на секунду для підписаних ендпоінтів.
- Реалізувати graceful degradation: при помилках API використовувати кеш або БД.
- Нормалізувати дані до стандарту EarnAggregator (обов'язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level).

---

## 📊 Аналіз API біржі KuCoin

### Основні ендпоінти для Earn продуктів:
- **GET /api/v3/earn/savings/products/current**: Отримання списку поточних Savings продуктів.
  - Базовий URL: https://api.kucoin.com.
  - Параметри запиту:
    - currency (string, optional): Фільтр по валюті (наприклад, "BTC").
    - fundsType (string, optional): Фільтр за типом (FLEXIBLE або FIXED).
  - Відповідь: JSON з data - масив об'єктів з полями productId, currency, apr (string), minAmount (string), maxAmount (string), issueAmount (string), remainingAmount (string), status (1 - активний, 0 - неактивний), productType (FIXED або FLEXIBLE), term (для FIXED - кількість днів як string), redeemType (AUTO або MANUAL), advanceRedeemSupport (true/false).
  - Flexible продукти: productType = "FLEXIBLE", term = "0".
  - Fixed продукти: productType = "FIXED", term вказує термін (наприклад, "7" для 7 днів).
  - APY: apr як string (наприклад, "0.05" для 5%).

### Аутентифікація:
- Обов'язкова для ендпоінтів: API key, secret, passphrase.
- Заголовки: KC-API-KEY, KC-API-SIGN (HMAC-SHA256 підпис), KC-API-TIMESTAMP (мілісекунди), KC-API-PASSPHRASE, KC-API-KEY-VERSION (2), Content-Type: application/json.
- Підпис генерується з рядка: timestamp + method + endpoint + query_string + body (якщо є).

### Rate limits та обмеження:
- Підписані ендпоінти: 10 запитів на секунду.
- Рекомендовано реалізувати exponential backoff для помилок 429.

### Формат відповіді та помилки:
- Успішна відповідь: code = "200000", msg = "success", data = масив продуктів.
- Помилки: code (наприклад, "200004" для недостатньо коштів, але для API - "400100" для параметрів), msg з описом.
- Поширені помилки: неправильний підпис (invalid signature), invalid timestamp, rate limit exceeded.

---

## ⚠️ Нюанси інтеграції з KuCoin API

На основі аналізу документації та обговорень на спеціалізованих форумах (Stack Overflow, GitHub issues для python-kucoin, CCXT, Reddit r/kucoin, r/KuCoinSupport):

- **Проблеми з генерацією підпису**: Часті помилки "invalid signature" через неправильне формування рядка для HMAC-SHA256. Рекомендовано строго дотримуватися формату: timestamp + метод + ендпоінт + query (сортований, без пробілів) + body. На GitHub issues CCXT та Stack Overflow радять тестувати в Postman з environment variables для timestamp та sign; уникати відмінностей в кодуванні (base64 для passphrase).

- **Passphrase та версія**: Обов'язковий KC-API-PASSPHRASE (SHA256 з passphrase); використовувати KC-API-KEY-VERSION=2. На форумах (Reddit r/kucoin) згадується, що без версії 2 аутентифікація не проходить для нових ендпоінтів.

- **Rate limits**: Strict 10/sec; на GitHub issues freqtrade користувачі рекомендують додавати затримки (sleep) та моніторити заголовки для remaining limits, бо перевищення веде до тимчасового бану.

- **Фільтри та параметри**: Для всіх продуктів використовувати без currency; fundsType для розподілу FIXED/FLEXIBLE. На Stack Overflow відзначають, що "remainingAmount" корисний для перевірки доступності, але тільки для активних (status=1).

- **Обробка APY**: apr як string; форуми радять парсити до float з точністю, бо може бути "0.0000" для неактивних.

- **Статуси продуктів**: Тільки status=1 вважати активними; redeemType впливає на вилучення (AUTO для flexible). На Reddit r/kucoin обговорюють, що FIXED продукти можуть мати advanceRedeemSupport для раннього виведення.

- **Помилки аутентифікації**: "Invalid KC-API-KEY" або timestamp issues (±5 сек); радять синхронізувати час з NTP.

- **Retry logic**: Exponential backoff (від 1 сек) для 429 або 5xx; на Stack Overflow згадують тимчасові помилки через навантаження сервера.

- **Тестування**: KuCoin має sandbox (api-sandbox.kucoin.com); рекомендовано тестувати signed requests там перед live. На GitHub python-kucoin радять використовувати CCXT для прототипу, але custom для Earn через специфічні ендпоінти.

- **Інші поради**: На Reddit r/kucoin згадують безпечне зберігання secret; уникати публічних репозиторіїв. Для lending/savings (Earn) - handle incomplete docs, бо ендпоінти можуть змінюватися; моніторити changelog.

---

## 📊 Правила нормалізації даних

- **Типи продуктів**:
  - Flexible: Якщо productType = "FLEXIBLE" та term = "0".
  - Fixed: Якщо productType = "FIXED" та term > 0 (lock_period_days = int(term)).
  
- **APY**:
  - Брати apr як float (парсити string), з 2-4 знаками.
  - Перетворювати до річного формату.

- **Суми**:
  - min_amount: Парсити minAmount (string) до float.
  - max_amount: Парсити maxAmount (string) до float, або null якщо не вказано.

- **Статус**:
  - is_active = True тільки якщо status = "1" та remainingAmount > 0.
  - Ігнорувати неактивні (status=0) або вичерпані.

- **Ризик**:
  - Low для stablecoins (USDT тощо), Medium для volatile assets.

- **Інші поля**:
  - id: "kucoin_" + productType + "_" + productId.
  - symbol: currency.
  - name: currency + " " + productType.capitalize() + " Savings" (додати term для FIXED).
  - provider: "KuCoin".
  - description: З redeemType та advanceRedeemSupport.
  - website_url: "https://www.kucoin.com/earn".
  - raw_data: Зберегти повний об'єкт для діагностики.

- **Валідація**: Перевіряти обов'язкові поля; видаляти невалідні продукти; парсити string до float/int з помилками.

---

## 📁 Структура модулів для KuCoin

- Шлях: yield-data-service/app/services/exchanges/kucoin/
  - __init__.py: Імпорти модулів.
  - api.py: API клієнт з методами для flexible/fixed/earn продуктів.
  - service.py: Бізнес-логіка, кешування, синхронізація з БД.
  - models.py (опціонально): Pydantic моделі для відповідей.

Стандартна структура відповіді для продукта KuCoin, приклад:
{
    "code": "200000",
    "data": [
        {
            "id": "2172",
            "currency": "BTC",
            "category": "DEMAND",
            "type": "DEMAND",
            "precision": 8,
            "productUpperLimit": "480",
            "productRemainAmount": "132.36153083",
            "userUpperLimit": "20",
            "userLowerLimit": "0.01",
            "redeemPeriod": 0,
            "lockStartTime": 1644807600000,
            "lockEndTime": null,
            "applyStartTime": 1644807600000,
            "applyEndTime": null,
            "returnRate": "0.00047208",
            "incomeCurrency": "BTC",
            "earlyRedeemSupported": 0,
            "status": "ONGOING",
            "redeemType": "MANUAL",
            "incomeReleaseType": "DAILY",
            "interestDate": 1729267200000,
            "duration": 0,
            "newUserOnly": 0
        }
    ]
}
---

## 🚀 Покрокова інструкція інтеграції

### Крок 1: Підготовка
- Ознайомитися з документацією KuCoin API для Earn.
- Зареєструвати API key з правами на Earn (read-only).
- Створити директорію: yield-data-service/app/services/exchanges/kucoin.
- Додати ключі до .env: KUCOIN_API_KEY, KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE.

### Крок 2: Реалізація API клієнта (api.py)
- Успадкувати від BaseExchange.
- Реалізувати аутентифікацію: генерувати headers з KC-API-KEY, KC-API-SIGN (HMAC-SHA256), KC-API-TIMESTAMP, KC-API-PASSPHRASE, KC-API-KEY-VERSION=2.
- Методи: get_flexible_savings_products (fundsType="FLEXIBLE"), get_locked_savings_products (fundsType="FIXED"), get_earn_products (агрегація), get_earn_products_by_asset (з currency).
- Обробити query params та парсинг data.

Верифікація коректності підпису запитів

- Перед запуском інтеграції протестувати підписані запити через Postman або curl:
- Згенерувати підпис (HMAC-SHA256) з полями timestamp + method + endpoint + query + body.
- Перевірити, що KC-API-KEY-VERSION=2 обов’язково додається в заголовки.
- Звірити результат із “Signature Example” у документації KuCoin.
- При виникненні помилки invalid KC-API-SIGN — перевірити timestamp (різниця з сервером ≤ 5 секунд).

### Крок 3: Реалізація сервісу (service.py)
- Успадкувати від BaseExchangeService.
- Ініціалізувати API клієнт з ключів з settings.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Додати retry з exponential backoff.

Обробка API-відповідей KuCoin

- KuCoin може повертати порожній data=[] навіть при активних продуктах — у такому випадку слід виконати повторний запит через 3–5 секунд.
- Перевіряти поле status — тільки 1 вважається активним продуктом.
- Для деяких валют remainingAmount може бути null — у таких випадках продукт позначати is_active = True, якщо status = 1.
- Значення apr (APY) — рядкове, тому потрібно приводити до float з 4 десятковими знаками.

Додати валідацію:
- apy > 0
- symbol не порожній
- minAmount > 0

### Крок 4: Реалізація моделей (models.py) - опціонально
- Моделі для Flexible та Fixed продуктів з полями з API.

### Крок 5: Налаштування імпортів (__init__.py)
- Експортувати класи API, Service, моделі.

### Крок 6: Реєстрація біржі в системі
- Додати до aggregation_service.py: DataSource.API_KUCOIN, fallback_chain, _get_exchange_data.
- Додати до registry.py: AVAILABLE_EXCHANGES = ["binance", ..., "kucoin"].
- Додати до routes.py: Валідація в get_exchanges та get_exchanges_popular; оновити provider_mapping = {'kucoin': 'KuCoin'}.

### Крок 7: Оновлення конфігурації
- Додати до config.py: kucoin_api_key, kucoin_api_secret, kucoin_api_passphrase.
- Додати до docker-compose.yml: environment для KUCOIN_*.

---

## 📱 Інтеграція з Telegram ботом

- Додати до provider_mapping в filtered_products.py: {'kucoin': 'KuCoin'}.
- Оновити списки бірж: AVAILABLE_EXCHANGES, exchanges в main_menu.py, callback_handlers.py.
- Додати реферальне посилання до REFERRAL_URLS: "kucoin": "https://www.kucoin.com/ref/YOUR_REF".
- Додати методи до api_client.py: get_kucoin_products, get_kucoin_popular.
- Бот автоматично підтримає /all_kucoin_products, фільтри, сортування, пагінацію.

---

## ✅ Валідація та тестування

- Unit тести: Підключення, отримання flexible/fixed продуктів, нормалізація.
- Інтеграційні: Curl для /api/v1/exchanges?exchange=kucoin, /api/v1/kucoin/test.
- Функціональні: Команди в боту, перевірка таблиць, фільтрів.
- БД: SQL запити на count по provider='KuCoin'.
- Додай перевірку у /all_kucoin_products: якщо KuCoin API тимчасово не відповідає, бот повинен відображати попередження:
⚠️ KuCoin тимчасово недоступний. Дані показано з останнього оновлення (3 години тому).
Для цього у api_client.py додати обробку status_code == 429 або 500 з fallback на кеш.

---

## 📊 Моніторинг та підтримка

- Додати метрики Prometheus: EXTERNAL_API_CALLS, API_RESPONSE_TIME для "kucoin".
- Логування: Інфо про кількість продуктів, помилки з exc_info.
- Обробка помилок: Graceful degradation, retry.
- Регулярні завдання: Щоденна синхронізація, моніторинг змін API.