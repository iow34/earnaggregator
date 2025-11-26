# Система Трекінгу - Документація Імплементації

## Огляд

Повна система трекінгу дій користувачів від рекламних посилань до кліків на реферальні посилання бірж.

## Архітектура

```
Рекламний пост (x.com/telegram) 
    ↓
Deep Link: t.me/YourBot?start=ad_xcom_campaign123
    ↓
Telegram Bot → POST /api/v1/tracking/user/register
    ↓
tracking_users (UUID, acquisition_source)
    ↓
tracking_campaigns (auto-created)
    ↓
User переглядає сторінки бота
    ↓
Динамічні посилання: /ref?user={uuid}&source={source}&page={1|2|N}&exchange={exchange}
    ↓
Redirect Server → tracking_clicks (IP, timestamp, ref_code)
    ↓
302 Redirect → https://binance.com/ref=YOUR_CODE
    ↓
Analytics endpoints → Звіти (CTR, conversions, user journey)
```

## Компоненти

### 1. Deep Link Handler
**Файл:** `yield-telegram-bot/bot/handlers/start.py`

**Функція:** Обробка `/start` з payload

**Приклад:**
```python
# /start ad_xcom_nov2025_001
→ tracking_client.register_user(
    telegram_id=123456789,
    payload="ad_xcom_nov2025_001"
)
→ БД: user_uuid генерується, source зберігається
```

### 2. Redirect Server
**Файл:** `yield-data-service/app/api/tracking_routes.py`

**Endpoint:** `GET /ref`

**Параметри:**
- user: UUID користувача
- source: acquisition_source
- page: 1, 2, або N
- exchange: назва біржі
- ref_code: реферальний код (опціонально)

**Приклад:**
```bash
curl "http://yield-api:8000/ref?user=abc-123&source=ad_xcom_001&page=1&exchange=binance&ref_code=MY_REF"
→ 302 Redirect to https://binance.com/ref=MY_REF
→ БД: INSERT в tracking_clicks
```

### 3. Referral Link Generator
**Файл:** `yield-telegram-bot/bot/services/referral_link_generator.py`

**Використання:**
```python
from bot.services.referral_link_generator import referral_link_generator

link = await referral_link_generator.generate_link(
    telegram_id=user_id,
    exchange="binance",
    page="1"  # 1=головна, 2=продукти, N=список
)
# → http://yield-api:8000/ref?user={uuid}&source={source}&page=1&exchange=binance&ref_code={code}
```

### 4. Analytics Service
**Файл:** `yield-data-service/app/services/tracking/analytics.py`

**Методи:**
- `get_ctr_by_pages()` - CTR по сторінках
- `get_conversion_rate()` - Конверсія кліків
- `get_user_journey()` - Шлях користувача
- `get_campaign_performance()` - Ефективність кампаній

**Приклад:**
```python
# CTR аналітика
ctr_data = await tracking_analytics.get_ctr_by_pages(session)
# → [{"page": "1", "total_clicks": 100, "unique_users": 50, "ctr": 2.0}]
```

---

## Використання

### Генерація Рекламного Посилання

1. Створіть campaign в БД (опціонально, auto-created):
```sql
INSERT INTO tracking_campaigns (campaign_id, platform, start_date)
VALUES ('nov2025_001', 'xcom', NOW());
```

2. Згенеруйте посилання:
```
https://t.me/YourYieldBot?start=ad_xcom_nov2025_001
```

3. Опублікуйте в x.com/telegram/etc.

### Відстеження Результатів

**Статистика кампанії:**
```bash
curl "http://yield-api:8000/api/v1/tracking/analytics/campaign-performance?campaign_id=nov2025_001"
```

**CTR по сторінках:**
```bash
curl "http://yield-api:8000/api/v1/tracking/analytics/ctr"
```

**Конверсія:**
```bash
curl "http://yield-api:8000/api/v1/tracking/analytics/conversions?source_pattern=ad_xcom_%"
```

---

## SQL Queries для Аналітики

### Топ джерела по користувачах
```sql
SELECT acquisition_source, COUNT(*) as users
FROM tracking_users
WHERE acquisition_source LIKE 'ad_%'
GROUP BY acquisition_source
ORDER BY users DESC;
```

### Conversion rate по кампаніях
```sql
SELECT 
    u.acquisition_source,
    COUNT(DISTINCT u.user_uuid) as total_users,
    COUNT(c.id) as total_clicks,
    (COUNT(c.id)::float / COUNT(DISTINCT u.user_uuid) * 100) as conversion_rate
FROM tracking_users u
LEFT JOIN tracking_clicks c ON u.user_uuid = c.user_uuid
WHERE u.acquisition_source LIKE 'ad_%'
GROUP BY u.acquisition_source;
```

### Популярні біржі
```sql
SELECT exchange, COUNT(*) as clicks
FROM tracking_clicks
GROUP BY exchange
ORDER BY clicks DESC;
```

### User journey конкретного користувача
```sql
SELECT 
    c.timestamp,
    c.page,
    c.exchange,
    c.ref_code
FROM tracking_clicks c
WHERE c.user_uuid = 'abc-123-def-456'
ORDER BY c.timestamp ASC;
```

---

## Конфігурація

### Environment Variables

**Data Service (.env):**
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db

# Redis (для rate limiting)
REDIS_URL=redis://redis:6379/0
```

**Telegram Bot (.env):**
```env
# Tracking
DATA_SERVICE_URL=http://yield-api:8000

# Реферальні коди (замінити YOUR_REF на реальні)
REFERRAL_BINANCE=https://accounts.binance.com/register?ref=YOUR_REF
REFERRAL_BYBIT=https://www.bybit.com/invite?ref=YOUR_REF
...
```

---

## Troubleshooting

### Проблема: User не реєструється
**Симптом:** POST /tracking/user/register повертає 500

**Рішення:**
1. Перевірте БД підключення
2. Переконайтесь що таблиці створені:
```bash
docker exec -i earn-postgres psql -U yield_user -d yield_db \
  < yield-data-service/app/db/migrations/001_create_tracking_tables.sql
```

### Проблема: Redirect не працює
**Симптом:** 405 Method Not Allowed

**Рішення:**
1. Перевірте що роутери підключені в main.py:
```python
app.include_router(redirect_router)  # БЕЗ prefix
```
2. Restart сервіс: `docker restart earn-yield-api`

### Проблема: Rate limiting не спрацьовує
**Симптом:** Можна робити >10 requests/min

**Рішення:**
1. Перевірте Redis підключення
2. Перевірте middleware в main.py:
```python
app.add_middleware(
    RateLimiterMiddleware,
    redis_url=settings.redis_url,
    rate_limit=10,
    time_window=60,
    endpoints=['/ref']
)
```

---

## Наступні Кроки

1. ✅ Виправити minor issues (campaign_id парсинг)
2. ✅ Додати реферальні коди в .env
3. 📊 Налаштувати Grafana dashboard
4. 🧪 Провести навантажувальні тести
5. 🚀 Deploy на production

