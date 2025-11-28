# 🔧 Команди для налаштування змінних середовища в Railway

**Дата створення:** 2025-11-28  
**Проект:** EarnAggregator

---

## ⚠️ Передумова

**ВАЖЛИВО:** Спочатку потрібно створити сервіси в Railway UI:
- PostgreSQL (managed)
- Redis (managed)
- yield-api (GitHub Repo)
- telegram-bot (GitHub Repo)

Після створення сервісів виконайте команди нижче.

---

## 🚀 Yield API Service

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

---

## 🤖 Telegram Bot Service

```bash
# Підключитися до сервісу
railway service telegram-bot

# Обов'язкові змінні
railway variables set BOT_TOKEN=REMOVED_TELEGRAM_BOT_TOKEN
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

**Після отримання URL yield-api сервісу:**

```bash
# Отримати URL yield-api
railway service yield-api
railway domain

# Встановити URL для telegram-bot
railway service telegram-bot
railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app
railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app
```

**Примітка:** `DATABASE_URL` та `REDIS_URL` потрібно підключити через Railway UI (аналогічно до yield-api).

---

## 📋 Повний список команд (копіювати всі разом)

### Yield API:

```bash
railway service yield-api
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set SERVICE_NAME=yield-api
```

### Telegram Bot:

```bash
railway service telegram-bot
railway variables set BOT_TOKEN=REMOVED_TELEGRAM_BOT_TOKEN
railway variables set LOG_LEVEL=INFO
railway variables set REQUEST_TIMEOUT=30.0
railway variables set TRACKING_ENABLED=true
railway variables set SERVICE_NAME=telegram-bot
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

---

## 🔍 Перевірка

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

2. **DATA_SERVICE_URL та TRACKING_REDIRECT_URL** - потрібно встановити після отримання URL yield-api сервісу (через `railway domain` або Railway UI).

3. **PORT** - Railway автоматично встановлює цю змінну, не потрібно встановлювати вручну.

4. **SERVICE_NAME** - обов'язково встановити для кожного application сервісу (`yield-api` або `telegram-bot`).

---

**Останнє оновлення:** 2025-11-28

