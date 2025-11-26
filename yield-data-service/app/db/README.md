# 🗄️ Database Layer - PostgreSQL

## 📁 Структура Директорії

```
app/db/
├── README.md                  # Цей файл
├── POSTGRESQL_GUIDE.md        # Повна інструкція по PostgreSQL
├── QUICK_REFERENCE.md         # Швидкий довідник команд
├── schema.sql                 # SQL скрипт для створення таблиць
├── __init__.py                # Python пакет
├── database.py                # Підключення до БД
├── models.py                  # SQLAlchemy моделі
└── crud.py                    # CRUD операції
```

---

## 🎯 Призначення Файлів

### 📖 Документація

1. **`POSTGRESQL_GUIDE.md`** - Повна інструкція

   - Встановлення та налаштування PostgreSQL
   - Структура таблиць з поясненнями
   - Основні команди та запити
   - Стратегія оновлення даних (кожні 60 хв)
   - Backup, restore, моніторинг
   - Troubleshooting

2. **`QUICK_REFERENCE.md`** - Швидкий довідник

   - Найчастіше використовувані запити
   - Адміністрування
   - Моніторинг
   - Експорт даних

3. **`schema.sql`** - SQL скрипт
   - Створення всіх таблиць
   - Індекси
   - Тригери та функції
   - Views для аналізу

---

### 💻 Python Код (Буде реалізовано)

4. **`database.py`** - Підключення до БД

   - Налаштування SQLAlchemy engine
   - Session management
   - Connection pooling

5. **`models.py`** - ORM моделі

   - SQLAlchemy моделі таблиць
   - Relationships
   - Validators

6. **`crud.py`** - CRUD операції
   - Створення (Create)
   - Читання (Read)
   - Оновлення (Update)
   - Видалення (Delete)
   - Спеціалізовані запити

---

## 🗂️ Структура Бази Даних

### Таблиці:

```
┌─────────────────────────┐
│   earn_products         │  ◄── Головна таблиця (актуальні продукти)
│  - id (PK)              │
│  - product_id (UK)      │
│  - exchange             │
│  - symbol               │
│  - apy                  │
│  - ...                  │
└─────────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────┐
│ earn_products_history   │  ◄── Історія змін (кожні 60 хв)
│  - id (PK)              │
│  - product_id (FK)      │
│  - snapshot (JSONB)     │
│  - recorded_at          │
└─────────────────────────┘

┌─────────────────────────┐
│   api_sync_log          │  ◄── Лог синхронізацій з API
│  - id (PK)              │
│  - exchange             │
│  - status               │
│  - products_synced      │
│  - started_at           │
└─────────────────────────┘

┌─────────────────────────┐
│   user_queries          │  ◄── Статистика запитів від користувачів
│  - id (PK)              │
│  - user_id              │
│  - symbol               │
│  - queried_at           │
└─────────────────────────┘
```

---

## 🔄 Стратегія Оновлення Даних

### Кожні 60 хвилин:

1. **Отримати дані з API** (Binance, Bybit)
2. **UPSERT** до `earn_products`:
   ```sql
   INSERT ... ON CONFLICT (exchange, product_id)
   DO UPDATE SET apy = ..., updated_at = NOW()
   ```
3. **Зберегти snapshot** до `earn_products_history`
4. **Деактивувати** продукти, які зникли з API
5. **Логувати** результат у `api_sync_log`

### Псевдокод:

```python
async def sync_exchange_products(exchange: str):
    # 1. Отримати дані з API
    products = await exchange_api.get_earn_products()

    # 2. Для кожного продукту
    for product in products:
        # UPSERT
        await db.upsert_product(product)

        # Зберегти історію
        await db.save_history(product)

    # 3. Деактивувати старі
    await db.deactivate_outdated_products(exchange)

    # 4. Лог
    await db.log_sync_result(exchange, len(products))
```

---

## 📊 Які Дані Зберігати

### ✅ Обов'язкові поля (є у всіх біржах):

| Поле               | Тип     | Опис                |
| ------------------ | ------- | ------------------- |
| `product_id`       | VARCHAR | Унікальний ID з API |
| `exchange`         | VARCHAR | Назва біржі         |
| `symbol`           | VARCHAR | BTC, ETH, USDT      |
| `name`             | VARCHAR | Назва продукту      |
| `apy`              | DECIMAL | APY у відсотках     |
| `min_amount`       | DECIMAL | Мінімальна сума     |
| `lock_period_days` | INTEGER | Днів блокування     |
| `is_active`        | BOOLEAN | Чи доступний        |

### 📦 Додаткові поля:

- `max_amount` - Максимальна сума
- `product_type` - Flexible, Locked, Fixed
- `category` - FlexibleSaving, OnChain
- `description` - Опис
- `website_url` - Посилання

