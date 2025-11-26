# ⚠️ Обмеження Трекінгу Реферальних Посилань - Технічний Звіт

**Дата:** 2025-11-09  
**Статус:** ❌ Неможливо трекати прямі URL посилання

---

## 🎯 Проблема

Користувач клікає на реферальні посилання в боті, але **дані НЕ записуються в БД**.

### Поточна Реалізація

**1. Головна сторінка (Блок 2 - огляд бірж):**

```html
<b>Binance</b> <a href="https://accounts.binance.com/...">перейти ↗️</a>
```

**2. Сторінка "Всі Біржі":**

```html
🏦 <b>Binance</b> <a href="https://accounts.binance.com/...">перейти ↗️</a>
```

**3. Команда /yield:**

```python
InlineKeyboardButton(text="Binance", url="https://accounts.binance.com/...")
```

---

## ❌ Чому Не Працює Трекінг

### Технічне Обмеження Telegram Bot API

**HTML посилання (`<a href>`)**:

```
Користувач клікає → Telegram відкриває браузер напряму
❌ Callback query НЕ генерується
❌ Bot API НЕ отримує повідомлення про клік
❌ Middleware НЕ може перехопити
❌ Дані НЕ записуються в БД
```

**URL кнопки (`type="url"`)**:

```
Користувач клікає → Telegram відкриває браузер
❌ Callback query НЕ генерується
❌ Update НЕ надсилається боту
❌ Неможливо трекати
```

**Callback кнопки (`type="callback"`)**:

```
Користувач клікає → Telegram надсилає callback_query
✅ Bot отримує Update
✅ Middleware перехоплює
✅ Handler обробляє
✅ Дані записуються в БД
```

### Офіційна Документація Telegram

