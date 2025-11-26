# ⚡ PostgreSQL Quick Reference - Швидкий Довідник

## 🚀 Швидкий Старт

```bash
# Підключитись до БД
psql -U yield_user -d yield_db

# Або через Docker
docker exec -it yield-postgres psql -U yield_user -d yield_db
```

---

## 📊 Найчастіше Використовувані Запити

### Топ-10 за APY

```sql
SELECT exchange, symbol, name, apy, lock_period_days
FROM earn_products
WHERE is_active = true
ORDER BY apy DESC
LIMIT 10;
```

### Пошук по Монеті

```sql
SELECT exchange, name, apy, lock_period_days, min_amount
FROM earn_products
WHERE symbol = 'BTC' AND is_active = true
ORDER BY apy DESC;
```

### Статистика по Біржах

```sql
SELECT
    exchange,
    COUNT(*) as total_products,
    AVG(apy) as avg_apy,
    MAX(apy) as max_apy
FROM earn_products
WHERE is_active = true
GROUP BY exchange;
```

### Тільки Flexible (без блокування)

```sql
SELECT exchange, symbol, name, apy
FROM earn_products
WHERE is_active = true AND lock_period_days = 0
ORDER BY apy DESC;
```

---

## 🔧 Адміністрування

### Розмір Таблиць

```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::text)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::text) DESC;
```

### Кількість Записів

```sql
SELECT
    'earn_products' as table, COUNT(*) as count FROM earn_products
UNION ALL
SELECT
    'earn_products_history' as table, COUNT(*) FROM earn_products_history;
```

### Очищення

```sql
VACUUM ANALYZE earn_products;
```

---

## 💾 Backup

```bash
# Створити backup
pg_dump -U yield_user -d yield_db > backup_$(date +%Y%m%d).sql

# Стиснутий backup
pg_dump -U yield_user -d yield_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Відновити
psql -U yield_user -d yield_db < backup_20241013.sql
```

---

## 🔍 Моніторинг Оновлень

### Перевірити останнє оновлення

```sql
SELECT
    exchange,
    MAX(last_api_sync) as last_sync,
    COUNT(*) as products_count
FROM earn_products
WHERE is_active = true
GROUP BY exchange;
```

### Лог синхронізації

```sql
SELECT
    exchange,
    status,
    products_synced,
    started_at,
    completed_at
FROM api_sync_log
ORDER BY started_at DESC
LIMIT 10;
```

---

## ⚠️ Troubleshooting

### Знайти дублікати

```sql
SELECT exchange, product_id, COUNT(*)
FROM earn_products
GROUP BY exchange, product_id
HAVING COUNT(*) > 1;
```

### Перевірити індекси

```sql
\di
```

### Активні з'єднання

```sql
SELECT count(*) FROM pg_stat_activity;
```

---

## 📤 Експорт Даних

### CSV

```sql
COPY (
    SELECT * FROM earn_products WHERE is_active = true
) TO '/tmp/products.csv' WITH CSV HEADER;
```

### JSON (через psql)

```bash
psql -U yield_user -d yield_db -c "SELECT json_agg(t) FROM (SELECT * FROM earn_products WHERE is_active = true LIMIT 100) t" > products.json
```

---

**Для детальної інформації дивіться:** `POSTGRESQL_GUIDE.md`