### 🎁 Специфічні дані бірж → JSONB

**Чому JSONB?**

- ✅ Гнучкість (різні біржі = різні поля)
- ✅ Не потрібно змінювати схему при додаванні нової біржі
- ✅ Швидкі запити (GIN індекс)
- ✅ Зберігаємо raw_data для аудиту

**Приклад:**

```json
{
  "binance": {
    "tierAnnualPercentageRate": { "0-0.01BTC": "0.0025" },
    "canPurchase": true,
    "canRedeem": true,
    "subscriptionStartTime": 1571730224000
  },
  "bybit": {
    "precision": "8",
    "duration": "Flexible",
    "bonusEvents": [],
    "category": "FlexibleSaving"
  }
}
```

---

## 🚀 План Імплементації Коду

### Частина 1: Базове Підключення (`database.py`)

- [ ] SQLAlchemy engine
- [ ] AsyncSession factory
- [ ] Connection pooling
- [ ] Dependency для FastAPI

### Частина 2: ORM Моделі (`models.py`)

- [ ] `EarnProduct` модель
- [ ] `EarnProductHistory` модель
- [ ] `APISyncLog` модель
- [ ] `UserQuery` модель
- [ ] Relationships та validators

### Частина 3: CRUD Операції (`crud.py`)

- [ ] `create_product()` - Додати продукт
- [ ] `get_product()` - Отримати продукт
- [ ] `update_product()` - Оновити продукт
- [ ] `upsert_product()` - Insert або Update
- [ ] `get_products_by_symbol()` - Фільтр по монеті
- [ ] `get_top_apy_products()` - Топ за APY
- [ ] `deactivate_outdated()` - Деактивація старих
- [ ] `save_history_snapshot()` - Зберегти історію
- [ ] `log_sync_result()` - Лог синхронізації

### Частина 4: Інтеграція з API (`scheduler.py`)

- [ ] Функція синхронізації з Binance
- [ ] Функція синхронізації з Bybit
- [ ] Загальна функція `sync_all_exchanges()`
- [ ] APScheduler job (кожні 60 хв)
- [ ] Error handling та retry

### Частина 5: API Endpoints (`routes.py`)

- [ ] `GET /api/v1/products` - Список продуктів
- [ ] `GET /api/v1/products/{symbol}` - По монеті
- [ ] `GET /api/v1/products/top` - Топ за APY
- [ ] `GET /api/v1/history/{symbol}` - Історія APY
- [ ] `GET /api/v1/stats` - Статистика

---

## 🔧 Швидкий Старт

### 1. Створити БД

```bash
# Запустити PostgreSQL (Docker)
docker run -d \
  --name yield-postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_USER=yield_user \
  -e POSTGRES_DB=yield_db \
  -p 5432:5432 \
  postgres:15-alpine
```

### 2. Виконати SQL скрипт

```bash
# Підключитись і виконати schema.sql
psql -U yield_user -d yield_db -f app/db/schema.sql
```

### 3. Налаштувати .env

```env
DATABASE_URL=postgresql://yield_user:your_password@localhost:5432/yield_db
```

### 4. Запустити код (коли буде реалізовано)

```bash
# Запуск FastAPI з БД
uvicorn app.main:app --reload
```

---

## 📚 Корисні Команди

```bash
# Підключитись до БД
psql -U yield_user -d yield_db

# Перевірити таблиці
\dt

# Переглянути структуру
\d earn_products

# Виконати запит
SELECT exchange, COUNT(*) FROM earn_products GROUP BY exchange;

# Вийти
\q
```

---

## 🎨 Рекомендації

### ✅ Що робити:

- Використовувати UPSERT замість DELETE+INSERT
- Зберігати історію для аналізу трендів APY
- Індексувати часто використовувані поля
- Регулярно робити VACUUM ANALYZE
- Робити backup перед великими змінами

### ❌ Чого не робити:

- Не зберігати дублікати
- Не видаляти історичні дані без причини
- Не ігнорувати індекси
- Не робити N+1 queries
- Не зберігати паролі в БД у відкритому вигляді

---

## 📖 Додаткові Ресурси

- **Детальна інструкція:** `POSTGRESQL_GUIDE.md`
- **Швидкий довідник:** `QUICK_REFERENCE.md`
- **SQL скрипт:** `schema.sql`
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## 🔄 Наступні Кроки

1. ✅ **Документація готова**
2. ⏳ **Реалізація коду** (по запиту користувача):
   - Частина 1: `database.py`
   - Частина 2: `models.py`
   - Частина 3: `crud.py`
   - Частина 4: Інтеграція з scheduler
   - Частина 5: API endpoints

---

**Створено:** 13.10.2024  
**Статус:** ✅ Документація готова, очікує реалізації коду
