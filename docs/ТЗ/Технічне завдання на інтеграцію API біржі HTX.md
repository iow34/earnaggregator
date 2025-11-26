# 🔧 Технічне завдання на інтеграцію Earn продуктів біржі HTX в EarnAggregator

## 🏗️ Загальна інформація про інтеграцію

### Мета інтеграції:
- Інтегрувати дані про Earn продукти (Savings) з біржі HTX в систему EarnAggregator.
- Забезпечити агрегацію Flexible та Fixed продуктів з нормалізацією до єдиного формату.
- Підтримати монетизацію через реферальні посилання HTX.
- Інтеграція повинна відповідати загальній архітектурі проекту: модульність, кешування в Redis, зберігання в PostgreSQL, REST API на FastAPI, Telegram бот на Aiogram 3.x.

### Джерела даних:
- Офіційна API документація HTX: https://www.htx.com/en-us/opend/newApiPages.
- Основний ендпоінт для отримання продуктів: GET /v1/dw/savings/products/get.

### Вимоги до інтеграції:
- Використовувати тільки офіційне API HTX.
- Обробляти аутентифікацію з API key та secret.
- Дотримуватися rate limits: 100 запитів на 10 секунд для підписаних ендпоінтів.
- Реалізувати graceful degradation: при помилках API використовувати кеш або БД.
- Нормалізувати дані до стандарту EarnAggregator (обов'язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level).

---

## 📊 Аналіз API біржі HTX

### Основні ендпоінти для Earn продуктів:
- **GET /v1/dw/savings/products/get**: Отримання списку Savings продуктів.
  - Базовий URL: https://api.htx.com.
  - Параметри запиту:
    - currency (string, optional): Фільтр по валюті (наприклад, "BTC").
    - type (string, optional): Фільтр за типом (flexible або fixed).
  - Відповідь: JSON з data - масив об'єктів з полями productId, currency, apr (string), minPurchaseAmount (string), maxPurchaseAmount (string), status (ONLINE або OFFLINE), type (FIXED або FLEXIBLE), term (для FIXED - кількість днів як string), redeemType (IMMEDIATE або NEXT_DAY).
  - Flexible продукти: type = "FLEXIBLE", term = "0".
  - Fixed продукти: type = "FIXED", term вказує термін (наприклад, "30" для 30 днів).
  - APY: apr як string (наприклад, "0.02" для 2%).

### Аутентифікація:
- Обов'язкова для ендпоінтів: API key, secret.
- Заголовки: AccessKeyId, SignatureMethod (HmacSHA256), SignatureVersion (2), Timestamp (UTC), Signature (підпис).
- Підпис генерується з рядка: method + \n + host + \n + path + \n + sorted_params.

### Rate limits та обмеження:
- Підписані ендпоінти: 100 запитів на 10 секунд.
- Рекомендовано реалізувати exponential backoff для помилок 429 Too Many Requests.

### Формат відповіді та помилки:
- Успішна відповідь: status = "ok", data = масив продуктів.
- Помилки: status = "error", err-code (наприклад, "base-param-required" для відсутніх параметрів), err-msg з описом.
- Поширені помилки: invalid signature, invalid timestamp, rate limit exceeded.

---

## ⚠️ Нюанси інтеграції з HTX API

На основі аналізу документації та обговорень на спеціалізованих форумах (Stack Overflow, GitHub issues для CCXT, Reddit r/Huobi, r/cryptocurrency, r/HTXexchange):

- **Проблеми з генерацією підпису**: Часті помилки "invalid signature" через неправильне сортування параметрів або формат рядка. Рекомендовано строго дотримуватися формату: method\nhost\npath\nsorted_params (без пробілів, URL-encoded). На GitHub issues CCXT та Stack Overflow радять тестувати підпис у Postman; уникати відмінностей у платформах (наприклад, Java vs Python може впливати на encoding).

- **Timestamp issues**: Timestamp мусить бути в UTC і близьким до серверного часу (±30 сек); помилки "invalid timestamp". Форуми радять використовувати NTP для синхронізації.

- **Rate limits**: Strict enforcement; на Reddit r/Huobi користувачі рекомендують queueing запитів та моніторинг заголовків відповіді для remaining limits, бо перевищення веде до бану на 2-5 хвилин.

- **Фільтри та параметри**: Для повного списку використовувати без currency; type для розподілу FIXED/FLEXIBLE. На Stack Overflow відзначають, що status="ONLINE" для активних, але перевіряти remaining amount для доступності.

- **Обробка APY**: apr як string; форуми радять парсити до float з точністю, бо може бути variable для деяких продуктів.

- **Статуси продуктів**: Тільки status="ONLINE" вважати активними. На GitHub issues згадується, що для FIXED redeemType впливає на вилучення.

- **Помилки аутентифікації**: "api-key-format-invalid" якщо key неправильний; радять створювати separate keys для read-only.

- **Retry logic**: Exponential backoff (від 1 сек) для 429 або network errors; на Stack Overflow обговорюють тимчасові downtime API.

- **Тестування**: HTX має sandbox (api-test.htx.com); рекомендовано тестувати signed requests там. На Reddit r/cryptocurrency радять CCXT для prototyping, але custom для Earn через специфічні params.

- **Інші поради**: На GitHub згадують безпечне зберігання secret; уникати hardcoding. Для savings - handle pagination якщо продуктів багато (хоча default повертає все).

---

## 📊 Правила нормалізації даних

- **Типи продуктів**:
  - Flexible: Якщо type = "FLEXIBLE" та term = "0".
  - Fixed: Якщо type = "FIXED" та term > 0 (lock_period_days = int(term)).
  
- **APY**:
  - Брати apr як float (парсити string), з 2-4 знаками.
  - Перетворювати до річного формату.

- **Суми**:
  - min_amount: Парсити minPurchaseAmount (string) до float.
  - max_amount: Парсити maxPurchaseAmount (string) до float, або null якщо необмежено.

- **Статус**:
  - is_active = True тільки якщо status = "ONLINE".
  - Ігнорувати OFFLINE або вичерпані.

- **Ризик**:
  - Low для stablecoins, Medium для volatile assets.

- **Інші поля**:
  - id: "htx_" + type + "_" + productId.
  - symbol: currency.
  - name: currency + " " + type.capitalize() + " Savings" (додати term для FIXED).
  - provider: "HTX".
  - description: З redeemType.
  - website_url: "https://www.htx.com/earn".
  - raw_data: Зберегти повний об'єкт для діагностики.

- **Валідація**: Перевіряти обов'язкові поля; видаляти невалідні продукти; парсити string до float/int з помилками.

---

## 📁 Структура модулів для HTX

- Шлях: yield-data-service/app/services/exchanges/htx/
  - __init__.py: Імпорти модулів.
  - api.py: API клієнт з методами для flexible/fixed/earn продуктів.
  - service.py: Бізнес-логіка, кешування, синхронізація з БД.
  - models.py (опціонально): Pydantic моделі для відповідей.

---

## 🚀 Покрокова інструкція інтеграції

### Крок 1: Підготовка
- Ознайомитися з документацією HTX API для Savings.
- Зареєструвати API key з правами на read.
- Створити директорію: yield-data-service/app/services/exchanges/htx.
- Додати ключі до .env: HTX_API_KEY, HTX_API_SECRET.

### Крок 2: Реалізація API клієнта (api.py)
- Успадкувати від BaseExchange.
- Реалізувати аутентифікацію: генерувати params з AccessKeyId, SignatureMethod, Timestamp, Signature.
- Методи: get_flexible_savings_products (type="FLEXIBLE"), get_locked_savings_products (type="FIXED"), get_earn_products (агрегація), get_earn_products_by_asset (з currency).
- Обробити sorted params та парсинг data.
- HTX API може повертати не всі продукти в одному запиті.
- Якщо у відповіді є поле nextId, потрібно виконати повторний запит із параметром id=nextId до отримання всіх сторінок.
- При обробці великої кількості продуктів (>500) додати асинхронну чергу запитів через aiohttp.

### Крок 3: Реалізація сервісу (service.py)
- Успадкувати від BaseExchangeService.
- Ініціалізувати API клієнт з ключів з settings.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Додати retry з exponential backoff.
- При статусі відповіді "status": "error" виконати retry через exponential backoff (1 → 2 → 4 → 8 секунд, максимум 4 спроби).
- Якщо код "429" — додати затримку не менше 10 секунд перед наступним запитом.
- Якщо "invalid timestamp" — повторити запит із оновленим часом.
- У випадку "invalid signature" — логувати запит та зберігати тіло у /logs/htx_failed_signature.log.

### Крок 4: Реалізація моделей (models.py) - опціонально
- Моделі для Flexible та Fixed продуктів з полями з API.

### Крок 5: Налаштування імпортів (__init__.py)
- Експортувати класи API, Service, моделі.

### Крок 6: Реєстрація біржі в системі
- Додати до aggregation_service.py: DataSource.API_HTX, fallback_chain, _get_exchange_data.
- Додати до registry.py: AVAILABLE_EXCHANGES = ["binance", ..., "htx"].
- Додати до routes.py: Валідація в get_exchanges та get_exchanges_popular; оновити provider_mapping = {'htx': 'HTX'}.

### Крок 7: Оновлення конфігурації
- Додати до config.py: htx_api_key, htx_api_secret.
- Додати до docker-compose.yml: environment для HTX_*.

---

## 📱 Інтеграція з Telegram ботом

- Додати до provider_mapping в filtered_products.py: {'htx': 'HTX'}.
- Оновити списки бірж: AVAILABLE_EXCHANGES, exchanges в main_menu.py, callback_handlers.py.
- Додати реферальне посилання до REFERRAL_URLS: "htx": "https://www.htx.com/ref/YOUR_REF".
- Додати методи до api_client.py: get_htx_products, get_htx_popular.
- Бот автоматично підтримає /all_htx_products, фільтри, сортування, пагінацію.

---

## ✅ Валідація та тестування

- Unit тести: Підключення, отримання flexible/fixed продуктів, нормалізація.
- Інтеграційні: Curl для /api/v1/exchanges?exchange=htx, /api/v1/htx/test.
- Функціональні: Команди в боту, перевірка таблиць, фільтрів.
- БД: SQL запити на count по provider='HTX'.

---

## 📊 Моніторинг та підтримка

- Додати метрики Prometheus: EXTERNAL_API_CALLS, API_RESPONSE_TIME для "htx".
- Логування: Інфо про кількість продуктів, помилки з exc_info.
- Обробка помилок: Graceful degradation, retry.
- Регулярні завдання: Щоденна синхронізація, моніторинг змін API.