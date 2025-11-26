# 🔧 Технічне завдання на інтеграцію Earn продуктів біржі Kraken в EarnAggregator

## 🏗️ Загальна інформація про інтеграцію

### Мета інтеграції:
- Інтегрувати дані про Earn продукти з біржі Kraken в систему EarnAggregator.
- Забезпечити агрегацію Flexible та Fixed продуктів з нормалізацією до єдиного формату.
- Підтримати монетизацію через реферальні посилання Kraken.
- Інтеграція повинна відповідати загальній архітектурі проекту: модульність, кешування в Redis, зберігання в PostgreSQL, REST API на FastAPI, Telegram бот на Aiogram 3.x.

### Джерела даних:
- Офіційна API документація Kraken: https://docs.kraken.com/api/docs/guides/spot-rest-earn.
- Основні ендпоінти для отримання продуктів: GET /private/Earn/Strategies для списку стратегій, GET /private/Earn/Allocations для алокацій.

### Вимоги до інтеграції:
- Використовувати тільки офіційне API Kraken.
- Обробляти аутентифікацію з API key та secret.
- Дотримуватися rate limits: 2 запити на секунду для private ендпоінтів.
- Реалізувати graceful degradation: при помилках API використовувати кеш або БД.
- Нормалізувати дані до стандарту EarnAggregator (обов'язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level).

---

## 📊 Аналіз API біржі Kraken

### Основні ендпоінти для Earn продуктів:
- **GET /private/Earn/Strategies**: Отримання списку Earn стратегій.
  - Базовий URL: https://api.kraken.com.
  - Параметри запиту:
    - asset (string, optional): Фільтр по ассету (наприклад, "ETH").
    - lock_type (string, optional): Фільтр за типом (flexible, bonded).
    - cursor (string, optional): Для пагінації.
    - limit (integer, optional): Кількість результатів (default 100).
  - Відповідь: JSON з result.strategies - масив об'єктів з полями id, asset, rate (APY як string), issuing_asset (якщо є), min_amount (string), max_amount (string, або unlimited), lock_type (flexible або bonded), duration (для bonded - кількість днів), can_allocate (boolean), allocation_restriction_info (якщо обмежено).
  - Flexible продукти: lock_type = "flexible", duration = 0.
  - Fixed продукти: lock_type = "bonded", duration вказує термін (наприклад, "28" днів).
  - APY: rate як string (наприклад, "0.04" для 4%), може бути variable.

- **GET /private/Earn/Allocations**: Отримання поточних алокацій (для перевірки статусу, optional для інтеграції).

### Аутентифікація:
- Обов'язкова для private ендпоінтів: API key, secret.
- Заголовки: API-Key, API-Sign (HMAC-SHA512 підпис), Content-Type: application/x-www-form-urlencoded.
- Підпис генерується з nonce + URI path + SHA256(nonce + POST data) + base64-decode(secret).
- Nonce: Зростаюче число, часто millisecond timestamp.

### Rate limits та обмеження:
- Private endpoints: Tier-based, базовий - 2 calls/sec, вищі tiers до 20/sec.
- Рекомендовано моніторити помилки 429 та використовувати exponential backoff.
- Rate limits базуються на tier аккаунта: для базового tier - 2 запити на секунду, але з decay (зменшенням) при перевищенні; рекомендовано queueing запитів та моніторинг помилок 429. На форумах (GitHub issues CCXT) відзначають, що private endpoints мають ledger-based limits (points system), де Earn/Strategies коштує 2 points.

### Формат відповіді та помилки:
- Успішна відповідь: error = [], result = об'єкт з даними.
- Помилки: error масив з кодами (наприклад, "EAPI:Invalid nonce", "EGeneral:Permission denied").
- Поширені помилки: неправильний nonce, invalid signature, rate limit exceeded.
-У відповіді числові поля (rate, min_amount, max_amount, duration) повертаються як string (наприклад, "0.04", "28"); потрібно парсити до float/int під час нормалізації. Якщо max_amount = "unlimited", встановити null.
- Пагінація: Якщо стратегій > limit (default 100), використовувати cursor з відповіді для наступних запитів; ігнорування призведе до неповного списку.
- Додаткові поля: rate_type (fixed або variable); для variable - rate є estimate, може змінюватися.

---

## ⚠️ Нюанси інтеграції з Kraken API

На основі аналізу документації та обговорень на спеціалізованих форумах (Stack Overflow, GitHub issues для python-kraken-sdk, CCXT, Reddit r/Kraken, r/KrakenSupport, r/cryptocurrency):

- **Проблеми з nonce**: Nonce мусить бути строго зростаючим і унікальним; рекомендовано використовувати millisecond timestamp, але уникати дублів при швидких запитах. На GitHub issues CCXT згадується, що помилки "EAPI:Invalid nonce" виникають через несинхронізований час або race conditions; радять додавати sleep(0.1) між запитами.

- **Генерація підпису**: Помилки "EAPI:Invalid signature" через неправильне кодування POST data або path. Форуми радять строго дотримуватися документації: SHA256(nonce + POST data), потім HMAC-SHA512 з decoded secret. Тестувати в Postman перед імплементацією.

- **Rate limits**: Strict enforcement; на Reddit r/KrakenSupport користувачі скаржаться на бан за перевищення, рекомендують queueing запитів і моніторинг remaining limits у відповідях (якщо доступно).

- **Фільтри та параметри**: Для повного списку використовувати без asset; якщо asset вказано, фільтрує по ньому. На форумах відзначають, що can_allocate = false для обмежених регіонів або tier; ігнорувати такі стратегії.

- **Обробка variable APY**: Rate може бути "variable"; форуми радять брати поточне значення, але моніторити зміни, оскільки staking rates fluctuate.

- **Статуси та доступність**: Тільки стратегії з can_allocate = true вважати активними. На GitHub issues python-kraken-sdk згадується, що для Earn потрібні спеціальні permissions в API key (Earn allocate/deallocate).

- **Помилки аутентифікації**: "EGeneral:Permission denied" якщо key без Earn прав; радять створювати key з "Earn" permissions.

- **Retry logic**: Exponential backoff для 429, 5xx помилок; на Stack Overflow обговорюють, що Kraken API може повертати тимчасові помилки через maintenance.

- **Тестування**: Рекомендовано використовувати test accounts або minimal queries; Kraken не має sandbox для Earn, тому тестувати на live з small data. На Reddit r/cryptocurrency радять CCXT для prototyping, але для custom - handle pagination з cursor.

- **Інші поради**: На GitHub issues згадують безпечне зберігання secret; уникати hardcoding. Для staking rewards sync (як в tax tools) - handle missing allocations, але для products focus on strategies.
- Пагінація з cursor: На Stack Overflow та GitHub issues python-kraken-sdk рекомендують loop з cursor, поки не буде порожньо, бо Earn стратегії можуть перевищувати 100 (для багатьох assets). Ігнорування cursor призводить до неповних даних.

---

## 📊 Правила нормалізації даних

- **Типи продуктів**:
  - Flexible: Якщо lock_type = "flexible" та duration = 0.
  - Fixed: Якщо lock_type = "bonded" та duration > 0 (lock_period_days = int(duration)).
  
- **APY**:
  - Брати rate як float (парсити string), з 2-4 знаками; якщо variable, використовувати поточне значення.
  - Перетворювати до річного формату.
  - Якщо rate_type = "variable", додати note в description ("Variable rate, current estimate"); парсити rate до float, з fallback 0.0 якщо порожнє.

- **Суми**:
  - min_amount: Парсити string до float.
  - max_amount: Парсити string до float, або null якщо "unlimited".
  - Якщо max_amount = "unlimited", встановити null; парсити string до float з try-except для помилок (наприклад, нечислові значення - логувати та ігнорувати продукт).

- **Статус**:
  - is_active = True тільки якщо can_allocate = true.
  - Ігнорувати обмежені (allocation_restriction_info вказує причини як Tier або Geo).

- **Ризик**:
  - Low для staking на Kraken (як centralized, insured), Medium для volatile assets.
  - Уточнення: Low для centralized staking (як на Kraken з insurance), але High для assets з slashing risks (наприклад, DOT); визначати за asset (stablecoins=Low, altcoins=Medium/High).

- **Інші поля**:
  - id: "kraken_" + lock_type + "_" + id.
  - symbol: asset.
  - name: asset + " " + lock_type.capitalize() + " Staking" (додати duration для bonded).
  - provider: "Kraken".
  - description: З issuing_asset якщо є.
  - website_url: "https://www.kraken.com/earn".
  - raw_data: Зберегти повний об'єкт для діагностики.

- **Валідація**: Перевіряти обов'язкові поля; видаляти невалідні продукти; парсити string до float/int з помилками.

---

## 📁 Структура модулів для Kraken

- Шлях: yield-data-service/app/services/exchanges/kraken/
  - __init__.py: Імпорти модулів.
  - api.py: API клієнт з методами для flexible/bonded/earn продуктів.
  - service.py: Бізнес-логіка, кешування, синхронізація з БД.
  - models.py (опціонально): Pydantic моделі для відповідей.

---

## 🚀 Покрокова інструкція інтеграції

### Крок 1: Підготовка
- Ознайомитися з документацією Kraken API для Earn.
- Зареєструвати API key з правами на Earn (allocate/deallocate).
- Створити директорію: yield-data-service/app/services/exchanges/kraken.
- Додати ключі до .env: KRAKEN_API_KEY, KRAKEN_API_SECRET.

### Крок 2: Реалізація API клієнта (api.py)
- Успадкувати від BaseExchange.
- Реалізувати аутентифікацію: генерувати headers з API-Key, API-Sign (HMAC-SHA512), nonce.
- Методи: get_flexible_savings_products (lock_type="flexible"), get_locked_savings_products (lock_type="bonded"), get_earn_products (агрегація), get_earn_products_by_asset (з asset).
- У методах додати pagination loop: Використовувати cursor для повного отримання списку, ітеративно запитуючи до порожньої відповіді.
- Обробити form-data для POST (Kraken використовує x-www-form-urlencoded для params).
- Обробити POST-form params та парсинг result.strategies.

### Крок 3: Реалізація сервісу (service.py)
- Успадкувати від BaseExchangeService.
- Ініціалізувати API клієнт з ключів з settings.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Додати retry з exponential backoff.

Метод sync_products_to_db повинен оркеструвати процес нормалізації та збереження в PostgreSQL. Ось детальний покроковий опис логіки (без прикладів коду, як просив у стилі):

Отримання даних з API: Викликати get_products_from_api (або з кешу, якщо доступно) для отримання сирого списку стратегій. Якщо asset вказано, фільтрувати по ньому; обробити pagination з cursor для повного списку.
Фільтрація активних продуктів: Ітеративно пройти по списку стратегій і відфільтрувати тільки ті, де can_allocate == true (активні та доступні). Ігнорувати з restriction_info (наприклад, geo або tier обмеження).
Нормалізація кожного продукту:

Створити словник з обов'язковими полями (id, symbol, name, provider тощо) за правилами нормалізації.
Парсити string до float для apy (rate), min_amount, max_amount (якщо "unlimited" - null); до int для lock_period_days (duration).
Якщо rate_type = "variable", додати в description "Variable APY".
Встановити product_type: "Flexible" для flexible, "Fixed" для bonded.
Додати raw_data як JSONB для діагностики.

Підготовка до вставки в БД:

Використовувати SQLAlchemy або psycopg2 для з'єднання з PostgreSQL (таблиця yield_products).
Перевірити існування продукту за id: Якщо існує, оновити поля (UPDATE query з WHERE id = ... для актуалізації APY тощо).


Транзакційна вставка:

Використовувати транзакцію (with session.begin()): Для кожного нормалізованого продукту виконати UPSERT (INSERT ... ON CONFLICT DO UPDATE) для уникнення дублів.
Поля для збереження: id (PRIMARY KEY), symbol (VARCHAR), name (VARCHAR), provider (VARCHAR), apy (NUMERIC), min_amount (NUMERIC або NULL), max_amount (NUMERIC або NULL), lock_period_days (INTEGER), product_type (VARCHAR), is_active (BOOLEAN), risk_level (VARCHAR), description (TEXT), website_url (VARCHAR), raw_data (JSONB).
Після вставки, комітити транзакцію.


Обробка помилок та логування:

Якщо помилка вставки (наприклад, невалідні дані або constraint violation), rollback транзакції та логувати (logger.error з деталями продукту).
Повернути словник з результатом: {"synced": кількість_продуктів, "updated": кількість_оновлених, "errors": список_помилок}.

Оновлення кешу після синхронізації: Після успішної вставки, оновити Redis-кеш з новими даними для швидкого доступу; інвалідувати старий кеш якщо APY змінився.

### Крок 4: Реалізація моделей (models.py) - опціонально
- Моделі для Flexible та Bonded продуктів з полями з API.

### Крок 5: Налаштування імпортів (__init__.py)
- Експортувати класи API, Service, моделі.

### Крок 6: Реєстрація біржі в системі
- Додати до aggregation_service.py: DataSource.API_KRAKEN, fallback_chain, _get_exchange_data.
- Додати до registry.py: AVAILABLE_EXCHANGES = ["binance", ..., "kraken"].
- Додати до routes.py: Валідація в get_exchanges та get_exchanges_popular; оновити provider_mapping = {'kraken': 'Kraken'}.
- Додати ендпоінт для синхронізації: POST /api/v1/kraken/sync, який викликає sync_products_to_db.

### Крок 7: Оновлення конфігурації
- Додати до config.py: kraken_api_key, kraken_api_secret.
- Додати до docker-compose.yml: environment для KRAKEN_*.
- У .env додати KRAKEN_API_SECRET=your_secret

---

## 📱 Інтеграція з Telegram ботом

- Додати до provider_mapping в filtered_products.py: {'kraken': 'Kraken'}.
- Оновити списки бірж: AVAILABLE_EXCHANGES, exchanges в main_menu.py, callback_handlers.py.
- Додати реферальне посилання до REFERRAL_URLS: "kraken": "https://www.kraken.com/ref/YOUR_REF".
- Додати методи до api_client.py: get_kraken_products, get_kraken_popular.
- Додати команду /all_kraken_products, фільтри, сортування, пагінацію.

---

## ✅ Валідація та тестування

- Unit тести: Підключення, отримання flexible/bonded продуктів, нормалізація.
- Інтеграційні: Curl для /api/v1/exchanges?exchange=kraken, /api/v1/kraken/test.
- Функціональні: Команди в боту, перевірка таблиць, фільтрів.
- БД: SQL запити на count по provider='Kraken'.

---

## 📊 Моніторинг та підтримка

- Додати метрики Prometheus: EXTERNAL_API_CALLS, API_RESPONSE_TIME для "kraken".
- Логування: Інфо про кількість продуктів, помилки з exc_info.
- Обробка помилок: Graceful degradation, retry.
- Регулярні завдання: Щоденна синхронізація, моніторинг змін API.