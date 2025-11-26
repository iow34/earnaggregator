**Технічне завдання — Інтеграція OKX Financial Product (On-chain earn, Simple Earn Flexible) в EarnAggregator**

## Мета:
Імплементувати у yield-data-service інтеграцію з OKX для отримання та синхронізації продуктів типу On-chain earn та Simple Earn Flexible. Підтримати отримання всіх доступних продуктів для цих категорій, нормалізувати дані в уніфікований формат EarnAggregator і забезпечити надійну роботу з урахуванням rate-limit, помилок та моніторингу.

1. Загальні вимоги

- API-ключ OKX зберігається тільки у файлі .env в кореневій директорії проекту (наприклад OKX_API_KEY, OKX_API_SECRET якщо secret потрібен). (обов’язково).
- Інтеграція повинна відповідати архітектурі EarnAggregator: окрема директорія app/services/exchanges/okx/ з файлами api.py, service.py, models.py, __init__.py. (Шаблон і правила структури взяти з внутрішньої інструкції).
- Всі зовнішні HTTP виклики — через центральний _make_request (базовий клієнт) із підтримкою backoff/retry, логування, метрик і cassh/fallback до БД. (Стандарт проекту).

2. Джерела й документація (посилання для розробника)

- On-chain earn endpoint: GET /api/v5/finance/staking-defi/offers

Simple Earn endpoint (потребує уточнення в документації, типово):

- GET /api/v5/finance/simple-earn/products
- Перевірити актуальні ендпоїнти в розділі "Financial Product → Simple Earn" документації


- Офіційна документація OKX — Financial Product (On-chain earn та супутні ендпоїнти). Обов’язково вивчити розділ Financial Product у docs-v5. 
- OKX Simple Earn (огляд та правила продукту — flexible). 
- OKX API documentation: https://www.okx.com/docs-v5/en/#financial-product
- Рекомендовані Python SDK та приклади/реалізації на GitHub (офіційний/спільнотний) — використовувати mcp github для пошуку прикладів поведінки підписання, обробки помилок та rate limits. 

3. Обсяги інтеграції (що має бути реалізовано)

- Отримання всіх доступних продуктів On-chain earn (усі сторінки/пагінація) — включно з полями: productId, ccy (symbol), protocol, protocolType, term (lock days / 0 для flexible), apy (як float), earlyRedeem (boolean), status/isActive, інші метадані. (Відповідно до відповіді OKX). 
- Отримання всіх Simple Earn Flexible продуктів (усі варіанти flexible в Simple Earn). Забезпечити повний перелік активів/пропозицій та їх APY, мін/макс суму, статус. 
OKX
- Нормалізація отриманих даних у внутрішній формат EarnAggregator (обов’язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level, raw_data).
- Експортувати/синхронізувати продукти у БД (Postgres) через існуючі сервіси синхронізації. Забезпечити id-mapping (унікальний id: okx_<type>_<productId>).

3.3 Специфіка аутентифікації OKX API
OKX використовує обов'язкові 3 параметри для аутентифікації (на відміну від Binance з 2 параметрами):

API Key (OKX_API_KEY)
API Secret (OKX_API_SECRET)
Passphrase (OKX_API_PASSPHRASE) - унікальна особливість OKX

Важливо: Passphrase — це пароль, який користувач встановлює при створенні API ключа. Його НЕ можна відновити, тільки створити новий API ключ.
Формат підпису OKX:
message = timestamp + method + requestPath + body
signature = base64(HMAC-SHA256(message, secret_key))

HTTP заголовки:

OK-ACCESS-KEY: API ключ
OK-ACCESS-SIGN: Підпис (base64-encoded HMAC SHA256)
OK-ACCESS-TIMESTAMP: ISO 8601 timestamp в UTC (формат: 2020-12-08T09:08:57.715Z)
OK-ACCESS-PASSPHRASE: Passphrase користувача
Content-Type: application/json

