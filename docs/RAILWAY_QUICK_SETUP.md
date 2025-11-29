# ⚡ Швидке налаштування Railway через CLI

**Дата створення:** 2025-11-28

---

## ✅ Що вже зроблено

- ✅ Railway CLI встановлено та авторизовано
- ✅ Проект "EarnAggregator" створено та підключено
- ✅ Скрипт для автоматичного налаштування створено

---

## 🚀 Швидкий старт

### Крок 1: Створити сервіси в Railway UI

**Обов'язково створити через веб-інтерфейс:**

1. Відкрити проект: https://railway.com/project/5c18f72a-df91-47d3-a344-ef946e0a6643

2. Створити сервіси:
   - **PostgreSQL** → New → Database → PostgreSQL
   - **Redis** → New → Database → Redis
   - **yield-api** → New → GitHub Repo → `iow34/earnaggregator` → Назвати `yield-api`
   - **telegram-bot** → New → GitHub Repo → `iow34/earnaggregator` → Назвати `telegram-bot`

### Крок 2: Запустити скрипт налаштування

```bash
cd /Users/user777/Documents/EarnAggregator
./scripts/railway_setup_variables.sh
```

Скрипт автоматично налаштує всі змінні для обох сервісів.

### Крок 3: Підключити DATABASE_URL та REDIS_URL

**Через Railway UI:**

1. Відкрити **yield-api** service
2. Перейти в **Variables**
3. Натиснути **Add Reference**
4. Вибрати `DATABASE_URL` з **PostgreSQL** service
5. Повторити для `REDIS_URL` з **Redis** service
6. Повторити для **telegram-bot** service

### Крок 4: Отримати URL yield-api та налаштувати DATA_SERVICE_URL

```bash
# Отримати URL yield-api
railway service yield-api
railway domain

# Встановити URL для telegram-bot
railway service telegram-bot
railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app
railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app
```

---

## 📋 Ручне налаштування (якщо скрипт не працює)

### Yield API Service

```bash
railway service yield-api
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set SERVICE_NAME=yield-api
```

### Telegram Bot Service

```bash
railway service telegram-bot
railway variables set BOT_TOKEN=8257355469:AAHw2D9BKWKZ63v2XgMPsq6vXys3A39gg70
railway variables set LOG_LEVEL=INFO
railway variables set REQUEST_TIMEOUT=30.0
railway variables set TRACKING_ENABLED=true
railway variables set SERVICE_NAME=telegram-bot

# Реферальні посилання
railway variables set REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924
railway variables set REFERRAL_BYBIT=https://www.bybit.com/invite?ref=JG6XK
railway variables set REFERRAL_OKX=https://okx.com/join/48177058
railway variables set REFERRAL_MEXC=https://promote.mexc.com/r/cqUliqmW
railway variables set REFERRAL_BITMART=https://www.bitmart.com/uk-UA/invite/ccVsFk
railway variables set REFERRAL_GATE=https://www.gate.com/referral/earn-together/invite/VVKQULFXVG?ref=VVKQULFXVG&ref_type=103&utm_cmp=rXJBDjtJ&activity_id=1762853469105
railway variables set REFERRAL_BITGET=https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF
railway variables set REFERRAL_KRAKEN=https://www.kraken.com/ref/YOUR_REF
railway variables set REFERRAL_KUCOIN=https://www.kucoin.com/ref/YOUR_REF
railway variables set REFERRAL_HTX=https://www.htx.com/ref/YOUR_REF
railway variables set REFERRAL_NEXO=https://nexo.com/ref/cqdnii5x8f?src=web-link

# Після отримання URL yield-api:
railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app
railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app
```

---

## 🔍 Перевірка налаштувань

### Перевірити змінні:

```bash
# Yield API
railway service yield-api
railway variables

# Telegram Bot
railway service telegram-bot
railway variables
```

### Перевірити через Railway UI:

1. Відкрити сервіс
2. Перейти в **Variables**
3. Перевірити всі змінні

---

## ⚠️ Важливі зауваження

1. **DATABASE_URL та REDIS_URL** - Railway автоматично створює ці змінні для managed сервісів, але їх потрібно підключити до application сервісів через "Add Reference" в Railway UI.

2. **DATA_SERVICE_URL та TRACKING_REDIRECT_URL** - потрібно встановити після отримання URL yield-api сервісу.

3. **PORT** - Railway автоматично встановлює цю змінну, не потрібно встановлювати вручну.

4. **SERVICE_NAME** - обов'язково встановити для кожного application сервісу (`yield-api` або `telegram-bot`).

---

## 🆘 Troubleshooting

### Проблема: "No service linked"

**Рішення:**
```bash
railway service <service-name>
```

### Проблема: Сервіс не знайдено

**Рішення:**
1. Перевірити чи сервіс створено в Railway UI
2. Перевірити назву сервісу (має бути точно `yield-api` або `telegram-bot`)

### Проблема: Змінні не встановлюються

**Рішення:**
1. Перевірити чи правильний сервіс підключено: `railway service`
2. Спробувати встановити вручну: `railway variables set KEY=value`

---

**Останнє оновлення:** 2025-11-28

