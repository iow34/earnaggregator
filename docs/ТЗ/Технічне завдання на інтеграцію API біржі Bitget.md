# 🔧 Технічне завдання на інтеграцію Earn продуктів біржі Bitget в EarnAggregator

## 🏗️ Загальна інформація про інтеграцію

### Мета інтеграції:
- Інтегрувати дані про Earn продукти (Savings) з біржі Bitget в систему EarnAggregator.
- Забезпечити агрегацію Flexible та Fixed продуктів з нормалізацією до єдиного формату.
- Підтримати монетизацію через реферальні посилання Bitget.
- Інтеграція повинна відповідати загальній архітектурі проекту: модульність, кешування в Redis, зберігання в PostgreSQL, REST API на FastAPI, Telegram бот на Aiogram 3.x.

### Джерела даних:
- Офіційна API документація Bitget: https://www.bitget.com/api-doc/earn/savings/Savings-Products.
- Основний ендпоінт для отримання продуктів: GET /api/v2/earn/savings/product.

### Вимоги до інтеграції:
- Використовувати тільки офіційне API Bitget.
- Обробляти аутентифікацію з API key, secret та passphrase.
- Дотримуватися rate limits: 10 запитів на секунду на UID.
- Реалізувати graceful degradation: при помилках API використовувати кеш або БД.
- Нормалізувати дані до стандарту EarnAggregator (обов'язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level).

---

## 📊 Аналіз API біржі Bitget

### Основні ендпоінти для Earn продуктів:
- **GET /api/v2/earn/savings/product**: Отримання списку Savings продуктів.
  - Базовий URL: https://api.bitget.com.
  - Параметри запиту:
    - coin (string, optional): Фільтр по монеті (наприклад, "BTC").
    - filter (string, optional): Фільтр за статусом (available - доступні для підписки, held - утримувані, available_and_held - доступні та утримувані, all - всі, включаючи зняті).
  - Відповідь: JSON масив об'єктів з полями productId, coin, periodType (flexible або fixed), period (порожнє для flexible), apyType (single або ladder), advanceRedeem (Yes/No), settleMethod (daily/maturity), apyList (список з rateLevel, minStepVal, maxStepVal, currentApy), status (not_started, in_progress, paused, completed, sold_out, off_line), productLevel (beginner, normal, VIP).
  - Flexible продукти: periodType = "flexible", period = "".
  - Fixed продукти: periodType = "fixed", period вказує термін (наприклад, "30" для 30 днів).
  - APY: Якщо apyType = "ladder", APY tiered (залежить від суми); якщо "single" - фіксований.

### Аутентифікація:
- Обов'язкова для всіх ендпоінтів: API key, secret, passphrase.
- Заголовки: ACCESS-KEY, ACCESS-SIGN (HMAC-SHA256 підпис), ACCESS-TIMESTAMP (мілісекунди), ACCESS-PASSPHRASE, Content-Type: application/json, locale (наприклад, en-US).
- Підпис генерується з рядка: timestamp + method + path + query_string + body (якщо є).

### Rate limits та обмеження:
- 10 запитів на секунду на користувача (UID).
- Рекомендовано реалізувати exponential backoff для retry при помилках (наприклад, 429 Too Many Requests).

### Формат відповіді та помилки:
- Успішна відповідь: code = "00000", msg = "success", data = масив продуктів.
- Помилки: code (наприклад, 40001 для порожнього ACCESS-KEY), msg з описом.
- Поширені помилки: неправильний підпис (sign signature error), відсутні ключі, перевищення rate limit.

---

## ⚠️ Нюанси інтеграції з Bitget API

На основі аналізу документації та обговорень на спеціалізованих форумах (Stack Overflow, GitHub issues для CCXT, Postman community, Reddit r/CryptoIndia, r/getdelta):

- **Проблеми з генерацією підпису**: Часто виникають помилки "sign signature error" через неправильне формування рядка для HMAC-SHA256. Рекомендовано строго дотримуватися формату: timestamp + метод (GET/POST) + шлях + query (без пробілів, сортований) + body (якщо POST). На форумах радять тестувати підпис у Postman з environment variables для timestamp та sign. Уникати відмінностей у платформах (наприклад, Windows vs Linux може впливати на кодування).
  
- **Passphrase**: Обов'язковий при створенні API key; без нього аутентифікація не проходить. На GitHub issues для CCXT згадується, що passphrase потрібно вказувати окремо від secret.

- **Rate limits**: 10/sec - критичний ліміт; форуми рекомендують додавати затримки (sleep) між запитами та моніторити заголовки відповіді для remaining limits.

- **Фільтри та параметри**: Для отримання всіх продуктів використовувати filter="all" або "available". Якщо coin вказаний, фільтрує по монеті. На форумах відзначають, що "held" корисний тільки для аутентифікованих користувачів з балансом.

- **Обробка ladder APY**: Якщо apyType="ladder", APY залежить від суми (tiers в apyList). Форуми радять для нормалізації брати максимальний APY з tiers або середній, залежно від контексту; уникати ігнорування tiers, бо це може спотворювати дані.

- **Статуси продуктів**: Тільки продукти зі status="in_progress" вважати активними. Sold_out або off_line ігнорувати.

- **Помилки аутентифікації**: Часті "Access denied: sign signature" - радять перевіряти timestamp (повинен бути близьким до серверного часу, ±30 сек). Використовувати NTP для синхронізації часу.

- **Retry logic**: Exponential backoff (почати з 1 сек, подвоювати) для помилок 429 або 5xx. На Stack Overflow обговорюють, що Bitget API іноді повертає тимчасові помилки через навантаження.

- **Тестування**: Рекомендовано спочатку тестувати в sandbox (якщо доступний), але Bitget не має повного sandbox для Earn. Використовувати public endpoints для перевірки, потім signed.

- **Інші поради**: На Reddit згадують інтеграцію з ботами (наприклад, для futures, але аналогічно для Earn) - забезпечити безпечне зберігання ключів. Уникати публічних репозиторіїв з ключами.

- Обробка порожніх полів: На форумах (GitHub issues CCXT) згадується, що для flexible продуктів поля advanceRedeem та settleMethod часто порожні; рекомендовано додати fallback-логіку, щоб уникнути помилок парсингу (наприклад, if not value: value = "default").

- Парсинг string-значень: Числові поля як string можуть містити десяткові крапки або нулі (наприклад, "0.000000"); радять використовувати float(value) з try-except для уникнення ValueError.

---

## 📊 Правила нормалізації даних

- **Типи продуктів**:
  - Flexible: Якщо periodType = "flexible" та period = "".
  - Fixed: Якщо periodType = "fixed" та period > 0 (lock_period_days = int(period)).
  
- **APY**:
  - Якщо apyType = "single", брати currentApy як float.
  - Якщо "ladder", обрати максимальний currentApy з apyList (або середній, якщо tiers критичні; форуми радять max для маркетингу).
  - Перетворювати до річного формату (float з 2-4 знаками).
  - При парсингу APY та сум (min_amount, max_amount) перетворювати string на float (наприклад, float(item['currentApy'])), з обробкою помилок (якщо значення порожнє або невалідне, встановити 0.0).

- **Суми**:
  - min_amount: minStepVal з першого tier apyList (якщо ladder) або з продукту.
  - max_amount: maxStepVal з останнього tier або null, якщо необмежено.

- **Статус**:
  - is_active = True тільки якщо status = "in_progress".
  - Ігнорувати неактивні (sold_out, off_line тощо).

- **Ризик**:
  - Low для stablecoins (USDT тощо), Medium для staking-like, High для нових монет (визначати за productLevel: beginner=Low, VIP=Medium).

- **Інші поля**:
  - id: "bitget_" + periodType + "_" + productId.
  - symbol: coin.
  - name: coin + " " + periodType.capitalize() + " Savings" (додати period для fixed).
  - provider: "Bitget".
  - description: З advanceRedeem та settleMethod.
  - website_url: "https://www.bitget.com/earn".
  - raw_data: Зберегти повний об'єкт для діагностики.
  - Якщо apyList порожній (рідкісний випадок), встановити apy = 0.0 та логувати помилку для моніторингу.

- **Валідація**: Перевіряти обов'язкові поля; видаляти невалідні продукти.

---

## 📁 Структура модулів для Bitget

- Шлях: yield-data-service/app/services/exchanges/bitget/
  - __init__.py: Імпорти модулів.
  - api.py: API клієнт з методами для flexible/fixed/earn продуктів.
  - service.py: Бізнес-логіка, кешування, синхронізація з БД.
  - models.py (опціонально): Pydantic моделі для відповідей.

---

## 🚀 Покрокова інструкція інтеграції

### Крок 1: Підготовка
- Ознайомитися з документацією Bitget API для Savings.
- Зареєструвати API key з правами на Earn (read-only достатньо).
- Створити директорію: yield-data-service/app/services/exchanges/bitget.
- Додати ключі до .env: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE.

### Крок 2: Реалізація API клієнта (api.py)
- Успадкувати від BaseExchange.
- Реалізувати аутентифікацію: генерувати headers з ACCESS-KEY, ACCESS-SIGN (HMAC-SHA256), ACCESS-TIMESTAMP, ACCESS-PASSPHRASE.
- Методи: get_flexible_savings_products (filter="available", periodType="flexible"), get_locked_savings_products (periodType="fixed"), get_earn_products (агрегація), get_earn_products_by_asset (з coin).
- У методах get_flexible_savings_products та get_locked_savings_products додати парсинг string-значень до float/int (наприклад, для currentApy, minStepVal).
- У get_earn_products обробити випадок, коли filter="all", щоб отримати повний список, включаючи неактивні для діагностики (але фільтрувати тільки активні для нормалізації).
- Обробити query params та парсинг відповіді з data.

### Крок 3: Реалізація сервісу (service.py)
- Успадкувати від BaseExchangeService.
- Ініціалізувати API клієнт з ключів з settings.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Додати retry з exponential backoff.

Метод sync_products_to_db повинен оркеструвати процес нормалізації та збереження в PostgreSQL. Ось детальний покроковий опис логіки (без прикладів коду, як просив у стилі):

Отримання даних з API: Викликати get_products_from_api (або з кешу, якщо доступно) для отримання сирого списку продуктів. Якщо symbol вказано, фільтрувати по coin.
Фільтрація активних продуктів: Ітеративно пройти по списку продуктів і відфільтрувати тільки ті, де status == "in_progress" (активні). Ігнорувати інші статуси (наприклад, sold_out, off_line).

Нормалізація кожного продукту:

- Створити словник з обов'язковими полями (id, symbol, name, provider тощо) за правилами нормалізації.
- Для ladder APY: Ітеративно пройти по apyList, знайти максимальний currentApy (float), або розрахувати середній, якщо tiers > 1 (наприклад, сума currentApy / len(apyList)).
- Парсити string до float для apy, min_amount, max_amount; якщо помилка парсингу, встановити null або 0.0 і логувати.
- Встановити lock_period_days: 0 для flexible, int(period) для fixed.
- Додати raw_data як JSONB поле для діагностики.

Підготовка до вставки в БД:

- Використовувати SQLAlchemy або psycopg2 для з'єднання з PostgreSQL (таблиця yield_products).
- Перевірити існування продукту за id: Якщо існує, оновити поля (UPDATE query з WHERE id = ...).
- Якщо не існує, вставити новий запис (INSERT INTO yield_products VALUES ...).


Транзакційна вставка:

- Використовувати транзакцію (with session.begin()): Для кожного нормалізованого продукту виконати UPSERT (INSERT ... ON CONFLICT DO UPDATE) для уникнення дублів.
- Поля для збереження: id (PRIMARY KEY), symbol, name, provider, apy (NUMERIC), min_amount (NUMERIC або NULL), max_amount (NUMERIC або NULL), lock_period_days (INTEGER), product_type (VARCHAR), is_active (BOOLEAN), risk_level (VARCHAR), description (TEXT), website_url (VARCHAR), raw_data (JSONB).
- Після вставки, комітити транзакцію.

Обробка помилок та логування:

- Якщо помилка вставки (наприклад, унікальність порушена), rollback транзакції та логувати (logger.error з деталями).
Повернути словник з результатом: {"synced": кількість_продуктів, "errors": список_помилок}.
- Оновлення кешу після синхронізації: Після успішної вставки, оновити Redis-кеш з новими даними для швидкого доступу в майбутніх запитах.

### Крок 4: Реалізація моделей (models.py) - опціонально
- Моделі для Flexible та Fixed продуктів з полями з API.

### Крок 5: Налаштування імпортів (__init__.py)
- Експортувати класи API, Service, моделі.

### Крок 6: Реєстрація біржі в системі
- Додати до aggregation_service.py: DataSource.API_BITGET, fallback_chain, _get_exchange_data.
- Додати до registry.py: AVAILABLE_EXCHANGES = ["binance", ..., "bitget"].
- Додати до routes.py: Валідація в get_exchanges та get_exchanges_popular; оновити provider_mapping = {'bitget': 'Bitget'}.
- Додати новий ендпоінт для тесту синхронізації: POST /api/v1/bitget/sync, який викликає sync_products_to_db і повертає статус.

### Крок 7: Оновлення конфігурації
- Додати до config.py: bitget_api_key, bitget_api_secret, bitget_api_passphrase.
- Додати до docker-compose.yml: environment для BITGET_*.
- У .env додати BITGET_API_PASSPHRASE=your_passphrase (обов'язково, оскільки без нього аутентифікація не працює).

---

## 📱 Інтеграція з Telegram ботом

- Додати до provider_mapping в filtered_products.py: {'bitget': 'Bitget'}.
- Оновити списки бірж: AVAILABLE_EXCHANGES, exchanges в main_menu.py, callback_handlers.py.
- Додати реферальне посилання до REFERRAL_URLS: "bitget": "https://www.bitget.com/ref/YOUR_REF".
- Додати методи до api_client.py: get_bitget_products, get_bitget_popular.
- Бот автоматично підтримає /all_bitget_products, фільтри, сортування, пагінацію.

---

## ✅ Валідація та тестування

- Unit тести: Підключення, отримання flexible/fixed продуктів, нормалізація.
- Інтеграційні: Curl для /api/v1/exchanges?exchange=bitget, /api/v1/bitget/test.
- Функціональні: Команди в боту, перевірка таблиць, фільтрів.
- БД: SQL запити на count по provider='Bitget'.

---

## 📊 Моніторинг та підтримка

- Додати метрики Prometheus: EXTERNAL_API_CALLS, API_RESPONSE_TIME для "bitget".
- Логування: Інфо про кількість продуктів, помилки з exc_info.
- Обробка помилок: Graceful degradation, retry.
- Регулярні завдання: Щоденна синхронізація, моніторинг змін API.