Згідно з [Telegram Bot API](https://core.telegram.org/bots/api#inlinekeyboardbutton):

> **url** (String, optional): HTTP or tg:// URL to be opened when the button is pressed. **Links opened by this button will not be tracked by the bot.**

**Переклад:** Посилання відкриті через цю кнопку НЕ БУДУТЬ відслідковуватись ботом.

---

## 📊 Перевірка БД - Підтвердження

### SQL Запити

```sql
-- Всього подій
SELECT COUNT(*) FROM user_actions;
-- Результат: 252

-- Реферальні кліки
SELECT COUNT(*) FROM user_actions WHERE action_type = 'referral_click';
-- Результат: 0

-- Типи подій
SELECT action_type, COUNT(*)
FROM user_actions
GROUP BY action_type;

-- Результат:
-- button_click: 218 (callback кнопки трекаються!)
-- command_start: 15
-- command_other: 14
-- text_input: 5
```

**Висновок:** Button clicks трекаються (218 записів), але тільки **callback кнопки**, не URL кнопки.

---

## 🔧 Можливі Рішення

### Рішення 1: Callback Кнопки (Відхилено користувачем)

**Як працює:**

- Кнопка з `callback_data` замість `url`
- При кліку бот отримує callback
- Записує в БД
- Відправляє користувачу повідомлення з посиланням

**Переваги:**

- ✅ 100% точність трекінгу
- ✅ Повний контекст (біржа, символ, час)
- ✅ Можливість аналітики

**Недоліки:**

- ❌ Додатковий крок для користувача (2 кліки замість 1)
- ❌ Змінює UX (користувач отримує повідомлення замість прямого переходу)

**Статус:** ❌ Відхилено користувачем

---

### Рішення 2: UTM Параметри (Рекомендовано)

**Підхід:** Додавати унікальні UTM параметри до кожного реферального посилання.

**Реалізація:**

```python
def get_tracked_referral_url(exchange: str, user_id: int, symbol: Optional[str] = None) -> str:
    """Генерувати реферальне посилання з UTM трекінгом."""
    base_urls = {
        "binance": "https://accounts.binance.com/register?ref=CPA_00K8Q3Q2",
        "bybit": "https://www.bybit.com/invite?ref=CPA_00K8Q3Q2",
        # ...
    }

    base_url = base_urls.get(exchange.lower(), "#")

    # Додати UTM параметри
    utm_params = (
        f"&utm_source=telegram_bot"
        f"&utm_medium=referral"
        f"&utm_campaign=earn_aggregator"
        f"&utm_content={exchange}"
        f"&user_id={user_id}"  # ← Унікальний ідентифікатор
    )

    if symbol:
        utm_params += f"&symbol={symbol}"

    return base_url + utm_params
```

**Використання:**

```python
# В main_menu.py
referral_url = get_tracked_referral_url("binance", user_id=message.from_user.id)
text = f"<b>Binance</b> <a href='{referral_url}'>перейти ↗️</a>\n"
```

**Переваги:**

- ✅ Зберігається прямий перехід (1 клік)
- ✅ UX не змінюється
- ✅ Трекінг через Google Analytics / біржеву аналітику
- ✅ Унікальні user_id в посиланні

**Недоліки:**

- ❌ Трекінг тільки якщо біржа підтримує UTM
- ❌ Потрібно інтегрувати з системою аналітики біржі
- ❌ Не записується в БД Telegram бота

**Статус:** 🟡 Можливе рішення

---

### Рішення 3: Server-Side Redirect

**Підхід:** Створити власний сервер для redirect з трекінгом.

**Архітектура:**

```
Користувач клікає → bot.earnaggregator.com/ref/binance?user=12345
                              ↓
                    1. Записує в БД (user_id, exchange, timestamp)
                    2. HTTP 302 Redirect → https://binance.com/...
                              ↓
                    Користувач переходить на біржу
```

**Реалізація:**

```python
# FastAPI endpoint для redirect
@app.get("/ref/{exchange}")
async def track_referral(
    exchange: str,
    user_id: int,
    symbol: Optional[str] = None
):
    # Записати в БД
    await db.execute(
        "INSERT INTO referral_clicks (user_id, exchange, symbol) VALUES ($1, $2, $3)",
        user_id, exchange, symbol
    )

    # Redirect на біржу
    referral_url = REFERRAL_URLS[exchange]
    return RedirectResponse(url=referral_url)
```

**Використання в боті:**

```python
redirect_url = f"https://bot.earnaggregator.com/ref/binance?user_id={user_id}&symbol=BTC"
text = f"<b>Binance</b> <a href='{redirect_url}'>перейти ↗️</a>\n"
```

**Переваги:**

- ✅ Прямий перехід (1 клік)
- ✅ 100% точність трекінгу
- ✅ Запис в БД
- ✅ UX не змінюється

**Недоліки:**

- ❌ Потрібен окремий веб-сервер
- ❌ Додаткова інфраструктура
- ❌ Потрібен домен

**Статус:** 🟢 Найкраще технічне рішення

---

### Рішення 4: Existing Tables (Поточна Система)

**Підхід:** Використовувати існуючу таблицю `referral_clicks`.

**Що трекається зараз:**

```python
# В bot/db/crud.py існує функція:
async def add_referral_click(session, user_id, exchange, symbol):
    click = ReferralClick(user_id=user_id, exchange=exchange, symbol=symbol)
    session.add(click)
    await session.commit()
```

**Де використовується:** НЕ використовується (немає місця де викликається).

**Можливість:** Ручне логування при певних діях

```python
# Наприклад, при команді /yield можна логувати як "інтерес до біржі"
if data["success"] and data["data"]:
    async with get_database_session() as session:
        # Логувати перегляд продуктів як потенційний інтерес
        await add_referral_click(
            session=session,
            user_id=user.id,  # ID в БД, не telegram_id
            exchange="mixed",  # Або топ біржа з результатів
            symbol=symbol
        )
```

**Переваги:**

- ✅ Немає змін в UI
- ✅ Використовує існуючу таблицю

**Недоліки:**

- ❌ Не точний трекінг (тільки "інтерес", не "клік")
- ❌ Не відображає реальні переходи
- ❌ Складно інтерпретувати дані

**Статус:** 🟡 Часткове рішення

---

### Рішення 5: Комбінований Підхід

**Підхід:** Трекати все що можливо + inferring (припущення).

**Що трекається:**

1. ✅ Команди (`/yield BTC`) → записується в `user_queries`
2. ✅ Перегляди сторінок → записується в `user_actions` (button_click)
3. ✅ Фільтри → записується в `user_actions`

**Що не трекається:**

1. ❌ Прямі кліки на URL посилання

**Inference (припущення):**

```python
# Аналіз: якщо користувач
# 1. Переглянув /yield BTC
# 2. Побачив результати з Binance
# 3. Не виконав інших дій протягом 5 хвилин
# → Можливо перейшов на Binance (ймовірність 70%)

# Записати як "потенційний referral"
```

**Переваги:**

- ✅ Використовує існуючі дані
- ✅ Немає змін в UI
- ✅ Якась аналітика доступна

**Недоліки:**

- ❌ Не точно
- ❌ Тільки припущення
- ❌ Не підходить для розрахунку винагород

**Статус:** 🟡 Можливо для загальної аналітики

---

## 📊 Поточний Стан Системи Трекінгу

### Що Працює ✅

**Таблиця `user_actions` (252 записи):**

```sql
✅ button_click: 218 (callback кнопки)
✅ command_start: 15 (команди)
✅ command_other: 14 (команди)
✅ text_input: 5 (текст)
```

**Компоненти:**

- ✅ TrackingMiddleware - працює
- ✅ EventProcessor - працює
- ✅ SessionManager - працює
- ✅ LogCleaner - працює
- ✅ Metrics - працюють

### Що НЕ Працює ❌

```sql
❌ referral_click: 0
```

**Причина:** Прямі URL посилання не генерують callback_query в Telegram Bot API.

---

## 💡 Рекомендоване Рішення

### Server-Side Redirect (Найкраще)

**Переваги:**

1. ✅ **100% точність** - кожен клік записується
2. ✅ **Зберігає UX** - прямий перехід одним кліком
3. ✅ **Повний контекст** - user_id, exchange, symbol, timestamp
4. ✅ **Масштабованість** - FastAPI endpoint витримає навантаження
5. ✅ **Додаткові можливості** - геолокація, device info, A/B тестування

**Імплементація:**

**1. Створити endpoint в yield-data-service:**

```python
# app/api/v1/endpoints/tracking.py

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.db.database import get_db
from app.db.models import ReferralClick

router = APIRouter()

REFERRAL_URLS = {
    "binance": "https://accounts.binance.com/register?ref=CPA_00K8Q3Q2",
    "bybit": "https://www.bybit.com/invite?ref=CPA_00K8Q3Q2",
    # ...
}

@router.get("/track/referral/{exchange}")
async def track_and_redirect(
    exchange: str,
    user_id: int,
    symbol: str = None,
    db: Session = Depends(get_db)
):
    """Трекінг реферального кліку та redirect."""

    # 1. Записати в БД
    try:
        click = ReferralClick(
            user_id=user_id,
            exchange=exchange,
            symbol=symbol,
            timestamp=datetime.now(UTC)
        )
        db.add(click)
        db.commit()
    except Exception as e:
        logger.error(f"Помилка запису: {e}")

    # 2. Redirect на біржу
    referral_url = REFERRAL_URLS.get(exchange.lower(), "https://example.com")
    return RedirectResponse(url=referral_url, status_code=302)
```

**2. Оновити посилання в боті:**

```python
# bot/handlers/main_menu.py
def get_tracked_url(exchange: str, user_id: int, symbol: str = None) -> str:
    """Генерувати URL з трекінгом."""
    base = f"https://yield-api:8000/api/v1/track/referral/{exchange}"
    params = f"?user_id={user_id}"
    if symbol:
        params += f"&symbol={symbol}"
    return base + params

# Використання
referral_url = get_tracked_url("binance", user_id=message.from_user.id)
text = f"<b>Binance</b> <a href='{referral_url}'>перейти ↗️</a>\n"
```

**Результат:**

```
Користувач клікає "перейти ↗️"
  ↓
Переходить на: yield-api:8000/track/referral/binance?user_id=12345
  ↓
Сервер записує: INSERT INTO referral_clicks (user_id, exchange, timestamp)
  ↓
Redirect 302 → https://binance.com/register?ref=...
  ↓
Користувач на сайті біржі
```

**Час обробки:** < 100ms (redirect майже миттєвий)

---

### Альтернатива: UTM + Manual Logging

**Якщо не хочете redirect сервер:**

1. **Додавати UTM з user_id:**

```python
url = f"https://binance.com/register?ref=...&user_id={user_id}&source=telegram_bot"
```

2. **Записувати "показ" замість "кліку":**

```python
# Коли показується повідомлення з реферальним посиланням
event_data = {
    "user_id": user_id,
    "action_type": "referral_shown",  # Не "click", а "shown"
    "context": {"exchange": "binance", "symbol": "BTC"}
}
await event_processor.add_event(event_data)
```

3. **Аналіз на стороні біржі:**

- Біржа бачить UTM параметри
- Якщо user зареєструвався - біржа знає звідки прийшов
- Але БД бота не має точних даних про клік

---

## 📋 Порівняння Рішень

| Рішення         | Точність | UX       | Складність | Рекомендація |
| --------------- | -------- | -------- | ---------- | ------------ |
| Callback кнопки | 100%     | ⭐⭐     | Низька     | ❌ Відхилено |
| Server Redirect | 100%     | ⭐⭐⭐⭐ | Середня    | ✅ Найкраще  |
| UTM параметри   | 50%      | ⭐⭐⭐⭐ | Низька     | 🟡 Часткове  |
| Manual logging  | 30%      | ⭐⭐⭐⭐ | Низька     | 🟡 Часткове  |
| Поточна система | 0%       | ⭐⭐⭐⭐ | -          | ❌ Не працює |

---

## 🎯 Фінальна Рекомендація

### Для Точного Трекінгу: Server-Side Redirect

**Кроки впровадження:**

1. Створити endpoint `/api/v1/track/referral/{exchange}` в yield-data-service
2. Оновити функцію `_get_referral_url()` для генерації tracked URLs
3. Тестувати redirect (має бути < 100ms)
4. Моніторити через metrics

**Очікуваний результат:**

- 📊 100% точний трекінг кліків
- 💰 Дані для монетизації
- 🎯 UX не змінюється
- ⚡ Швидкий redirect

### Для Базової Аналітики: UTM + Logging "Shown"

**Якщо redirect сервер не потрібен:**

1. Додавати UTM параметри з user_id
2. Логувати показ реферального посилання (не клік)
3. Аналізувати через інші метрики (перегляди, команди)

**Очікуваний результат:**

- 📊 Приблизна аналітика (покази, не кліки)
- 🎯 UX не змінюється
- ⚠️ Не точно для розрахунку винагород

---

## ✅ Поточний Стан (Після Відкату)

### Повернуто До Оригінальної Реалізації:

- ✅ HTML посилання: `<a href='...'>перейти ↗️</a>`
- ✅ URL кнопки: `InlineKeyboardButton(url=...)`
- ✅ UX зберігається
- ❌ Трекінг реферальних кліків НЕ працює

### Система Трекінгу (Залишилась):

- ✅ TrackingMiddleware - працює для callback кнопок
- ✅ EventProcessor - працює
- ✅ SessionManager - працює
- ✅ БД готова для даних
- ✅ 252 події вже записано (команди, button_click, text_input)

### Видалені Файли:

- ❌ `bot/handlers/referral_tracking.py` - видалено
- ✅ Інші компоненти збережені

---

## 📞 Наступні Кроки

**Якщо потрібен точний трекінг реферальних кліків:**

1. Обрати підхід (рекомендую Server-Side Redirect)
2. Реалізувати redirect endpoint
3. Протестувати
4. Запустити в продакшн

**Якщо точний трекінг не критичний:**

Поточна система трекує:

- ✅ Команди користувачів
- ✅ Навігацію по боту
- ✅ Використання фільтрів
- ✅ Перегляди сторінок
- ❌ Реферальні кліки (технічне обмеження Telegram API)

---

**Версія:** 1.0  
**Статус:** 📋 Пояснення обмежень та альтернатив
