# 🚂 Налаштування Railway через CLI

**Дата створення:** 2025-11-28  
**Проект:** EarnAggregator

---

## ✅ Статус

- ✅ Railway CLI встановлено та авторизовано
- ✅ Проект "EarnAggregator" створено та підключено
- ⚠️ Сервіси потрібно створити в Railway UI

---

## 📋 Крок 1: Створення сервісів

**Важливо:** Сервіси потрібно створити через Railway веб-інтерфейс, оскільки CLI не підтримує створення сервісів в неінтерактивному режимі.

### 1.1. Відкрити проект на Railway

Перейти на: https://railway.com/project/5c18f72a-df91-47d3-a344-ef946e0a6643

### 1.2. Створити сервіси

1. **PostgreSQL (managed):**

   - Натиснути "New" → "Database" → "PostgreSQL"
   - Railway автоматично створить `DATABASE_URL`

2. **Redis (managed):**

   - Натиснути "New" → "Database" → "Redis"
   - Railway автоматично створить `REDIS_URL`

3. **Yield API:**

   - Натиснути "New" → "GitHub Repo"
   - Вибрати репозиторій: `iow34/earnaggregator`
   - Назвати сервіс: `yield-api`
   - Railway автоматично встановить `PORT`

4. **Telegram Bot:**
   - Натиснути "New" → "GitHub Repo" (ще раз)
   - Вибрати репозиторій: `iow34/earnaggregator`
   - Назвати сервіс: `telegram-bot`

---

## 📋 Крок 2: Налаштування змінних через CLI

### 2.1. Yield API Service

```bash
# Підключитися до сервісу
railway service yield-api

# Встановити змінні
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set SERVICE_NAME=yield-api
```

**Примітка:** `DATABASE_URL` та `REDIS_URL` потрібно підключити через Railway UI:

- Variables → Add Reference → Вибрати `DATABASE_URL` з PostgreSQL service
- Variables → Add Reference → Вибрати `REDIS_URL` з Redis service

### 2.2. Telegram Bot Service

```bash
# Підключитися до сервісу
railway service telegram-bot

# Обов'язкові змінні
railway variables set BOT_TOKEN=REMOVED_TELEGRAM_BOT_TOKEN
railway variables set LOG_LEVEL=INFO
railway variables set REQUEST_TIMEOUT=30.0
railway variables set TRACKING_ENABLED=true
railway variables set SERVICE_NAME=telegram-bot

# DATA_SERVICE_URL та TRACKING_REDIRECT_URL потрібно встановити після отримання URL yield-api сервісу
# railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app
# railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app

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
```

**Примітка:** `DATABASE_URL` та `REDIS_URL` потрібно підключити через Railway UI (аналогічно до yield-api).

---

## 🔧 Автоматичне налаштування (скрипт)

Створено скрипт `scripts/setup_railway_env.sh` для автоматичного налаштування.

**Використання:**

```bash
./scripts/setup_railway_env.sh
```

Скрипт виведе всі необхідні команди для налаштування.

---

## 📝 Покрокова інструкція

### Крок 1: Створити сервіси в Railway UI

1. Відкрити проект: https://railway.com/project/5c18f72a-df91-47d3-a344-ef946e0a6643
2. Створити PostgreSQL service
3. Створити Redis service
4. Створити yield-api service (GitHub Repo)
5. Створити telegram-bot service (GitHub Repo)

### Крок 2: Налаштувати змінні для yield-api

```bash
cd /Users/user777/Documents/EarnAggregator
railway service yield-api
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set SERVICE_NAME=yield-api
```

### Крок 3: Підключити DATABASE_URL та REDIS_URL для yield-api

Через Railway UI:

1. Відкрити yield-api service
2. Перейти в "Variables"
3. Натиснути "Add Reference"
4. Вибрати `DATABASE_URL` з PostgreSQL service
5. Повторити для `REDIS_URL` з Redis service

### Крок 4: Отримати URL yield-api сервісу

```bash
railway service yield-api
railway domain
```

Або через Railway UI → yield-api service → Settings → Generate Domain

### Крок 5: Налаштувати змінні для telegram-bot

```bash
railway service telegram-bot
railway variables set BOT_TOKEN=REMOVED_TELEGRAM_BOT_TOKEN
railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app
railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app
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
```

### Крок 6: Підключити DATABASE_URL та REDIS_URL для telegram-bot

Аналогічно до кроку 3, але для telegram-bot service.

---

## 🔍 Перевірка налаштувань

### Перевірити змінні для yield-api:

```bash
railway service yield-api
railway variables
```

### Перевірити змінні для telegram-bot:

```bash
railway service telegram-bot
railway variables
```

---

## ⚠️ Важливі зауваження

1. **DATABASE_URL та REDIS_URL** - Railway автоматично створює ці змінні для managed сервісів, але їх потрібно підключити до application сервісів через "Add Reference" в Railway UI.

2. **DATA_SERVICE_URL та TRACKING_REDIRECT_URL** - потрібно встановити після отримання URL yield-api сервісу (через `railway domain` або Railway UI).

3. **PORT** - Railway автоматично встановлює цю змінну, не потрібно встановлювати вручну.

4. **SERVICE_NAME** - обов'язково встановити для кожного application сервісу (`yield-api` або `telegram-bot`).

---

## 🆘 Troubleshooting

### Проблема: "No service linked"

**Рішення:**

```bash
railway service <service-name>
```

### Проблема: "No project linked"

**Рішення:**

```bash
railway link
```

### Проблема: Змінні не відображаються

**Рішення:**

1. Перевірити чи правильний сервіс підключено: `railway service`
2. Перевірити змінні: `railway variables`
3. Перевірити через Railway UI

---

**Останнє оновлення:** 2025-11-28
