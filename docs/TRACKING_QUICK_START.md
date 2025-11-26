# Tracking System - Quick Start

## Швидкий запуск системи трекінгу

### 1. Створення таблиць

```bash
# В Docker
docker exec -i earn-postgres psql -U yield_user -d yield_db \
  < yield-data-service/app/db/migrations/001_create_tracking_tables.sql
```

### 2. Перевірка здоров'я

```bash
curl http://localhost:8000/api/v1/health
# → database_status: "healthy"
```

### 3. Тестування Deep Link

```bash
# Реєстрація користувача з рекламним посиланням
curl -X POST http://localhost:8000/api/v1/tracking/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "payload": "ad_xcom_test_campaign_001"
  }'

# Відповідь:
# {
#   "user_uuid": "abc-123-...",
#   "acquisition_source": "ad_xcom_test_campaign_001",
#   "campaign_id": "test_campaign_001",
#   "is_new_user": true
# }
```

### 4. Тестування Redirect

```bash
# Отримати UUID користувача
USER_UUID=$(curl -s http://localhost:8000/api/v1/tracking/user/123456789 | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['user_uuid'])")

# Тестовий redirect
curl -I "http://localhost:8000/ref?user=$USER_UUID&source=ad_xcom_test&page=1&exchange=binance&ref_code=TEST123"

# → 302 Redirect to binance.com
# → tracking_clicks: +1 запис
```

### 5. Перевірка Analytics

```bash
# CTR по сторінках
curl "http://localhost:8000/api/v1/tracking/analytics/ctr"

# Conversions
curl "http://localhost:8000/api/v1/tracking/analytics/conversions?source_pattern=ad_xcom_%"

# User journey
curl "http://localhost:8000/api/v1/tracking/analytics/user-journey/$USER_UUID"

# Campaign performance
curl "http://localhost:8000/api/v1/tracking/analytics/campaign-performance"
```

---

## Формати Deep Link

### Рекламні кампанії:
```
t.me/YourBot?start=ad_{platform}_{campaign_id}

Приклади:
- ad_xcom_november_2025_001
- ad_telegram_ads_promo_alpha
- ad_influencer_crypto_tony_campaign
```

### Тестові посилання:
```
t.me/YourBot?start=test_{platform}_{campaign_id}

Приклади:
- test_xcom_staging_001
- test_telegram_beta_test
```

### Organic (без посилання):
```
t.me/YourBot (без ?start=)
або
t.me/YourBot?start=
```

---

## Платформи (Whitelist)

Дозволені платформи для `{platform}`:
- xcom
- telegram / telegram_ads
- facebook
- reddit
- website / website_banner
- email / email_campaign
- influencer
- youtube
- instagram
- tiktok
- discord
- linkedin
- twitter
- medium
- blog

---

## Сторінки Бота

- **page=1** - Головна сторінка (/start)
- **page=2** - Продукти конкретної біржі
- **page=N** - Список всіх бірж

---

## SQL Запити для Аналітики

### Топ джерела
```sql
SELECT acquisition_source, COUNT(*) 
FROM tracking_users 
GROUP BY acquisition_source 
ORDER BY COUNT(*) DESC;
```

### Conversion rate
```sql
SELECT 
    u.acquisition_source,
    COUNT(DISTINCT u.user_uuid) as users,
    COUNT(c.id) as clicks,
    (COUNT(c.id)::float / COUNT(DISTINCT u.user_uuid) * 100) as conversion_rate
FROM tracking_users u
LEFT JOIN tracking_clicks c ON u.user_uuid = c.user_uuid
GROUP BY u.acquisition_source;
```

### Time to first click
```sql
SELECT 
    u.telegram_id,
    u.acquisition_source,
    MIN(c.timestamp) - u.joined_at as time_to_first_click
FROM tracking_users u
JOIN tracking_clicks c ON u.user_uuid = c.user_uuid
GROUP BY u.telegram_id, u.acquisition_source, u.joined_at
ORDER BY time_to_first_click;
```

---

## Troubleshooting

### Таблиці не створюються
```bash
# Перевірити чи існують
docker exec earn-postgres psql -U yield_user -d yield_db \
  -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'tracking%';"

# Якщо пусто - запустити міграцію
docker exec -i earn-postgres psql -U yield_user -d yield_db \
  < yield-data-service/app/db/migrations/001_create_tracking_tables.sql
```

### API повертає 500
```bash
# Перевірити логи
docker logs earn-yield-api --tail 50

# Перезапустити сервіс
docker restart earn-yield-api
```

### Rate limiting не працює
```bash
# Перевірити Redis
docker exec earn-redis redis-cli PING
# → PONG

# Перевірити ключі rate limit
docker exec earn-redis redis-cli KEYS "rate_limit:*"
```

---

## Next Steps

1. ✅ Замінити реферальні коди в .env
2. 📊 Налаштувати Grafana dashboard
3. 🧪 Провести навантажувальні тести
4. 🚀 Deploy на production

**Готовність:** 95%

