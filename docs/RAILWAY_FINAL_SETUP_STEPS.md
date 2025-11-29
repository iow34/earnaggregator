# 🚀 Фінальні кроки налаштування Railway

**Дата:** 2025-11-28  
**Статус:** Сервіс запущено, потрібно завершити налаштування

---

## ✅ Що вже зроблено

1. ✅ Dockerfile виправлено (шлях до telegram-bot)
2. ✅ Змінні середовища налаштовано:
   - `SERVICE_NAME=yield-api`
   - `ENVIRONMENT=production`
   - `LOG_LEVEL=INFO`
   - `HOST=0.0.0.0`
   - `DATABASE_URL` (підключено з Postgres)
3. ✅ Домен згенеровано: `https://earnaggregator-production.up.railway.app`
4. ✅ Сервіс запущено успішно

---

## ⚠️ Що потрібно зробити

### 🔴 Крок 1: Налаштувати REDIS_URL (КРИТИЧНО!)

**Проблема:** Сервіс не працює через відсутність `REDIS_URL`. `RateLimiterMiddleware` потребує Redis для роботи.

**Через Railway UI:**

1. Відкрити сервіс `earnaggregator` в Railway UI
2. Перейти в **Variables** → **Add Reference**
3. Вибрати `REDIS_URL` з сервісу **Redis**
4. Зберегти

**Перевірка:**

```bash
railway variables | grep REDIS_URL
```

**Після налаштування:** Railway автоматично перезапустить сервіс з новою змінною.

---

### Крок 2: Виконати міграції бази даних

**Варіант 1: Через Railway CLI (рекомендовано)**

```bash
# Підключитися до сервісу
railway service earnaggregator

# Виконати міграції
railway run python -m scripts.run_all_migrations
```

**Варіант 2: Через Railway Shell**

1. В Railway UI відкрити сервіс `earnaggregator`
2. Перейти в **Deployments** → вибрати останній deployment
3. Натиснути **Shell** (або **View Logs** → **Shell**)
4. Виконати:

```bash
python -m scripts.run_all_migrations
```

**Очікуваний результат:**

```
✅ Підключення до БД успішне
📄 Виконуємо міграцію: 001_create_tracking_tables.sql
✅ Міграція 001_create_tracking_tables.sql виконано успішно
📄 Виконуємо міграцію: 002_create_simple_clicks_table.sql
✅ Міграція 002_create_simple_clicks_table.sql виконано успішно
📄 Виконуємо міграцію: 003_create_priority_products_table.sql
✅ Міграція 003_create_priority_products_table.sql виконано успішно
✅ Всі міграції виконано успішно!
```

---

### Крок 3: Перевірити health check

**Через браузер:**

```
https://earnaggregator-production.up.railway.app/health
```

**Очікуваний результат:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": {
    "connected": true,
    "status": "healthy"
  }
}
```

**Через curl:**

```bash
curl https://earnaggregator-production.up.railway.app/health
```

**Через Railway CLI:**

```bash
railway run curl http://localhost:$PORT/health
```

---

### Крок 4: Перевірити API endpoints

**Root endpoint:**

```bash
curl https://earnaggregator-production.up.railway.app/
```

**API Health check:**

```bash
curl https://earnaggregator-production.up.railway.app/api/v1/health
```

**Список бірж:**

```bash
curl https://earnaggregator-production.up.railway.app/api/v1/exchanges
```

---

### Крок 5: Налаштувати Telegram Bot сервіс (опціонально)

Якщо потрібно запустити Telegram Bot:

1. **Створити новий сервіс в Railway UI:**

   - New → GitHub Repo → `iow34/earnaggregator`
   - Назвати: `telegram-bot`

2. **Налаштувати змінні середовища:**

```bash
railway service telegram-bot
railway variables set SERVICE_NAME=telegram-bot
railway variables set BOT_TOKEN=your_bot_token_here
railway variables set DATA_SERVICE_URL=https://earnaggregator-production.up.railway.app
railway variables set TRACKING_REDIRECT_URL=https://earnaggregator-production.up.railway.app
railway variables set LOG_LEVEL=INFO
railway variables set REQUEST_TIMEOUT=30.0
railway variables set TRACKING_ENABLED=true
```

3. **Підключити DATABASE_URL та REDIS_URL:**

   - Variables → Add Reference → `DATABASE_URL` з Postgres
   - Variables → Add Reference → `REDIS_URL` з Redis

4. **Додати реферальні посилання** (опціонально):

```bash
railway variables set REFERRAL_BINANCE=https://accounts.binance.com/register?ref=39794924
railway variables set REFERRAL_BYBIT=https://www.bybit.com/invite?ref=JG6XK
# ... інші реферальні посилання
```

---

## 🔍 Перевірка роботи сервісу

### 1. Перевірити логи

```bash
railway logs --deployment <deployment-id>
```

Або через Railway UI:

- Deployments → вибрати deployment → View Logs

**Очікувані логи:**

```
🚀 Запуск yield-api сервісу...
📦 Версія: 1.0.0
✅ Redis кеш ініціалізовано
✅ Реєстр бірж ініціалізовано
✅ Scheduler запущено
✅ EarnAggregator Data Service запущено успішно
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 2. Перевірити метрики

```bash
curl https://earnaggregator-production.up.railway.app/metrics
```

### 3. Перевірити документацію API

Відкрити в браузері:

```
https://earnaggregator-production.up.railway.app/docs
```

---

## 📋 Чеклист завершення

- [ ] REDIS_URL налаштовано через Railway UI
- [ ] Міграції БД виконано успішно
- [ ] Health check повертає `"status": "healthy"`
- [ ] API endpoints працюють коректно
- [ ] Документація API доступна (`/docs`)
- [ ] Метрики Prometheus доступні (`/metrics`)
- [ ] (Опціонально) Telegram Bot сервіс налаштовано

---

## 🆘 Troubleshooting

### Проблема: Health check повертає "degraded"

**Можливі причини:**

1. Redis не підключено (перевірити REDIS_URL)
2. База даних не доступна (перевірити DATABASE_URL)
3. Міграції не виконано

**Рішення:**

1. Перевірити змінні середовища
2. Виконати міграції БД
3. Перевірити логи сервісу

### Проблема: API endpoints не працюють

**Можливі причини:**

1. Сервіс не запущено
2. Неправильний PORT
3. Проблеми з підключенням до БД

**Рішення:**

1. Перевірити статус deployment
2. Перевірити логи
3. Перевірити змінні середовища

### Проблема: Міграції не виконуються

**Рішення:**

1. Перевірити чи файли міграцій копіюються в Docker образ
2. Перевірити шлях до міграцій в скрипті
3. Виконати міграції вручну через Railway Shell

---

## 📝 Наступні кроки після завершення

1. **Моніторинг:**

   - Налаштувати алерти в Railway
   - Підключити зовнішній моніторинг (якщо потрібно)

2. **Оптимізація:**

   - Налаштувати автопідключення до БД
   - Оптимізувати кешування
   - Налаштувати резервне копіювання БД

3. **Безпека:**
   - Обмежити CORS origins
   - Налаштувати rate limiting
   - Додати аутентифікацію для адмін endpoints

---

**Останнє оновлення:** 2025-11-28