Формат timestamp: ISO 8601 з мілісекундами та суфіксом 'Z':
timestamp = datetime.datetime.utcnow().isoformat()[:-3] + 'Z'
# Приклад: "2025-10-29T14:23:45.123Z"


4. Архітектура модуля (високо-рівнево)

Розміщення: yield-data-service/app/services/exchanges/okx/

4.1. api.py — клієнт OKX:

- Повинен враховувати пагінацію, rate limits, retry/backoff, таймаути, логування, парсинг помилок.
- Виклики повинні повертати сирий JSON і/або перелік диктів ready-to-normalize.
- Підтримка sandbox/simulation mode (тільки для локального тестування) — якщо OKX дає sandbox, додати конфігурований base_url.

4.2. service.py — бізнес-логіка:

- Ініціалізація клієнта з API-ключем з settings (завантаженим з .env).
- Методи: initialize(), get_products_from_api(symbol=None), get_products_with_cache(symbol=None), sync_products_to_db(), test_connection(), get_health_status().
- Вбудувати Prometheus-метрики: зовнішні виклики, час відповіді, кількість помилок. 

4.3. models.py — pydantic-моделі (опціонально але рекомендовано):

- Моделі для On-chain продуктів, Simple Earn Flexible продуктів та уніфікована модель EarnAggregator.

4.4. init.py — експорт класів/модулів.


5. Контракти API та важливі деталі реалізації

Прямі ендпоїнти та контрактні поля — узяти з офіційної документації OKX. В ТЗ даємо структуру викликів/логіки (без коду).

5.1 On-chain earn — основні ендпоїнти та правила

Endpoint: GET /api/v5/finance/staking-defi/offers
Параметри запиту:
{
    "productId": "",      # опціонально: фільтр по конкретному продукту
    "protocolType": "",   # опціонально: "staking" / "defi_lending" / тощо
    "ccy": ""             # опціонально: фільтр по валюті (BTC, ETH, тощо)
}

Приклад відповіді: (згідно з docs)
{
  "code": "0",
  "data": [
    {
      "ccy": "ETH",
      "productId": "1234567",
      "protocol": "lido",
      "protocolType": "staking",
      "term": "",
      "apy": "0.0395",
      "earlyRedeem": true,
      "investData": [
        {
          "ccy": "ETH",
          "bal": "0.01",
          "minAmt": "0.01",
          "maxAmt": ""
        }
      ],
      "state": "purchasable"
    }
  ],
  "msg": ""
}
Ключові правила:

apy повертається як string у форматі десяткового дробу (0.0395 = 3.95%)
term для On-chain often порожній (flexible) або в днях
state: "purchasable" = активний, "sold_out" / "suspend" = неактивний
Пагінація: відсутня в офіційній документації для цього ендпоїнту — отримувати всі за один виклик

Основні операції (згідно з docs):

- отримати перелік пропозицій
- Фільтрувати тільки active продукти (за їхнім полем статусу), але зберігати raw_data для діагностики.

5.2 Simple Earn Flexible — основні ендпоїнти та правила

Endpoint: GET /api/v5/finance/simple-earn/products
ВАЖЛИВО: Точний ендпоїнт потрібно уточнити в розділі "Financial Product → Simple Earn" офіційної документації OKX, оскільки він може змінюватися.

Типова структура відповіді:
{
  "code": "0",
  "data": [
    {
      "ccy": "USDT",
      "rate": "0.05",
      "minAmt": "1",
      "maxAmt": "1000000",
      "autoRenew": true,
      "status": "available"
    }
  ],
  "msg": ""
}

OKX Simple Earn має власну категорію продуктів (Flexible і Fixed). Для flexible необхідно отримувати: список токенів/пропозицій, APY, мін/макс суми, можливі терміни (0 — flexible), статус.
- Документація OKX згадує Simple Earn endpoints в розділі Financial Product; потрібно використовувати відповідні ендпоїнти типу savings/simple earn (точні назви у docs-v5 — використовувати як довідник при імплементації). 

