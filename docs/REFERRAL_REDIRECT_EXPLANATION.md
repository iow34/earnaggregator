# Технічна реалізація редіректу на реферальні посилання бірж

## Загальна схема роботи

Система редіректу працює в два етапи:

1. **Генерація трекінгового посилання** - створюється посилання через redirect server з параметрами трекінгу
2. **Редірект на біржу** - redirect server логує клік та виконує 302 редірект на реферальне посилання з .env

## Детальний опис процесу

### Етап 1: Генерація трекінгового посилання

**Файл:** `yield-telegram-bot/bot/services/referral_link_generator.py`

**Метод:** `ReferralLinkGenerator.generate_link()`

**Процес:**

1. Отримує `telegram_id`, `exchange`, `page` та опціональний `ref_code`
2. Для `telegram_id <= 0` (кеш/плейсхолдер) повертає пряме реферальне посилання з .env без трекінгу
3. Для реальних користувачів:
   - Отримує `source` (acquisition_source) через tracking API (за замовчуванням 'organic')
   - Отримує реферальний код з .env якщо не передано
   - Формує URL: `{TRACKING_REDIRECT_URL}/ref?telegram_id={id}&source={source}&page={page}&exchange={exchange}&ref_code={code}`
   - Повертає це трекінгове посилання

**Приклад:**

```
http://192.168.1.38:8000/ref?telegram_id=123456&source=organic&page=1&exchange=binance&ref_code=39794924
```

### Етап 2: Редірект на біржу

**Файл:** `yield-data-service/app/api/tracking_routes.py`

**Endpoint:** `GET /ref`

**Процес:**

1. **Отримання параметрів:**

   - `telegram_id` - ID користувача (новий формат)
   - `user` - UUID користувача (старий формат, застаріло)
   - `source` - джерело входу (organic, deep_link, etc.)
   - `page` - сторінка бота (1, 2, 3)
   - `exchange` - назва біржі (binance, bybit, etc.)
   - `ref_code` - реферальний код (опціонально, застаріло)

2. **Логування кліку:**

   - Якщо є валідний `telegram_id`, записує клік в БД через `SimpleClickCRUD.create()`
   - Зберігає: telegram_id, exchange, page, source, ip_address, user_agent, ref_code
   - Якщо логування не вдалося, продовжує редірект (graceful degradation)

3. **Отримання реферального посилання:**

   - Викликає `get_exchange_referral_url(exchange)`
   - Функція читає реферальні посилання з `.env` через `settings`:
     - `settings.referral_binance` → `REFERRAL_BINANCE` з .env
     - `settings.referral_bybit` → `REFERRAL_BYBIT` з .env
     - і т.д. для всіх бірж
   - Повертає повне реферальне посилання з .env (воно вже містить реферальний код)

4. **302 Redirect:**
   - Виконує `RedirectResponse(url=target_url, status_code=302)`
   - Браузер автоматично переходить на реферальне посилання біржі

**Приклад редіректу:**

```
GET /ref?telegram_id=123456&source=organic&page=1&exchange=binance
→ Логування кліку в БД
→ Redirect 302 на: https://accounts.binance.com/register?ref=39794924
```

## Конфігурація

### Реферальні посилання в .env

Всі реферальні посилання зберігаються в `.env` файлі:

```env
REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924
REFERRAL_BYBIT=https://www.bybit.com/invite?ref=JG6XK
REFERRAL_OKX=https://okx.com/join/48177058
# ... і т.д.
```

### Читання з .env

**Файл:** `yield-data-service/app/config.py`

Реферальні посилання додані в клас `Settings`:

```python
referral_binance: str = Field(default="...", alias="REFERRAL_BINANCE")
referral_bybit: str = Field(default="...", alias="REFERRAL_BYBIT")
# ... і т.д.
```

Pydantic автоматично читає значення з `.env` файлу через `alias`.

### Використання в редіректі

**Файл:** `yield-data-service/app/api/tracking_routes.py`

Функція `get_exchange_referral_url()` мапить назву біржі на відповідне поле з `settings`:

```python
def get_exchange_referral_url(exchange: str) -> str:
    referral_map = {
        'binance': settings.referral_binance,
        'bybit': settings.referral_bybit,
        # ... і т.д.
    }
    return referral_map.get(exchange.lower(), settings.referral_binance)
```

## Важливі моменти

1. **Реферальні посилання вже містять коди:**

   - Раніше система намагалася додавати `ref_code` як параметр до базового URL
   - Тепер використовуються повні URL з .env, які вже містять реферальні коди

2. **Fallback механізм:**

   - Якщо біржа не знайдена в маппінгу, використовується `settings.referral_binance` як fallback
   - Якщо помилка під час редіректу, також використовується Binance як fallback

3. **Трекінг кліків:**

   - Кліки логуються в БД для аналітики
   - Якщо логування не вдалося, редірект все одно виконується (graceful degradation)

4. **Підтримка старого формату:**
   - Система підтримує старий формат з `user` (UUID) для сумісності
   - Але рекомендується використовувати новий формат з `telegram_id`

## Приклад повного потоку

1. **Користувач клікає на посилання в Telegram боті:**

   ```
   <a href="http://192.168.1.38:8000/ref?telegram_id=123456&source=organic&page=1&exchange=binance">
   ```

2. **Redirect server отримує запит:**

   - Логує клік в БД (telegram_id=123456, exchange=binance, page=1)
   - Отримує реферальне посилання: `settings.referral_binance`
   - Значення з .env: `https://accounts.binance.com/register?ref=39794924`

3. **Виконує 302 Redirect:**

   ```
   HTTP/1.1 302 Found
   Location: https://accounts.binance.com/register?ref=39794924
   ```

4. **Браузер автоматично переходить на Binance** з реферальним кодом

## Переваги цієї реалізації

1. **Централізоване управління:** Всі реферальні посилання в одному місці (.env)
2. **Трекінг:** Всі кліки логуються для аналітики
3. **Гнучкість:** Легко змінити реферальні коди через .env без зміни коду
4. **Надійність:** Graceful degradation - редірект працює навіть якщо логування не вдалося
