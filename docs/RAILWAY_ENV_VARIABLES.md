# 🔐 Змінні середовища для Railway

**Дата створення:** 2025-11-28  
**Проект:** EarnAggregator  
**Платформа:** Railway

---

## 📋 Загальна інформація

Цей документ містить повний список змінних середовища, необхідних для деплою проекту на Railway.

**Важливо:**
- Всі змінні потрібно налаштувати в Railway UI для кожного сервісу
- Секрети (токени, паролі) не повинні бути в коді
- Для різних сервісів потрібні різні набори змінних

---

## 🚀 Yield API Service (yield-api)

### 🔴 Обов'язкові змінні

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `DATABASE_URL` | URL підключення до PostgreSQL | `postgresql://user:pass@host:port/db` | Railway автоматично надає для managed PostgreSQL |
| `REDIS_URL` | URL підключення до Redis | `redis://host:port/0` | Railway автоматично надає для managed Redis |
| `PORT` | Порт для FastAPI (Railway надає автоматично) | `8000` | Railway автоматично встановлює |
| `ENVIRONMENT` | Середовище виконання | `production` | Встановити вручну |

### 🟡 Рекомендовані змінні

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `LOG_LEVEL` | Рівень логування | `INFO` | Встановити вручну |
| `HOST` | Host для FastAPI | `0.0.0.0` | Встановити вручну (зазвичай `0.0.0.0`) |

### 🟢 Опціональні змінні

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `SERVICE_NAME` | Назва сервісу (для Dockerfile) | `yield-api` | Встановити вручну |

---

## 🤖 Telegram Bot Service (telegram-bot)

### 🔴 Обов'язкові змінні

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `BOT_TOKEN` | Токен Telegram бота | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` | Отримати з @BotFather |
| `DATABASE_URL` | URL підключення до PostgreSQL | `postgresql://user:pass@host:port/db` | Railway автоматично надає для managed PostgreSQL |
| `REDIS_URL` | URL підключення до Redis | `redis://host:port/1` | Railway автоматично надає для managed Redis |
| `DATA_SERVICE_URL` | URL до Yield API сервісу | `https://your-api.railway.app` | URL вашого yield-api сервісу на Railway |
| `TRACKING_REDIRECT_URL` | URL для трекінгових редіректів | `https://your-api.railway.app` | URL вашого yield-api сервісу на Railway |

### 🟡 Рекомендовані змінні

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `LOG_LEVEL` | Рівень логування | `INFO` | Встановити вручну |
| `REQUEST_TIMEOUT` | Таймаут HTTP запитів | `30.0` | Встановити вручну |
| `TRACKING_ENABLED` | Увімкнути трекінг | `true` | Встановити вручну |

### 🟢 Реферальні посилання (опціональні)

| Змінна | Опис | Приклад | Де взяти |
|--------|------|---------|----------|
| `REFERRAL_BINANCE` | Реферальне посилання Binance | `https://accounts.binance.com/register?ref=YOUR_REF` | Ваш реферальний код Binance |
| `REFERRAL_BYBIT` | Реферальне посилання Bybit | `https://www.bybit.com/invite?ref=YOUR_REF` | Ваш реферальний код Bybit |
| `REFERRAL_OKX` | Реферальне посилання OKX | `https://www.okx.com/join/YOUR_REF` | Ваш реферальний код OKX |
| `REFERRAL_MEXC` | Реферальне посилання MEXC | `https://www.mexc.com/register?inviteCode=YOUR_REF` | Ваш реферальний код MEXC |
| `REFERRAL_BITMART` | Реферальне посилання BitMart | `https://www.bitmart.com/register?referralCode=YOUR_REF` | Ваш реферальний код BitMart |
| `REFERRAL_GATE` | Реферальне посилання Gate.io | `https://www.gate.io/signup?referralCode=YOUR_REF` | Ваш реферальний код Gate.io |
| `REFERRAL_BITGET` | Реферальне посилання Bitget | `https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF` | Ваш реферальний код Bitget |
| `REFERRAL_KRAKEN` | Реферальне посилання Kraken | `https://www.kraken.com/ref/YOUR_REF` | Ваш реферальний код Kraken |
| `REFERRAL_KUCOIN` | Реферальне посилання KuCoin | `https://www.kucoin.com/ref/YOUR_REF` | Ваш реферальний код KuCoin |
| `REFERRAL_HTX` | Реферальне посилання HTX | `https://www.htx.com/ref/YOUR_REF` | Ваш реферальний код HTX |
| `REFERRAL_NEXO` | Реферальне посилання Nexo | `https://nexo.io/ref/YOUR_REF` | Ваш реферальний код Nexo |

### 🟢 Трекінгові посилання (опціональні, fallback)

Якщо динамічна генерація трекінгових посилань не працює, можна встановити статичні посилання:

| Змінна | Опис | Приклад |
|--------|------|---------|
| `TRACK_BINANCE_PAGE1` | Статичне трекінгове посилання Binance сторінка 1 | `https://your-api.railway.app/ref/binance?page=1` |
| `TRACK_BINANCE_PAGE2` | Статичне трекінгове посилання Binance сторінка 2 | `https://your-api.railway.app/ref/binance?page=2` |
| `TRACK_BYBIT_PAGE1` | Статичне трекінгове посилання Bybit сторінка 1 | `https://your-api.railway.app/ref/bybit?page=1` |
| ... | (аналогічно для інших бірж) | ... |

