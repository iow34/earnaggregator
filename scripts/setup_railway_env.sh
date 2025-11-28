#!/bin/bash
# Скрипт для налаштування змінних середовища в Railway через CLI
# Використання: ./scripts/setup_railway_env.sh

set -e

echo "🚀 Налаштування змінних середовища для Railway"
echo "=============================================="

# Перевірка чи проект підключений
if ! railway status &>/dev/null; then
    echo "❌ Проект не підключений. Запустіть: railway link"
    exit 1
fi

echo "✅ Проект підключено"

# Змінні для Yield API Service
echo ""
echo "📋 Налаштування змінних для yield-api сервісу..."
echo "Примітка: Спочатку потрібно створити сервіс 'yield-api' в Railway UI"
echo ""
echo "Команди для налаштування:"
echo "railway service yield-api"
echo "railway variables set ENVIRONMENT=production"
echo "railway variables set LOG_LEVEL=INFO"
echo "railway variables set HOST=0.0.0.0"
echo "railway variables set SERVICE_NAME=yield-api"
echo ""
echo "DATABASE_URL та REDIS_URL будуть автоматично підключені після створення managed сервісів"

# Змінні для Telegram Bot Service
echo ""
echo "📋 Налаштування змінних для telegram-bot сервісу..."
echo "Примітка: Спочатку потрібно створити сервіс 'telegram-bot' в Railway UI"
echo ""
echo "Команди для налаштування:"
echo "railway service telegram-bot"
echo "railway variables set BOT_TOKEN=REMOVED_TELEGRAM_BOT_TOKEN"
echo "railway variables set DATA_SERVICE_URL=<URL_your_yield_api_service>"
echo "railway variables set TRACKING_REDIRECT_URL=<URL_your_yield_api_service>"
echo "railway variables set LOG_LEVEL=INFO"
echo "railway variables set REQUEST_TIMEOUT=30.0"
echo "railway variables set TRACKING_ENABLED=true"
echo "railway variables set SERVICE_NAME=telegram-bot"
echo ""
echo "Реферальні посилання:"
echo "railway variables set REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924"
echo "railway variables set REFERRAL_BYBIT=https://www.bybit.com/invite?ref=JG6XK"
echo "railway variables set REFERRAL_OKX=https://okx.com/join/48177058"
echo "railway variables set REFERRAL_MEXC=https://promote.mexc.com/r/cqUliqmW"
echo "railway variables set REFERRAL_BITMART=https://www.bitmart.com/uk-UA/invite/ccVsFk"
echo "railway variables set REFERRAL_GATE=https://www.gate.com/referral/earn-together/invite/VVKQULFXVG?ref=VVKQULFXVG&ref_type=103&utm_cmp=rXJBDjtJ&activity_id=1762853469105"
echo "railway variables set REFERRAL_BITGET=https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF"
echo "railway variables set REFERRAL_KRAKEN=https://www.kraken.com/ref/YOUR_REF"
echo "railway variables set REFERRAL_KUCOIN=https://www.kucoin.com/ref/YOUR_REF"
echo "railway variables set REFERRAL_HTX=https://www.htx.com/ref/YOUR_REF"
echo "railway variables set REFERRAL_NEXO=https://nexo.com/ref/cqdnii5x8f?src=web-link"
echo ""
echo "DATABASE_URL та REDIS_URL будуть автоматично підключені після створення managed сервісів"

echo ""
echo "✅ Інструкції виведено"
echo ""
echo "⚠️  ВАЖЛИВО:"
echo "1. Спочатку створіть сервіси в Railway UI:"
echo "   - PostgreSQL (managed)"
echo "   - Redis (managed)"
echo "   - yield-api (GitHub Repo)"
echo "   - telegram-bot (GitHub Repo)"
echo ""
echo "2. Потім виконайте команди вище для налаштування змінних"
echo ""
echo "3. Підключіть DATABASE_URL та REDIS_URL через Railway UI:"
echo "   Variables → Add Reference → Вибрати з managed сервісів"

