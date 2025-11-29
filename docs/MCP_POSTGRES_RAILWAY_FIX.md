# 🔧 Виправлення доступу до Railway PostgreSQL через MCP

**Дата:** 2025-11-28  
**Проблема:** MCP postgres-railway повертає помилку `-32603` (внутрішня помилка сервера)

---

## 🔍 Аналіз проблеми

### Виявлені проблеми:

1. **Пакет застарілий:** `@modelcontextprotocol/server-postgres@0.6.2` помічений як DEPRECATED
2. **Connection string:** Використовується `DATABASE_PUBLIC_URL` з Railway
3. **SSL:** Railway може вимагати SSL підключення

---

## ✅ Рішення

### Варіант 1: Оновлена конфігурація (поточний)

Файл: `/Users/user777/.cursor/mcp.json`

```json
"postgres-railway": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-postgres",
    "postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway"
  ]
}
```

**Важливо:** Після зміни конфігурації потрібно **перезапустити Cursor IDE**.

### Варіант 2: З параметрами SSL

Якщо Railway вимагає SSL:

```json
"postgres-railway": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-postgres",
    "postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway?sslmode=require"
  ]
}
```

### Варіант 3: Через змінну середовища

```json
"postgres-railway": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-postgres"
  ],
  "env": {
    "POSTGRES_URL": "postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway"
  }
}
```

---

## 🔄 Кроки для виправлення

### 1. Перевірка Railway налаштувань

1. **Перевірте `DATABASE_PUBLIC_URL`:**

   - Railway UI → Проект → PostgreSQL сервіс → Variables
   - Переконайтеся, що `DATABASE_PUBLIC_URL` присутня

2. **Увімкніть Public Networking:**
   - Railway UI → PostgreSQL сервіс → Settings → Networking
   - Увімкніть "Public TCP Proxy"

### 2. Оновлення конфігурації MCP

1. Відкрийте `/Users/user777/.cursor/mcp.json`
2. Перевірте конфігурацію `postgres-railway`
3. Збережіть файл

### 3. Перезапуск Cursor

**КРИТИЧНО:** Після зміни `mcp.json` обов'язково перезапустіть Cursor IDE:

1. Закрийте Cursor повністю (Cmd+Q на Mac)
2. Відкрийте Cursor знову
3. Перевірте підключення через MCP

### 4. Перевірка підключення

Після перезапуску спробуйте:

```sql
SELECT version();
```

---

## 🐛 Troubleshooting

### Помилка: `MCP error -32603`

**Можливі причини:**

1. Cursor не перезапущений після зміни конфігурації
2. Неправильний формат connection string
3. Railway не дозволяє зовнішні підключення
4. Проблеми з SSL сертифікатом

**Рішення:**

1. Перезапустіть Cursor IDE
2. Перевірте формат connection string
3. Перевірте налаштування Public Networking в Railway
4. Спробуйте додати `?sslmode=require` до connection string

### Помилка: Connection timeout

**Можливі причини:**

1. Public TCP Proxy не увімкнено
2. Firewall блокує підключення
3. Неправильний хост/порт

**Рішення:**

1. Увімкніть Public Networking в Railway
2. Перевірте, чи хост `maglev.proxy.rlwy.net` доступний
3. Перевірте порт `27723`

### Помилка: Authentication failed

**Можливі причини:**

1. Неправильний пароль
2. Користувач не має доступу

**Рішення:**

1. Перевірте пароль в Railway Variables
2. Переконайтеся, що використовуєте `DATABASE_PUBLIC_URL`, а не `DATABASE_URL`

---

## 📝 Поточна конфігурація

**Connection String:**

```
postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway
```

**Компоненти:**

- **User:** `postgres`
- **Password:** `WqguqqplclnYvKNoXbFBpxttShgZjgMH`
- **Host:** `maglev.proxy.rlwy.net`
- **Port:** `27723`
- **Database:** `railway`

---

## ⚠️ Важливі примітки

1. **Безпека:**

   - Пароль зберігається в `mcp.json` у відкритому вигляді
   - Рекомендується використовувати env змінні або секрети

2. **Витрати:**

   - Public Networking може призвести до додаткових витрат на egress traffic

3. **DEPRECATED пакет:**
   - `@modelcontextprotocol/server-postgres` помічений як DEPRECATED
   - Можливо потрібно шукати альтернативу в майбутньому

---

## 🔗 Корисні посилання

- [Railway PostgreSQL Documentation](https://docs.railway.com/guides/postgresql)
- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [Railway Help Station - Postgres Connection](https://station.railway.com/questions/postgres-database-url-does-not-show-c9a6c651)

---

## 🔄 Оновлення (після перезапуску Cursor)

### Використано альтернативний MCP сервер

Оскільки `@modelcontextprotocol/server-postgres` помічений як DEPRECATED, використано альтернативний пакет `mcp-postgres@latest` (версія 1.1.2).

**Оновлена конфігурація:**

```json
"postgres-railway": {
  "command": "npx",
  "args": [
    "-y",
    "mcp-postgres@latest"
  ],
  "env": {
    "DATABASE_URL": "postgresql://postgres:WqguqqplclnYvKNoXbFBpxttShgZjgMH@maglev.proxy.rlwy.net:27723/railway?sslmode=require"
  }
}
```

**Відмінності:**

- Використовується `mcp-postgres@latest` замість `@modelcontextprotocol/server-postgres`
- Connection string передається через змінну середовища `DATABASE_URL` (не `POSTGRES_CONNECTION_STRING`)
- Додано параметр `?sslmode=require` для безпечного підключення

**Важливо:** Після зміни конфігурації обов'язково перезапустіть Cursor IDE.

### Альтернативний спосіб перевірки

Якщо MCP все ще не працює, можна використати прямий Python скрипт для тестування підключення:

```bash
python3 scripts/test_railway_postgres.py
```

Скрипт перевіряє:

- Підключення до Railway PostgreSQL
- Наявність таблиць
- Кількість записів у `yield_products` та `priority_products`

---

**Останнє оновлення:** 2025-11-28