---

## 🗄️ PostgreSQL Service (managed)

Railway автоматично надає `DATABASE_URL` для managed PostgreSQL.  
Потрібно тільки створити сервіс PostgreSQL в Railway UI.

---

## 🔴 Redis Service (managed)

Railway автоматично надає `REDIS_URL` для managed Redis.  
Потрібно тільки створити сервіс Redis в Railway UI.

---

## 📝 Інструкція по налаштуванню

### Крок 1: Створити сервіси на Railway

1. **PostgreSQL:**
   - Додати "PostgreSQL" service
   - Railway автоматично створить `DATABASE_URL`

2. **Redis:**
   - Додати "Redis" service
   - Railway автоматично створить `REDIS_URL`

3. **Yield API:**
   - Додати "GitHub Repo" service
   - Вибрати репозиторій `iow34/earnaggregator`
   - Встановити `SERVICE_NAME=yield-api`
   - Railway автоматично встановить `PORT`

4. **Telegram Bot:**
   - Додати "GitHub Repo" service (ще один)
   - Вибрати той самий репозиторій `iow34/earnaggregator`
   - Встановити `SERVICE_NAME=telegram-bot`

### Крок 2: Налаштувати змінні середовища

#### Для Yield API:

1. Відкрити налаштування Yield API service
2. Перейти в "Variables"
3. Додати змінні:
   - `ENVIRONMENT=production`
   - `LOG_LEVEL=INFO`
   - `HOST=0.0.0.0`
   - `SERVICE_NAME=yield-api`
4. Підключити `DATABASE_URL` та `REDIS_URL` з managed сервісів (Railway автоматично пропонує)

#### Для Telegram Bot:

1. Відкрити налаштування Telegram Bot service
2. Перейти в "Variables"
3. Додати змінні:
   - `BOT_TOKEN=<ваш_токен_з_BotFather>`
   - `DATA_SERVICE_URL=<URL_your_yield_api_service>`
   - `TRACKING_REDIRECT_URL=<URL_your_yield_api_service>`
   - `LOG_LEVEL=INFO`
   - `REQUEST_TIMEOUT=30.0`
   - `TRACKING_ENABLED=true`
   - `SERVICE_NAME=telegram-bot`
4. Додати реферальні посилання (опціонально):
   - `REFERRAL_BINANCE=...`
   - `REFERRAL_BYBIT=...`
   - (і так далі)
5. Підключити `DATABASE_URL` та `REDIS_URL` з managed сервісів

### Крок 3: Перевірити підключення

Після налаштування перевірити:
- Yield API доступний за URL
- Health check endpoint працює: `https://your-api.railway.app/health`
- Telegram бот відповідає на команди

---

## 🔒 Безпека

### ⚠️ Важливо:

1. **Ніколи не комітити секрети в Git**
   - Використовувати `.env` локально
   - Використовувати Railway Variables для production

2. **Обмежити доступ до змінних**
   - Тільки необхідні люди мають доступ до Railway проекту
   - Використовувати Railway Teams для управління доступом

3. **Регулярно оновлювати токени**
   - Змінювати `BOT_TOKEN` при підозрі на компрометацію
   - Оновлювати реферальні коди при необхідності

---

## 📊 Шаблон для копіювання

### Yield API Service:

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
HOST=0.0.0.0
SERVICE_NAME=yield-api
# DATABASE_URL та REDIS_URL Railway додасть автоматично
```

### Telegram Bot Service:

```bash
BOT_TOKEN=your_bot_token_here
DATA_SERVICE_URL=https://your-api.railway.app
TRACKING_REDIRECT_URL=https://your-api.railway.app
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30.0
TRACKING_ENABLED=true
SERVICE_NAME=telegram-bot
REFERRAL_BINANCE=https://accounts.binance.com/register?ref=YOUR_REF
REFERRAL_BYBIT=https://www.bybit.com/invite?ref=YOUR_REF
# ... інші реферальні посилання
# DATABASE_URL та REDIS_URL Railway додасть автоматично
```

---

## 🆘 Troubleshooting

### Проблема: DATABASE_URL не підключено

**Рішення:**
1. Перевірити, чи створено PostgreSQL service
2. В налаштуваннях Yield API / Telegram Bot service
3. Перейти в "Variables" → "Add Reference"
4. Вибрати `DATABASE_URL` з PostgreSQL service

### Проблема: REDIS_URL не підключено

**Рішення:**
Аналогічно до DATABASE_URL, але вибрати Redis service.

### Проблема: BOT_TOKEN не працює

**Рішення:**
1. Перевірити, чи токен правильний (без пробілів)
2. Перевірити, чи токен активний в @BotFather
3. Перезапустити Telegram Bot service

---

**Останнє оновлення:** 2025-11-28
<<<<<<< HEAD

=======
>>>>>>> 838651ea112ede6673d9ce4f82e973a4b448a2f6