Обов’язкові правила:

- Підтримати пагінацію та агрегацію всіх flexible-пропозицій.
- APY може оновлюватися часто — зберігати час останнього оновлення та raw_data.
- Перетворювати одиниці (якщо OKX повертає APY як дробове число) у внутрішній формат; забезпечити точність (2–4 знаки після коми).


6. Rate limits, retry, throttling, кеш

- Rate limits — дотримуватися значень з docs (On-chain earn: 3 req/s по User ID). Планувати глобальний контролер викликів для OKX (shared для всіх ендпоїнтів). 
- Retry logic — при 5xx та network errors — exponential backoff (наприклад: 0.5s, 1s, 2s, 4s), обмежити максимум спроб (на рівні клієнта, наприклад 3–5). Для 429 — враховувати Retry-After заголовок, якщо надано.
- Cache — використовувати Redis як кеш для списків продуктів (TTL configurable, наприклад 60 хв для flexible, fixed/on-chain залежно від частоти оновлень). Використати get_products_with_cache(...).
- Fallback — при відмові API повертати останні дані з БД/кешу та відповідне поле статусу (degraded).

Глобальний throttler:

Використовувати Token Bucket або Leaky Bucket алгоритм
Спільний для всіх викликів до OKX Financial Product
Конфігурація: max_requests_per_second = 3


7. Нормалізація та збереження даних

- Нормалізувати кожен продукт до внутрішньої моделі (див. пункт 3.1). Поля обов’язкові: id, symbol, name, provider="OKX", apy, min_amount, max_amount, lock_period_days, product_type (Onchain / SimpleFlexible), is_active, raw_data.
- APY: якщо OKX повертає дробове (0.07) — перетворити на відсоткове значення або у формат, прийнятий у проекті; фіксувати precision (2–4 знаки).
- min_amount / max_amount: приводити до float або null. Якщо валюта різна (наприклад USDT vs BTC) — зберігати одиницю у symbol.
- Додавати source_updated_at (час відповіді API) та fetched_at (локальний timestamp).
- Для продуктів on-chain з earlyRedeem=true — відмітити в полі can_early_redeem.


8. Тестування та валідація

- Unit tests: мокати API-відповіді (positive/negative), перевірити парсинг та нормалізацію полів (apy, term → lock_period_days, product_type). В internal tests слідувати шаблонам з інструкції.
- Integration tests: реальні HTTP виклики до sandbox (якщо доступний) або до production з тестовими API-ключами. Тест-кейси: отримання списку, пагінація, rate limit handling, кеш.
- E2E: виклик REST-endpointів сервісу (/api/v1/exchanges/okx/products, /api/v1/okx/test, /api/v1/okx/sync) та перевірка записів у БД: унікальність id, коректність product_type, наявність raw_data. (Шаблони маршрутів — як у внутрішньому гайді).


9. Моніторинг, логування, SLA

- Метрики Prometheus: okx_api_calls_total, okx_api_errors_total, okx_api_response_time_seconds (етикети: endpoint, status_code). Інтегрувати у service.py перед/після зовнішніх викликів.
- Логи: structured logs з полями exchange=okx, endpoint, request_id, duration_ms, http_status, error (stack при помилці).
- Alerting: сповіщення при: частих 5xx (>5% запитів за 5 хв), постійному 429, падінні sync job.
- SLA: при неможливості оновити продукти — сервіс повинен повернути дані з кешу і статус degraded у health endpoint.


10. Конфігурація та безпека

