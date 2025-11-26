# 🗄️ PostgreSQL Database - Інструкція та Керівництво

## 📋 Зміст

1. [Встановлення та Налаштування](#встановлення-та-налаштування)
2. [Структура Бази Даних](#структура-бази-даних)
3. [Основні Команди](#основні-команди)
4. [Робота з Даними](#робота-з-даними)
5. [Оновлення Даних (кожні 60 хвилин)](#оновлення-даних)
6. [Backup та Restore](#backup-та-restore)
7. [Моніторинг та Оптимізація](#моніторинг-та-оптимізація)
8. [Troubleshooting](#troubleshooting)

---

## 📦 Встановлення та Налаштування

### Встановлення PostgreSQL

#### macOS:

```bash
# Використовуючи Homebrew
brew install postgresql@15
brew services start postgresql@15

# Перевірка статусу
brew services list | grep postgresql
```

#### Ubuntu/Debian:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib

# Запуск сервісу
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Docker (Рекомендовано для розробки):

```bash
# Запуск PostgreSQL в Docker
docker run -d \
  --name yield-postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_USER=yield_user \
  -e POSTGRES_DB=yield_db \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Перевірка
docker ps | grep postgres
```

---

### Створення Бази Даних

```bash
# Підключення до PostgreSQL
psql -U postgres

# Створення користувача
CREATE USER yield_user WITH PASSWORD 'your_secure_password';

# Створення бази даних
CREATE DATABASE yield_db OWNER yield_user;

# Надання прав
GRANT ALL PRIVILEGES ON DATABASE yield_db TO yield_user;

# Вихід
\q
```

---

### Налаштування .env файлу

У кореневій директорії `/Users/user777/Documents/EarnAggregator/.env`:

```env
# PostgreSQL підключення
DATABASE_URL=postgresql://yield_user:your_secure_password@localhost:5432/yield_db

# Або для Docker
DATABASE_URL=postgresql://yield_user:your_password@localhost:5432/yield_db
```

---

## 🏗️ Структура Бази Даних

### Рекомендована Структура

**Рішення:** Використовуємо **одну таблицю** `earn_products` для всіх бірж з JSONB колонкою для специфічних даних.

**Переваги:**

- ✅ Простота запитів (порівняння між біржами)
- ✅ Уніфікована структура
- ✅ Гнучкість (JSONB для унікальних полів)
- ✅ Легко додавати нові біржі

**Альтернатива:** Окремі таблиці для кожної біржі (не рекомендується, складніше для порівняння)

---

### Таблиця 1: `earn_products` (Головна таблиця)

**Призначення:** Зберігає актуальні Earn продукти з усіх бірж

```sql
CREATE TABLE earn_products (
    -- Первинний ключ
    id SERIAL PRIMARY KEY,

    -- Унікальний ідентифікатор продукту (з API)
    product_id VARCHAR(100) UNIQUE NOT NULL,

    -- Базова інформація
    exchange VARCHAR(50) NOT NULL,              -- Binance, Bybit
    symbol VARCHAR(20) NOT NULL,                -- BTC, ETH, USDT
    name VARCHAR(200) NOT NULL,                 -- BTC Flexible Savings

    -- Фінансові дані
    apy DECIMAL(10, 6) NOT NULL,                -- APY у відсотках (5.25)
    min_amount DECIMAL(20, 8) DEFAULT 0,        -- Мінімальна сума
    max_amount DECIMAL(20, 8),                  -- Максимальна сума (може бути NULL)

    -- Умови продукту
    lock_period_days INTEGER DEFAULT 0,         -- Днів блокування (0 = Flexible)
    product_type VARCHAR(50),                   -- Flexible, Locked, Fixed
    category VARCHAR(50),                       -- FlexibleSaving, OnChain, тощо

    -- Статус
    is_active BOOLEAN DEFAULT true,             -- Чи доступний продукт
    is_cefi BOOLEAN DEFAULT true,               -- CeFi чи DeFi

    -- Додаткова інформація
    description TEXT,                           -- Опис продукту
    website_url VARCHAR(500),                   -- Посилання
    risk_level VARCHAR(20) DEFAULT 'Medium',    -- Low, Medium, High

    -- Спеціфічні дані біржі (гнучка колонка)
    exchange_specific_data JSONB,               -- Унікальні поля кожної біржі

    -- Часові мітки
    created_at TIMESTAMP DEFAULT NOW(),         -- Коли додано
    updated_at TIMESTAMP DEFAULT NOW(),         -- Останнє оновлення
    last_api_sync TIMESTAMP DEFAULT NOW(),      -- Останнє оновлення з API

    -- Індекси
    CONSTRAINT unique_product UNIQUE (exchange, product_id)
);

-- Індекси для швидких запитів
CREATE INDEX idx_earn_products_exchange ON earn_products(exchange);
CREATE INDEX idx_earn_products_symbol ON earn_products(symbol);
CREATE INDEX idx_earn_products_apy ON earn_products(apy DESC);
CREATE INDEX idx_earn_products_active ON earn_products(is_active) WHERE is_active = true;
CREATE INDEX idx_earn_products_updated ON earn_products(updated_at DESC);
CREATE INDEX idx_earn_products_exchange_symbol ON earn_products(exchange, symbol);

-- JSONB індекс для швидкого пошуку в специфічних даних
CREATE INDEX idx_earn_products_exchange_data ON earn_products USING gin(exchange_specific_data);
```

---

### Таблиця 2: `earn_products_history` (Історія змін)

**Призначення:** Зберігає історію змін APY та інших параметрів

```sql
CREATE TABLE earn_products_history (
    id SERIAL PRIMARY KEY,

    -- Зв'язок з основною таблицею
    product_id VARCHAR(100) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Історичні дані
    apy DECIMAL(10, 6) NOT NULL,
    min_amount DECIMAL(20, 8),
    is_active BOOLEAN,

    -- Snapshot всіх даних
    snapshot JSONB NOT NULL,                    -- Повний знімок продукту

    -- Мітка часу
    recorded_at TIMESTAMP DEFAULT NOW(),

    -- Індекси
    FOREIGN KEY (product_id) REFERENCES earn_products(product_id) ON DELETE CASCADE
);

-- Індекси
CREATE INDEX idx_history_product ON earn_products_history(product_id);
CREATE INDEX idx_history_symbol ON earn_products_history(symbol);
CREATE INDEX idx_history_date ON earn_products_history(recorded_at DESC);
CREATE INDEX idx_history_exchange_symbol ON earn_products_history(exchange, symbol, recorded_at DESC);
```

---

### Таблиця 3: `api_sync_log` (Лог синхронізації)

**Призначення:** Відстежує успішність оновлень з API

```sql
CREATE TABLE api_sync_log (
    id SERIAL PRIMARY KEY,

    -- Деталі синхронізації
    exchange VARCHAR(50) NOT NULL,
    sync_type VARCHAR(50) NOT NULL,             -- full, incremental, asset_specific

    -- Результати
    status VARCHAR(20) NOT NULL,                -- success, failed, partial
    products_synced INTEGER DEFAULT 0,          -- Кількість оброблених продуктів
    products_added INTEGER DEFAULT 0,           -- Додано нових
    products_updated INTEGER DEFAULT 0,         -- Оновлено
    products_deactivated INTEGER DEFAULT 0,     -- Деактивовано

    -- Помилки
    error_message TEXT,                         -- Опис помилки (якщо є)

    -- Часові мітки
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER,                   -- Тривалість синхронізації

    -- Додаткова інформація
    metadata JSONB                              -- Додаткові дані про синхронізацію
);

-- Індекси
CREATE INDEX idx_sync_log_exchange ON api_sync_log(exchange);
CREATE INDEX idx_sync_log_status ON api_sync_log(status);
CREATE INDEX idx_sync_log_started ON api_sync_log(started_at DESC);
```

---

### Таблиця 4: `user_queries` (Статистика запитів користувачів)

**Призначення:** Відстежує які продукти цікавлять користувачів

```sql
CREATE TABLE user_queries (
    id SERIAL PRIMARY KEY,

    -- Користувач (з Telegram Bot)
    user_id BIGINT,                             -- Telegram user ID (може бути NULL)

    -- Деталі запиту
    query_type VARCHAR(50) NOT NULL,            -- search_symbol, top_apy, recommendations
    symbol VARCHAR(20),                         -- Якщо шукали конкретну монету
    exchange VARCHAR(50),                       -- Якщо фільтрували по біржі

    -- Результати
    results_count INTEGER DEFAULT 0,

    -- Мітка часу
    queried_at TIMESTAMP DEFAULT NOW(),

    -- IP або джерело (опціонально)
    source VARCHAR(100)
);

-- Індекси
CREATE INDEX idx_user_queries_symbol ON user_queries(symbol);
CREATE INDEX idx_user_queries_date ON user_queries(queried_at DESC);
```

---

## 🎯 Які Дані Зберігати з API

### Обов'язкові Поля (Є у всіх біржах):

| Поле               | Тип     | Опис                | Приклад                      |
| ------------------ | ------- | ------------------- | ---------------------------- |
| `product_id`       | VARCHAR | Унікальний ID з API | `binance_simple_flex_BTC001` |
| `exchange`         | VARCHAR | Назва біржі         | `Binance`, `Bybit`           |
| `symbol`           | VARCHAR | Символ монети       | `BTC`, `ETH`                 |
| `name`             | VARCHAR | Назва продукту      | `BTC Flexible Savings`       |
| `apy`              | DECIMAL | APY у відсотках     | `5.25`                       |
| `min_amount`       | DECIMAL | Мінімальна сума     | `0.001`                      |
| `lock_period_days` | INTEGER | Днів блокування     | `0`, `30`, `90`              |
| `is_active`        | BOOLEAN | Чи доступний        | `true`/`false`               |

### Додаткові Поля (Рекомендовано):

| Поле           | Опис                                    |
| -------------- | --------------------------------------- |
| `max_amount`   | Максимальна сума (може бути NULL)       |
| `product_type` | `Flexible`, `Locked`, `Fixed`           |
| `category`     | `FlexibleSaving`, `OnChain` (для Bybit) |
| `description`  | Опис продукту                           |
| `website_url`  | Посилання на сторінку                   |
| `risk_level`   | Рівень ризику                           |

### Специфічні Дані Бірж (JSONB):

**Binance специфічні:**

```json
{
  "tierAnnualPercentageRate": { "0-0.01BTC": "0.00250000" },
  "canPurchase": true,
  "canRedeem": true,
  "isSoldOut": false,
  "subscriptionStartTime": 1571730224000,
  "raw_product_id": "BTC001"
}
```

**Bybit специфічні:**

```json
{
  "precision": "8",
  "bonusEvents": [],
  "duration": "Flexible",
  "stakeExchangeRate": "",
  "redeemExchangeRate": "",
  "rewardIntervalMinute": 0
}
```

---

## 💾 Основні Команди PostgreSQL

### Підключення до БД

```bash
# Локально
psql -U yield_user -d yield_db

# Через Docker
docker exec -it yield-postgres psql -U yield_user -d yield_db

# З .env файлом
psql $DATABASE_URL
```

### Перегляд Структури

```sql
-- Список всіх таблиць
\dt

-- Опис таблиці
\d earn_products

-- Розмір таблиці
SELECT pg_size_pretty(pg_total_relation_size('earn_products'));

-- Кількість записів
SELECT COUNT(*) FROM earn_products;
```

### Базові Запити

```sql
-- Переглянути всі продукти
SELECT * FROM earn_products LIMIT 10;

-- Продукти з найвищим APY
SELECT exchange, symbol, name, apy, lock_period_days
FROM earn_products
WHERE is_active = true
ORDER BY apy DESC
LIMIT 20;

-- Продукти для BTC
SELECT exchange, name, apy, lock_period_days, min_amount
FROM earn_products
WHERE symbol = 'BTC' AND is_active = true
ORDER BY apy DESC;

-- Порівняння бірж для конкретної монети
SELECT
    exchange,
    name,
    apy,
    lock_period_days,
    min_amount
FROM earn_products
WHERE symbol = 'ETH' AND is_active = true
ORDER BY exchange, apy DESC;

-- Статистика по біржах
SELECT
    exchange,
    COUNT(*) as products_count,
    AVG(apy) as avg_apy,
    MAX(apy) as max_apy,
    MIN(apy) as min_apy
FROM earn_products
WHERE is_active = true
GROUP BY exchange;
```

---

## 🔄 Оновлення Даних (кожні 60 хвилин)

### Стратегія Оновлення: UPSERT

**Підхід:** Використовуємо `INSERT ... ON CONFLICT ... UPDATE`

```sql
-- Приклад UPSERT для одного продукту
INSERT INTO earn_products (
    product_id, exchange, symbol, name, apy,
    min_amount, max_amount, lock_period_days,
    product_type, category, is_active,
    description, website_url, exchange_specific_data,
    last_api_sync
) VALUES (
    'binance_simple_flex_BTC001',
    'Binance',
    'BTC',
    'BTC Flexible Savings',
    5.25,
    0.001,
    NULL,
    0,
    'Flexible',
    'Simple Earn',
    true,
    'Flexible savings for BTC',
    'https://www.binance.com/en/earn',
    '{"canPurchase": true, "canRedeem": true}'::jsonb,
    NOW()
)
ON CONFLICT (exchange, product_id)
DO UPDATE SET
    apy = EXCLUDED.apy,
    min_amount = EXCLUDED.min_amount,
    max_amount = EXCLUDED.max_amount,
    is_active = EXCLUDED.is_active,
    exchange_specific_data = EXCLUDED.exchange_specific_data,
    updated_at = NOW(),
    last_api_sync = NOW();
```

### Деактивація Старих Продуктів

```sql
-- Деактивувати продукти, які не оновлювались > 2 години
UPDATE earn_products
SET
    is_active = false,
    updated_at = NOW()
WHERE
    last_api_sync < NOW() - INTERVAL '2 hours'
    AND is_active = true;
```

### Збереження Історії

```sql
-- При кожному оновленні зберігаємо snapshot
INSERT INTO earn_products_history (
    product_id, exchange, symbol, apy,
    min_amount, is_active, snapshot
)
SELECT
    product_id, exchange, symbol, apy,
    min_amount, is_active,
    row_to_json(earn_products.*)::jsonb
FROM earn_products
WHERE updated_at > NOW() - INTERVAL '1 hour';
```

---

## 🔍 Корисні Запити для Аналізу

### Топ-10 продуктів за APY

```sql
SELECT
    exchange,
    symbol,
    name,
    apy,
    lock_period_days,
    min_amount,
    CASE
        WHEN lock_period_days = 0 THEN 'Flexible'
        ELSE CONCAT(lock_period_days, ' days')
    END as lock_info
FROM earn_products
WHERE is_active = true
ORDER BY apy DESC
LIMIT 10;
```

### Історія змін APY для BTC

```sql
SELECT
    exchange,
    apy,
    recorded_at
FROM earn_products_history
WHERE symbol = 'BTC'
ORDER BY recorded_at DESC
LIMIT 50;
```

### Продукти без блокування (Flexible)

```sql
SELECT
    exchange,
    symbol,
    name,
    apy,
    min_amount
FROM earn_products
WHERE
    is_active = true
    AND lock_period_days = 0
ORDER BY apy DESC;
```

### Порівняння середніх APY між біржами

```sql
SELECT
    exchange,
    symbol,
    AVG(apy) as avg_apy,
    COUNT(*) as products_count
FROM earn_products
WHERE is_active = true
GROUP BY exchange, symbol
ORDER BY symbol, avg_apy DESC;
```

### Популярні запити користувачів

```sql
SELECT
    symbol,
    COUNT(*) as query_count,
    MAX(queried_at) as last_query
FROM user_queries
WHERE queried_at > NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY query_count DESC
LIMIT 10;
```

---

## 💾 Backup та Restore

### Створення Backup

```bash
# Повний backup бази даних
pg_dump -U yield_user -d yield_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Тільки структура (без даних)
pg_dump -U yield_user -d yield_db --schema-only > schema_backup.sql

# Тільки дані
pg_dump -U yield_user -d yield_db --data-only > data_backup.sql

# Стиснутий backup
pg_dump -U yield_user -d yield_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore з Backup

```bash
# Відновлення з backup
psql -U yield_user -d yield_db < backup_20241013_120000.sql

# З стиснутого файлу
gunzip -c backup_20241013.sql.gz | psql -U yield_user -d yield_db
```

### Автоматичний Backup (cron)

```bash
# Додати в crontab
crontab -e

# Щоденний backup о 3:00
0 3 * * * pg_dump -U yield_user -d yield_db | gzip > /path/to/backups/backup_$(date +\%Y\%m\%d).sql.gz

# Видалення старих backups (старіші 7 днів)
0 4 * * * find /path/to/backups -name "backup_*.sql.gz" -mtime +7 -delete
```

---

## 📊 Моніторинг та Оптимізація

### Перевірка Розміру Таблиць

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Статистика Використання Індексів

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Vacuum та Analyze

```sql
-- Очищення мертвих рядків
VACUUM ANALYZE earn_products;

-- Повне очищення (потребує ексклюзивного lock)
VACUUM FULL earn_products;

-- Оновлення статистики для оптимізатора запитів
ANALYZE earn_products;
```

### Автоматичний Vacuum

```sql
-- Налаштування в postgresql.conf
autovacuum = on
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_scale_factor = 0.05
```

---

## 🔧 Troubleshooting

### Проблема: Повільні Запити

```sql
-- Знайти повільні запити
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Включити логування повільних запитів (postgresql.conf)
log_min_duration_statement = 1000  # мс
```

### Проблема: Дублікати Даних

```sql
-- Знайти дублікати
SELECT
    exchange, product_id, COUNT(*)
FROM earn_products
GROUP BY exchange, product_id
HAVING COUNT(*) > 1;

-- Видалити дублікати (залишити останній)
DELETE FROM earn_products
WHERE id IN (
    SELECT id
    FROM (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY exchange, product_id
                ORDER BY updated_at DESC
            ) as rn
        FROM earn_products
    ) t
    WHERE t.rn > 1
);
```

### Проблема: З'єднання Відмовляються

```bash
# Перевірка активних з'єднань
psql -U yield_user -d yield_db -c "SELECT count(*) FROM pg_stat_activity;"

# Вбити зависле з'єднання
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE pid <> pg_backend_pid() AND state = 'idle';
```

### Проблема: Помилка "disk full"

```bash
# Перевірка вільного місця
df -h

# Очищення старих логів
sudo find /var/log/postgresql -name "*.log" -mtime +7 -delete

# Vacuum для звільнення місця
VACUUM FULL;
```

---

## 🛠️ Корисні Команди для Щоденної Роботи

### Перевірка Статусу

```bash
# Статус PostgreSQL
sudo systemctl status postgresql

# Або для Docker
docker ps | grep postgres
docker logs yield-postgres
```

### Швидкий Доступ

```bash
# Створити alias для швидкого доступу
echo 'alias pgdb="psql -U yield_user -d yield_db"' >> ~/.bashrc
source ~/.bashrc

# Тепер можна просто
pgdb
```

### Експорт Даних

```sql
-- Експорт у CSV
COPY (
    SELECT exchange, symbol, name, apy, lock_period_days
    FROM earn_products
    WHERE is_active = true
    ORDER BY apy DESC
) TO '/tmp/top_products.csv' WITH CSV HEADER;

-- Експорт у JSON (через psql)
\o /tmp/products.json
SELECT json_agg(row_to_json(t))
FROM (
    SELECT exchange, symbol, name, apy
    FROM earn_products
    WHERE is_active = true
    LIMIT 100
) t;
\o
```

---

## 📚 Додаткові Ресурси

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [SQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [JSONB Best Practices](https://www.postgresql.org/docs/current/datatype-json.html)

---

## 🛠️ Інструменти для Роботи з PostgreSQL

### **DBeaver** (Безкоштовний)

**Що це:** Універсальний клієнт для різних БД.

**Встановлення:**

```bash
# macOS
brew install --cask dbeaver-community

# Windows/Linux: завантажити з dbeaver.io
```

**Підключення:**

1. File → New → Database Connection
2. PostgreSQL → Next
3. Налаштування:
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `yield_db`
   - **Username:** `yield_user`
   - **Password:** `yield_secure_password_2024`

**Переваги:**

- ✅ Підтримка багатьох БД
- ✅ ER діаграми
- ✅ SQL автодоповнення
- ✅ Експорт даних у різні формати


### Налаштування MCP для Cursor IDE

**Крок 1:** Додайте MCP конфігурацію в Cursor

```json
{
  "mcp": {
    "servers": {
      "postgres": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "env": {
          "POSTGRES_URL": "postgresql://yield_user:yield_secure_password_2024@localhost:5432/yield_db"
        }
      }
    }
  }
}
```

**Крок 2:** Перезапустіть Cursor IDE

**Крок 3:** Перевірте підключення

- Відкрийте Command Palette (Ctrl+Shift+P)
- Знайдіть "MCP" команди
- Виконайте тестовий запит

### Альтернативне MCP підключення

Якщо стандартне MCP не працює, використовуйте:

```json
{
  "mcp": {
    "servers": {
      "postgres": {
        "command": "docker",
        "args": [
          "exec",
          "-i",
          "earn-postgres",
          "psql",
          "-U",
          "yield_user",
          "-d",
          "yield_db"
        ],
        "env": {}
      }
    }
  }
}
```

---

## 📊 Приклади Використання Інструментів

### Приклад 1: pgAdmin - Перегляд топ продуктів

```sql
-- Топ-10 продуктів за APY
SELECT
    exchange,
    symbol,
    name,
    apy,
    lock_period_days,
    remaining_pool_size
FROM earn_products
WHERE is_active = true
ORDER BY apy DESC
LIMIT 10;
```

**Результат у pgAdmin:**

- Таблиця з результатами
- Можливість експорту в CSV/Excel
- Фільтрація та сортування

### Приклад 2: DBeaver - Аналіз по біржах

```sql
-- Статистика по біржах
SELECT
    exchange,
    COUNT(*) as products_count,
    AVG(apy) as avg_apy,
    MAX(apy) as max_apy,
    MIN(apy) as min_apy,
    SUM(remaining_pool_size) as total_pool_size
FROM earn_products
WHERE is_active = true
GROUP BY exchange
ORDER BY avg_apy DESC;
```

**Результат у DBeaver:**

- Таблиця з агрегованими даними
- Можливість створення діаграм
- Експорт у різні формати

### Приклад 3: TablePlus - Пошук продуктів

```sql
-- Продукти з високим APY та низьким ризиком
SELECT
    exchange,
    symbol,
    name,
    apy,
    risk_level,
    global_product,
    auto_renewal
FROM earn_products
WHERE
    is_active = true
    AND apy > 5.0
    AND risk_level = 'Low'
    AND global_product = true
ORDER BY apy DESC;
```
