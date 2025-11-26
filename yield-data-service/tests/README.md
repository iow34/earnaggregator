# 🧪 Тести для Yield Data Service

## Тестові файли

### 1. `simple_test_api.py` - Швидкий тест (РЕКОМЕНДОВАНО)

Простий скрипт для швидкої перевірки API однієї криптовалюти.

**Запуск:**

```bash
cd /Users/user777/Documents/EarnAggregator/yield-data-service
python tests/simple_test_api.py
```

**Що робить:**

- Тестує BTC на Binance та Bybit
- Виводить топ-3 продукти за APY
- Зберігає повні дані в JSON файли

---

### 2. `test_exchanges_real_data.py` - Повний тест

Детальний тест для 5 криптовалют (BTC, ETH, USDT, BNB, SOL).

**Запуск:**

```bash
cd /Users/user777/Documents/EarnAggregator/yield-data-service
python tests/test_exchanges_real_data.py
```

**Що робить:**

- Тестує 5 популярних криптовалют
- Виводить детальну статистику
- Зберігає результати в JSON з timestamp

---

## 📋 Підготовка

### 1. Створіти `.env` файл

У **кореневій директорії** `/Users/user777/Documents/EarnAggregator/` створіть файл `.env`:

```bash
# API ключі Binance
BINANCE_API_KEY=ваш_binance_api_key
BINANCE_API_SECRET=ваш_binance_api_secret

# API ключі Bybit
BYBIT_API_KEY=ваш_bybit_api_key
BYBIT_API_SECRET=ваш_bybit_api_secret

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/yield_db
```

### 2. Отримати API ключі

**Binance:**

1. Зайдіть на https://www.binance.com/
2. Акаунт → API Management
3. Створіть нові ключі
4. **ВАЖЛИВО:** Увімкніть тільки "Enable Reading" (без Trading!)

**Bybit:**

1. Зайдіть на https://www.bybit.com/
2. API Management
3. Створіть нові ключі
4. **ВАЖЛИВО:** Надайте тільки Read-Only права!

### 3. Встановити залежності

```bash
cd /Users/user777/Documents/EarnAggregator
pip install -r requirements.txt
```

---

## 🚀 Приклад виводу

```
============================================================
  🚀 ШВИДКИЙ ТЕСТ API БІРЖ
============================================================

Тестовий актив: BTC

============================================================
  🔍 Binance - Тестування BTC
============================================================

⏳ Отримання даних для BTC...
✅ Знайдено 15 продуктів

📊 Топ-3 продукти за APY:

1. BTC Flexible Savings
   APY: 5.20%
   Мін. сума: 0.001
   Блокування: Flexible

2. BTC Locked Savings
   APY: 8.50%
   Мін. сума: 0.01
   Блокування: 90 днів

3. BTC Locked Savings (30 днів)
   APY: 7.30%
   Мін. сума: 0.01
   Блокування: 30 днів

💾 Повні дані збережено в: tests/data/binance_BTC_data.json
```

---

## 📊 Структура JSON результату

Приклад збереженого файлу `binance_BTC_data.json`:

```json
[
  {
    "id": "binance_simple_flex_BTC",
    "symbol": "BTC",
    "name": "BTC Flexible Savings",
    "provider": "Binance",
    "apy": 5.2,
    "is_cefi": true,
    "min_amount": 0.001,
    "lock_period_days": 0,
    "is_active": true,
    "description": "Bitcoin Flexible Savings",
    "website_url": "https://www.binance.com/en/earn",
    "raw_data": { ... }
  }
]
```

---

## ⚠️ Типові помилки

### 1. "API ключі не налаштовані"

**Рішення:** Створіть `.env` файл з API ключами

### 2. "ModuleNotFoundError: No module named 'app'"

**Рішення:** Запускайте з директорії `yield-data-service`:

```bash
cd /Users/user777/Documents/EarnAggregator/yield-data-service
python tests/simple_test_api.py
```

### 3. "HTTP 401 Unauthorized"

**Рішення:** Перевірте правильність API ключів у `.env`

### 4. "HTTP 403 Forbidden"

**Рішення:**

- Перевірте IP whitelist на біржі
- Переконайтеся що ключі мають Read права

### 5. "Продуктів не знайдено"

**Можливі причини:**

- Актив не підтримується біржею
- Binance/Bybit API endpoint змінився
- Географічні обмеження

---

## 🔧 Налаштування тестів

Щоб змінити тестовий актив у `simple_test_api.py`:

```python
# Змініть рядок 90:
test_asset = "BTC"  # Змініть на ETH, USDT, BNB, тощо
```

Щоб протестувати інші активи у `test_exchanges_real_data.py`:

```python
# Змініть рядок 18:
TEST_ASSETS = ["BTC", "ETH", "USDT", "BNB", "SOL"]
```

---

## 📝 Логування

Логи зберігаються в:

- `/Users/user777/Documents/EarnAggregator/yield-data-service/logs/app.log`
- `/Users/user777/Documents/EarnAggregator/yield-data-service/logs/errors.log`

Переглянути останні логи:

```bash
tail -f yield-data-service/logs/app.log
```

---

## 🐛 Дебаг

Для детального виводу помилок, додайте у тестовий файл:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📞 Підтримка

Якщо виникають проблеми:

1. Перевірте `.env` файл
2. Перегляньте логи
3. Переконайтеся що API ключі мають Read-Only права
4. Перевірте чи не заблоковані запити до API (VPN, Firewall)
