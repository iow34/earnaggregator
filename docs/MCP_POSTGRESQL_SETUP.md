# 🔧 MCP PostgreSQL Setup - Покрокова Інструкція

## 📋 Зміст

1. [Перевірка Поточного Статусу](#перевірка-поточного-статусу)
2. [Налаштування MCP в Cursor IDE](#налаштування-mcp-в-cursor-ide)
3. [Альтернативні Способи Підключення](#альтернативні-способи-підключення)
4. [Тестування Підключення](#тестування-підключення)
5. [Troubleshooting](#troubleshooting)

---

## 🔍 Перевірка Поточного Статусу

### ✅ Що вже налаштовано:

```bash
# PostgreSQL контейнер запущений
docker ps | grep postgres
# earn-postgres    Up 2 minutes (healthy)   0.0.0.0:5432->5432/tcp

# База даних створена
docker-compose exec postgres psql -U yield_user -d yield_db -c "\l"
# yield_db    | yield_user | UTF8 | C | C |

# Таблиці створені
docker-compose exec postgres psql -U yield_user -d yield_db -c "\dt"
# earn_products, earn_products_history, api_sync_log, user_queries

# Тестові дані додані
docker-compose exec postgres psql -U yield_user -d yield_db -c "SELECT COUNT(*) FROM earn_products;"
# 2 записи
```

---

## 🛠️ Налаштування MCP в Cursor IDE

### Крок 1: Знайдіть конфігураційний файл MCP

**Для macOS:**

```bash
# Шлях до конфігурації Cursor
~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/

# Або створити в кореневій директорії проекту
/Users/user777/Documents/EarnAggregator/.cursor/
```

### Крок 2: Створіть конфігураційний файл

**Створіть файл:** `.cursor/mcp.json`

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

### Крок 3: Альтернативна конфігурація (якщо перша не працює)

```json
{
  "mcp": {
    "servers": {
      "postgres-docker": {
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

### Крок 4: Перезапустіть Cursor IDE

```bash
# Закрийте Cursor повністю
# Відкрийте знову
# Перевірте Command Palette (Cmd+Shift+P)
```

---

## 🔄 Альтернативні Способи Підключення

### Спосіб 1: Пряме підключення через psql

```bash
# Локальне підключення
psql -h localhost -p 5432 -U yield_user -d yield_db

# Через Docker
docker-compose exec postgres psql -U yield_user -d yield_db
```

### Спосіб 2: pgAdmin (Веб-інтерфейс)

```bash
# Запуск pgAdmin
docker run -d \
  --name pgadmin \
  -p 80:80 \
  -e 'PGADMIN_DEFAULT_EMAIL=admin@admin.com' \
  -e 'PGADMIN_DEFAULT_PASSWORD=admin' \
  dpage/pgadmin4

# Доступ: http://localhost
# Логін: admin@admin.com / admin
```

**Налаштування сервера в pgAdmin:**

- **Name:** EarnAggregator DB
- **Host:** host.docker.internal (для Docker на macOS)
- **Port:** 5432
- **Database:** yield_db
- **Username:** yield_user
- **Password:** yield_secure_password_2024

### Спосіб 3: VS Code Extension

1. Встановіть розширення "PostgreSQL"
2. Ctrl+Shift+P → "PostgreSQL: New Query"
3. Налаштуйте підключення:
   - **Host:** localhost
   - **Port:** 5432
   - **Database:** yield_db
   - **Username:** yield_user
   - **Password:** yield_secure_password_2024

---

## 🧪 Тестування Підключення

### Тест 1: Базова перевірка

```sql
-- Перевірка підключення
SELECT 'PostgreSQL підключена успішно!' as status;

-- Перевірка таблиць
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

-- Перевірка даних
SELECT COUNT(*) as total_products FROM earn_products;
```

### Тест 2: Перевірка нових полів

```sql
-- Перевірка додаткових полів
SELECT
    exchange,
    symbol,
    apy,
    global_product,
    auto_renewal,
    remaining_pool_size
FROM earn_products
LIMIT 5;
```

### Тест 3: Тестовий INSERT

```sql
-- Додавання тестового продукту
INSERT INTO earn_products (
    product_id, exchange, symbol, name, apy,
    min_amount, lock_period_days, product_type,
    is_active, global_product, auto_renewal
) VALUES (
    'test_coin_USDT001',
    'TestExchange',
    'USDT',
    'USDT Test Product',
    3.5,
    10.0,
    30,
    'Fixed',
    true,
    true,
    true
);

-- Перевірка додавання
SELECT * FROM earn_products WHERE exchange = 'TestExchange';
```

---

## 🚨 Troubleshooting

### Проблема 1: "Connection refused"

**Симптоми:**

```
ERROR: connection refused
Is the server running on host "localhost" and accepting TCP/IP connections on port 5432?
```

**Рішення:**

```bash
# Перевірте чи запущений контейнер
docker ps | grep postgres

# Якщо не запущений - запустіть
docker-compose up -d postgres

# Перевірте логи
docker-compose logs postgres
```

### Проблема 2: "Authentication failed"

**Симптоми:**

```
ERROR: password authentication failed for user "yield_user"
```

**Рішення:**

```bash
# Перевірте пароль в .env файлі
cat .env | grep POSTGRES_PASSWORD

# Перевірте в docker-compose.yml
docker-compose config | grep POSTGRES_PASSWORD

# Якщо потрібно - змініть пароль
# 1. Зупиніть контейнер
docker-compose down

# 2. Видаліть volume
docker volume rm earn_postgres_data

# 3. Змініть пароль в .env
# 4. Запустіть знову
docker-compose up -d postgres
```

### Проблема 3: "Database does not exist"

**Симптоми:**

```
ERROR: database "yield_db" does not exist
```

**Рішення:**

```bash
# Підключіться до postgres БД
docker-compose exec postgres psql -U yield_user -d postgres

# Створіть базу даних
CREATE DATABASE yield_db;

# Надайте права
GRANT ALL PRIVILEGES ON DATABASE yield_db TO yield_user;

# Вихід
\q
```

### Проблема 4: MCP не працює в Cursor

**Симптоми:**

- MCP команди не з'являються в Command Palette
- Помилки при виконанні MCP запитів

**Рішення:**

```bash
# 1. Перевірте файл конфігурації
cat ~/.cursor/mcp.json

# 2. Перевірте синтаксис JSON
python -m json.tool ~/.cursor/mcp.json

# 3. Спробуйте альтернативну конфігурацію
# 4. Перезапустіть Cursor
# 5. Перевірте логи Cursor
```

---

## 📊 Корисні Команди для MCP

### Якщо MCP працює:

```sql
-- Отримати статистику
SELECT
    exchange,
    COUNT(*) as products,
    AVG(apy) as avg_apy,
    MAX(apy) as max_apy
FROM earn_products
GROUP BY exchange;

-- Знайти топ продукти
SELECT
    exchange,
    symbol,
    name,
    apy,
    global_product
FROM earn_products
WHERE is_active = true
ORDER BY apy DESC
LIMIT 10;

-- Перевірити останні оновлення
SELECT
    exchange,
    MAX(last_api_sync) as last_sync,
    COUNT(*) as total_products
FROM earn_products
GROUP BY exchange;
```

---

## 🎯 Перевірочний Список

### ✅ Налаштування завершено якщо:

- [ ] PostgreSQL контейнер запущений (`docker ps`)
- [ ] База даних `yield_db` створена
- [ ] Користувач `yield_user` має доступ
- [ ] Всі 4 таблиці створені
- [ ] Тестові дані додані (2+ записи)
- [ ] MCP конфігурація створена
- [ ] Cursor IDE перезапущений
- [ ] Тестові SQL запити працюють

### 📝 Наступні кроки:

1. **Перевірте MCP підключення** через Command Palette
2. **Встановіть pgAdmin** для візуального управління
3. **Налаштуйте backup** процедури
4. **Створіть індекси** для оптимізації запитів

---

## 🔗 Корисні Посилання

- [MCP Documentation](https://modelcontextprotocol.io/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [pgAdmin Docker Hub](https://hub.docker.com/r/dpage/pgadmin4)
- [Cursor IDE Documentation](https://cursor.sh/docs)

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Готово до використання

---

## 💡 Рекомендації

### Для щоденної роботи:

1. **Використовуйте pgAdmin** - найзручніший інтерфейс
2. **Налаштуйте backup** - автоматичні щоденні бекапи
3. **Моніторьте логи** - перевіряйте логи PostgreSQL

### Для розробки:

1. **VS Code Extension** - швидкі запити
2. **Docker exec** - швидкий доступ до psql
3. **MCP** - інтеграція з AI асистентом

**Готовий до роботи з PostgreSQL! 🚀**
