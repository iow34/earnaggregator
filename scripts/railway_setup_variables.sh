#!/bin/bash
# Автоматичне налаштування змінних середовища в Railway через CLI
# Використання: ./scripts/railway_setup_variables.sh

set -e

PROJECT_DIR="/Users/user777/Documents/EarnAggregator"
cd "$PROJECT_DIR"

echo "🚀 Налаштування змінних середовища для Railway"
echo "=============================================="
echo ""

# Перевірка чи проект підключений
if ! railway status &>/dev/null; then
    echo "❌ Проект не підключений. Запустіть: railway link"
    exit 1
fi

echo "✅ Проект підключено"
echo ""

# Функція для встановлення змінних
set_variable() {
    local service=$1
    local key=$2
    local value=$3
    
    echo "  Setting $key=$value"
    railway service "$service" &>/dev/null || {
        echo "  ⚠️  Сервіс $service не знайдено. Пропускаємо..."
        return 1
    }
    
    railway variables set "$key=$value" 2>&1 | grep -v "already exists" || true
}

# =============================================================================
# Yield API Service
# =============================================================================
echo "📋 Налаштування змінних для yield-api сервісу..."
echo ""

YIELD_API_VARS=(
    "ENVIRONMENT=production"
    "LOG_LEVEL=INFO"
    "HOST=0.0.0.0"
    "SERVICE_NAME=yield-api"
)

for var in "${YIELD_API_VARS[@]}"; do
    set_variable "yield-api" "${var%%=*}" "${var#*=}" || true
done

echo "✅ Змінні для yield-api налаштовано"
echo ""
echo "⚠️  ВАЖЛИВО: Підключіть DATABASE_URL та REDIS_URL через Railway UI:"
echo "   Variables → Add Reference → Вибрати з managed сервісів"
echo ""

# =============================================================================
# Telegram Bot Service
# =============================================================================
echo "📋 Налаштування змінних для telegram-bot сервісу..."
echo ""

TELEGRAM_BOT_VARS=(
    "BOT_TOKEN=8257355469:AAHw2D9BKWKZ63v2XgMPsq6vXys3A39gg70"
    "LOG_LEVEL=INFO"
    "REQUEST_TIMEOUT=30.0"
    "TRACKING_ENABLED=true"
    "SERVICE_NAME=telegram-bot"
    "REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924"
    "REFERRAL_BYBIT=https://www.bybit.com/invite?ref=JG6XK"
    "REFERRAL_OKX=https://okx.com/join/48177058"
    "REFERRAL_MEXC=https://promote.mexc.com/r/cqUliqmW"
    "REFERRAL_BITMART=https://www.bitmart.com/uk-UA/invite/ccVsFk"
    "REFERRAL_GATE=https://www.gate.com/referral/earn-together/invite/VVKQULFXVG?ref=VVKQULFXVG&ref_type=103&utm_cmp=rXJBDjtJ&activity_id=1762853469105"
    "REFERRAL_BITGET=https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF"
    "REFERRAL_KRAKEN=https://www.kraken.com/ref/YOUR_REF"
    "REFERRAL_KUCOIN=https://www.kucoin.com/ref/YOUR_REF"
    "REFERRAL_HTX=https://www.htx.com/ref/YOUR_REF"
    "REFERRAL_NEXO=https://nexo.com/ref/cqdnii5x8f?src=web-link"
)

for var in "${TELEGRAM_BOT_VARS[@]}"; do
    set_variable "telegram-bot" "${var%%=*}" "${var#*=}" || true
done

echo "✅ Змінні для telegram-bot налаштовано"
echo ""
echo "⚠️  ВАЖЛИВО:"
echo "   1. Встановіть DATA_SERVICE_URL та TRACKING_REDIRECT_URL після отримання URL yield-api:"
echo "      railway service yield-api"
echo "      railway domain"
echo "      railway service telegram-bot"
echo "      railway variables set DATA_SERVICE_URL=https://your-yield-api.railway.app"
echo "      railway variables set TRACKING_REDIRECT_URL=https://your-yield-api.railway.app"
echo ""
echo "   2. Підключіть DATABASE_URL та REDIS_URL через Railway UI:"
echo "      Variables → Add Reference → Вибрати з managed сервісів"
echo ""

echo "✅ Налаштування завершено!"
echo ""
echo "📝 Наступні кроки:"
echo "   1. Створити сервіси в Railway UI (якщо ще не створено)"
echo "   2. Підключити DATABASE_URL та REDIS_URL через Railway UI"
echo "   3. Отримати URL yield-api та встановити DATA_SERVICE_URL та TRACKING_REDIRECT_URL"