- .env — зберігати OKX_API_KEY і OKX_API_SECRET (якщо потрібен). Заборонено комітити .env. Документувати у README крок створення ключа на OKX та права ключа (read-only для отримання продуктів.
- Перевірка permission — при 401/403 логувати і виводити зрозуміле повідомлення (API key відсутній/неправильний/не має прав).
- Безпечне логування — ніколи не логувати API-secret або приватну інформацію користувача (PPI).

Безпечне логування:
# ❌ ЗАБОРОНЕНО:
logger.info(f"Using API key: {api_key}")
logger.debug(f"Passphrase: {passphrase}")
logger.debug(f"Signature: {signature}")

# ✅ ПРАВИЛЬНО:
logger.info(f"Using API key: {api_key[:8]}***")  # Тільки перші 8 символів
logger.debug("Signature generated successfully")  # Без самого підпису
# Passphrase взагалі не логувати!


11. План робіт — Етапи та підетапи (покроково)
Етап A — Підготовчий (документація + оточення)

- Ознайомлення з OKX Financial Product docs (On-chain earn, Simple Earn Flexible). 
- Підготувати структуру директорії app/services/exchanges/okx/ згідно з внутрішнім стандартом.
- Додати змінні у .env.example (OKX_API_KEY, OKX_API_SECRET, OKX_BASE_URL (prod/sandbox)). Заборонити комітити .env.

Етап B — Реалізація API-клієнта (api.py)

- Описати методи для потрібних ендпоїнтів.
- Реалізувати handling пагінації, rate limit (3 rps для on-chain), retry/backoff, timeout. 
- Документувати кожен метод (в docstring): вхідні параметри, поведінка пагінації, очікувані поля у відповіді (mapping).
- Написати unit-тести на парсинг/нормалізацію відповідей.

Етап C — Бізнес-логіка (service.py)

- Ініціалізація клієнта з конфігурації/.env.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Інтегрувати Prometheus-метрики та логування.

Етап D — Нормалізація → DB

- Визначити mapping полів OKX → EarnAggregator (document mapping table у README модуля).
- Реалізувати транзакційну синхронізацію (upsert логіка: оновлювати поля, зберігати raw_data).
- Тестувати SQL запитами та перевірками у тестовій БД.

Етап E — Endpoints і бот

- Додати маршрути у app/api/routes.py: /api/v1/exchanges/okx/test, /api/v1/exchanges/okx/products, /api/v1/exchanges/okx/sync.
- Додати виклики у Telegram-бот (методи для запитів до нових API).


12. Перелік артефактів (що має бути передано після виконання)

- Папка app/services/exchanges/okx/ з файлами: api.py, service.py, models.py, __init__.py. (код — в PR).
- README модуля з:

описом ендпоїнтів OKX, їх rate limits, параметрів;
mapping полів OKX → EarnAggregator;
прикладами можливих помилок і як їх дебажити.

- Unit + integration тест-сьюти (pytest).
- Скрипт/CI job для запуску sync (docker-compose).
- Документація зміни в загальному README проекту (.env.example оновлення).


13. Ризики та нюанси (з голосу спільноти / SDK)

- Невідповідність полів: OKX іноді повертає APY як 0.07 або як '0.07'. Написати валідацію типів і fallback-парсинг (строка→float). (практика зі sdk/обговорень). 
- Rate limits/429: деякі ендпоїнти мають жорсткіший ліміт; використовувати централізований throttler. (спільні поради зі sdk). 
- Region/Availability: деякі продукти можуть бути недоступні в окремих регіонах — зберігати поле region/available_to якщо воно присутнє.
- Sandbox: тестувати у sandbox/тестовому режимі SDK перед роботою з production keys (якщо доступно).

Відмінності структури On-chain vs Simple Earn

On-chain: повертає масив investData з варіантами інвестування
Simple Earn: повертає прості об'єкти з одним варіантом
Рішення: Уніфікувати парсинг через окремі методи для кожного типу

Empty responses vs Errors

OKX може повернути {"code": "0", "data": [], "msg": ""} — це НЕ помилка, просто немає продуктів
Перевіряти code == "0" для успішності, а не тільки наявність даних