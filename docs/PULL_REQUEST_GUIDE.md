# 📚 Гайд по Pull Requests для EarnAggregator

## 🎯 Що таке Pull Request (PR)?

**Pull Request** (PR) — це механізм GitHub для запропонування змін у коді. Це дозволяє:

- Переглянути зміни перед мерджем
- Обговорити код з командою
- Запустити автоматичні тести
- Зберегти історію змін

---

## 🔄 Коли потрібно робити Pull Request?

### ✅ **Обов'язково робити PR:**

1. **Коли зливаєш `staging` → `main` (production)**

   - Це найважливіший випадок
   - Завжди потрібен рев'ю перед мерджем в production
   - Приклад: додавання нової функції, оновлення версії

2. **Коли зливаєш `feature/*` → `staging`**

   - Нова функція готова до тестування
   - Потрібно перевірити, що все працює разом
   - Приклад: додавання нової біржі, новий API endpoint

3. **Коли зливаєш `hotfix/*` → `main`**

   - Критичне виправлення помилки в production
   - Потрібен швидкий мердж, але все одно через PR
   - Приклад: виправлення критичного бага

4. **Коли зливаєш `bugfix/*` → `staging`**
   - Виправлення помилки в staging
   - Приклад: виправлення помилки в API

### ❌ **НЕ потрібно робити PR:**

1. **Коли працюєш локально на `feature/*` гілці**

   - Просто пушиш зміни: `git push origin feature/my-feature`
   - PR створиш тільки коли гілка готова

2. **Коли робиш коміти в свою гілку**
   - Локальні коміти не потребують PR
   - PR потрібен тільки для злиття гілок

---

## 📋 Структура гілок у вашому проекті

```
main (production)
  ↑
  └── staging (тестування)
       ↑
       └── feature/* (розробка)
            ├── feature/new-exchange
            ├── feature/api-improvements
            ├── feature/bot-enhancements
            ├── feature/scheduler-optimization
            └── hotfix/* (критичні виправлення)
```

### **Призначення гілок:**

| Гілка       | Призначення                 | Коли мерджити                    |
| ----------- | --------------------------- | -------------------------------- |
| `main`      | Production (бойова версія)  | Тільки через PR з staging        |
| `staging`   | Тестування перед production | Через PR з feature гілок         |
| `feature/*` | Розробка нових функцій      | Пуш без PR, PR тільки для мерджу |

---

## 🚀 Як створити Pull Request (покроково)

### **Сценарій 1: Feature → Staging**

#### Крок 1: Створити feature гілку та зробити зміни

```bash
# 1. Переконатися, що ти на staging
git checkout staging
git pull origin staging

# 2. Створити нову feature гілку
git checkout -b feature/add-nexo-exchange

# 3. Зробити зміни в коді
# ... редагуєш файли ...

# 4. Закомітити зміни
git add .
git commit -m "feat: додано інтеграцію з біржею Nexo"

# 5. Запушити гілку на GitHub
git push origin feature/add-nexo-exchange
```

#### Крок 2: Створити Pull Request через GitHub UI

1. **Перейти на GitHub:**

   - Відкрити: https://github.com/iow34/earnaggregator
   - Натиснути кнопку **"Compare & pull request"** (з'явиться після push)

2. **Заповнити форму PR:**

   ```
   Title: feat: додано інтеграцію з біржею Nexo

   Description:
   ## Що зроблено
   - ✅ Додано API клієнт для Nexo
   - ✅ Додано сервіс для отримання продуктів
   - ✅ Додано Nexo в exchange_registry
   - ✅ Оновлено документацію

   ## Тестування
   - ✅ Локально протестовано
   - ✅ API endpoint працює
   - ✅ Продукти відображаються
   ```

3. **Налаштування PR:**

   - **Base branch:** `staging` (куди мерджимо)
   - **Compare branch:** `feature/add-nexo-exchange` (що мерджимо)
   - **Reviewers:** (опціонально) додати рев'юерів
   - **Labels:** додати `feature`, `enhancement`

4. **Створити PR:**
   - Натиснути **"Create pull request"**

#### Крок 3: Очікувати рев'ю та мердж

- GitHub автоматично запустить тести (якщо налаштовано CI/CD)
- Після рев'ю та проходження тестів — мердж PR
- Після мерджу можна видалити feature гілку

---

### **Сценарій 2: Staging → Main (Production)**

#### Крок 1: Переконатися, що staging готовий

```bash
# 1. Перевірити, що staging стабільний
git checkout staging
git pull origin staging

# 2. Перевірити, що все працює
docker-compose -f docker-compose.staging.yml up -d
# Тестувати API, бот, тощо
```

#### Крок 2: Створити PR через GitHub UI

1. **Перейти на GitHub:**

   - https://github.com/iow34/earnaggregator
   - Натиснути **"New pull request"**

2. **Налаштування PR:**

   - **Base branch:** `main` (production)
   - **Compare branch:** `staging` (що мерджимо)
   - **Title:** `Release v1.1.0 - Nexo integration and improvements`

3. **Опис PR (детальний):**

   ```markdown
   ## 🚀 Release v1.1.0

   ### Основні зміни:

   - ✅ Додано інтеграцію з біржею Nexo
   - ✅ Оновлено scheduler інтервали
   - ✅ Додано версійність проекту
   - ✅ Виправлено помилки в API

   ### Тестування:

   - ✅ Staging тестування пройдено
   - ✅ Всі API endpoints працюють
   - ✅ Telegram бот працює коректно
   - ✅ Моніторинг показує healthy статус

   ### Deployment:

   - [ ] Оновити версію в VERSION файлі
   - [ ] Створити тег v1.1.0 після мерджу
   - [ ] Оновити CHANGELOG.md
   ```

4. **Створити PR:**
   - Натиснути **"Create pull request"**

#### Крок 3: Після мерджу

```bash
# 1. Оновити локальну main гілку
git checkout main
git pull origin main

# 2. Створити тег для версії
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0

# 3. Оновити staging з main (якщо потрібно)
git checkout staging
git merge main
git push origin staging
```

---

## 📝 Детальні приклади Pull Requests для EarnAggregator

### **Приклад 1: Додавання нової біржі (Kraken)**

**Гілка:** `feature/add-kraken-exchange` → `staging`

**Контекст:** Потрібно додати нову біржу Kraken до системи. Це включає створення API клієнта, сервісу, моделей та інтеграцію в exchange_registry.

**Опис PR:**

```markdown
## feat: додано інтеграцію з біржею Kraken

### 🎯 Що зроблено:

- ✅ Створено `yield-data-service/app/services/exchanges/kraken/api.py` - API клієнт для Kraken
- ✅ Створено `yield-data-service/app/services/exchanges/kraken/service.py` - сервіс для отримання продуктів
- ✅ Створено `yield-data-service/app/services/exchanges/kraken/models.py` - Pydantic моделі для даних
- ✅ Додано Kraken в `yield-data-service/app/services/exchanges/registry.py`
- ✅ Додано тести в `yield-data-service/tests/test_kraken.py`
- ✅ Оновлено документацію `docs/NEW_EXCHANGE_INTEGRATION_GUIDE.md`

### 🔧 Технічні деталі:

- API використовує Kraken REST API v0
- Підтримуються Flexible та Locked продукти
- Додано обробку помилок та retry логіку
- Кешування через Redis (TTL: 60 хвилин)

### 🧪 Тестування:

- ✅ Локально протестовано отримання продуктів
- ✅ API endpoint `/api/v1/exchanges?exchange=kraken` працює
- ✅ Продукти відображаються в Telegram боті
- ✅ Scheduler синхронізує дані з Kraken
- ✅ Unit тести пройдені (покриття: 85%)

### 📊 Метрики:

- Додано файлів: 4
- Додано рядків: +450
- Видалено рядків: -0

### 🔗 Пов'язані файли:

- `yield-data-service/app/services/exchanges/kraken/api.py`
- `yield-data-service/app/services/exchanges/kraken/service.py`
- `yield-data-service/app/services/exchanges/kraken/models.py`
- `yield-data-service/app/services/exchanges/registry.py`
- `yield-data-service/tests/test_kraken.py`

### ⚠️ Потенційні ризики:

- Kraken API може мати rate limits - додано обробку
- Потрібно перевірити на staging перед production
```

---

### **Приклад 2: Виправлення помилки відображення APY (Gate)**

**Гілка:** `bugfix/fix-gate-apy-display` → `staging`

**Контекст:** Gate продукти показували APY 0.0% замість реальних значень. Проблема була в неузгодженості назв біржі в різних таблицях БД.

**Опис PR:**

```markdown
## fix: виправлено відображення APY для Gate біржі

### 🐛 Проблема:

Gate продукти показували APY 0.0% замість реальних значень в Telegram боті та API.

**Повідомлення помилки:**
```

Gate перейти ↗️ 📊 BTC 0.0% • ETH 0.0% • SOL 0.0% • USDT 0.0%

````

### 🔍 Причина:
Неузгодженість назв біржі в різних таблицях БД:
- `exchange_data` таблиця: `gate`
- `yield_products` таблиця: `Gate.io`
- `priority_products` таблиця: `gate`

Це призводило до того, що запити не знаходили продукти.

### ✅ Виправлення:
- ✅ Уніфіковано назву біржі до `gate` (lowercase) в усіх місцях
- ✅ Створено міграцію БД `004_fix_gate_naming.sql` для оновлення існуючих записів
- ✅ Додано маппінг `EXCHANGE_TO_PROVIDER` в `priority_products_service.py`
- ✅ Оновлено `yield-data-service/app/services/exchanges/gate/api.py`
- ✅ Оновлено `yield-data-service/app/services/exchanges/gate/service.py`
- ✅ Оновлено `yield-data-service/app/services/exchanges/gate/models.py`

### 🧪 Тестування:
- ✅ Перевірено відображення APY для Gate в Telegram боті
- ✅ Продукти відображаються коректно: `Gate 📊 BTC 2.5% • ETH 3.1% • SOL 4.2% • USDT 5.0%`
- ✅ Міграція БД виконана успішно на staging
- ✅ API endpoint `/api/v1/priority-products/gate` повертає коректні дані
- ✅ Перевірено всі інші біржі - працюють коректно

### 📊 Вплив:
- Змінено файлів: 6
- Оновлено записів в БД: 127 (всі Gate продукти)
- Виправлено відображення для 4 основних продуктів (BTC, ETH, SOL, USDT)

### 🔄 Rollback:
Якщо щось піде не так:
```sql
-- Відкотити назви в yield_products
UPDATE yield_products SET provider = 'Gate.io' WHERE provider = 'gate';
````

### ⚠️ Важливо:

- Міграцію потрібно виконати на production після мерджу
- Перевірити, що всі інші біржі не постраждали

````

---

### **Приклад 3: Оновлення інтервалів Scheduler**

**Гілка:** `feature/optimize-scheduler-intervals` → `staging`

**Контекст:** Потрібно оптимізувати інтервали scheduler для зменшення навантаження на API бірж та базу даних.

**Опис PR:**
```markdown
## feat: оптимізовано інтервали scheduler для зменшення навантаження

### 🎯 Мета:
Зменшити навантаження на API бірж та базу даних шляхом оптимізації інтервалів scheduler.

### 📊 Поточні інтервали (були):
- `update_cache_job`: кожні 1 годину
- `update_database_job`: кожні 1 годину
- `health_check_job`: кожні 15 хвилин
- `update_popular_symbols_job`: кожні 30 хвилин

### ✅ Нові інтервали:
- `update_cache_job`: кожні **12 годин** (було: 1 година)
- `update_database_job`: кожні **12 годин** (було: 1 година)
- `health_check_job`: кожні **8 годин** (було: 15 хвилин)
- `update_popular_symbols_job`: кожні **6 годин** (було: 30 хвилин)

### 🔧 Технічні зміни:
- ✅ Оновлено `yield-data-service/app/services/scheduler.py`
- ✅ Змінено `IntervalTrigger(hours=1)` на `IntervalTrigger(hours=12)` для cache та DB
- ✅ Змінено `IntervalTrigger(minutes=15)` на `IntervalTrigger(hours=8)` для health check
- ✅ Змінено `IntervalTrigger(minutes=30)` на `IntervalTrigger(hours=6)` для popular symbols
- ✅ Оновлено документацію в коментарях

### 📈 Очікуваний ефект:
- **Зменшення API запитів:** ~95% (з 96 до ~5 запитів на день)
- **Зменшення навантаження на БД:** ~95%
- **Економія ресурсів:** значна економія CPU та пам'яті
- **Продуктивність:** дані все одно оновлюються достатньо часто для користувачів

### 🧪 Тестування:
- ✅ Scheduler запускається коректно з новими інтервалами
- ✅ Всі задачі виконуються вчасно
- ✅ Логи показують правильні інтервали
- ✅ Prometheus метрики відображають нові інтервали
- ✅ Тестовано на staging протягом 24 годин

### ⚠️ Потенційні ризики:
- Дані можуть бути трохи менш актуальні (але все одно оновлюються 2 рази на день)
- Потрібно моніторити, чи достатньо цього для користувачів

### 📝 Документація:
- Оновлено коментарі в `scheduler.py`
- Додано пояснення в `docs/SCHEDULER_ANALYSIS_REPORT.md`
````

---

### **Приклад 4: Додавання версійності проекту**

**Гілка:** `feature/add-versioning` → `staging`

**Контекст:** Потрібно додати централізовану версійність проекту для відстеження релізів.

**Опис PR:**

````markdown
## feat: додано централізовану версійність проекту v1.0.0

### 🎯 Мета:

Реалізувати централізоване управління версією проекту через файл `VERSION`.

### ✅ Що зроблено:

- ✅ Створено файл `VERSION` в корені проекту з версією `1.0.0`
- ✅ Створено модуль `yield-data-service/app/__version__.py` для читання версії
- ✅ Оновлено `yield-data-service/app/main.py` - використовує `__version__`
- ✅ Оновлено `yield-data-service/app/models/response.py` - `HealthResponse` використовує версію
- ✅ Оновлено `yield-data-service/app/api/routes.py` - health endpoints показують версію
- ✅ Створено документацію `docs/VERSIONING_GUIDE.md`

### 🔧 Технічна реалізація:

- Версія читається з файлу `VERSION` автоматично
- Модуль `__version__.py` надає функцію `get_version()` та змінну `__version__`
- Версія відображається в:
  - FastAPI метаданих (Swagger UI)
  - API endpoints (`GET /`, `GET /api/v1/health`)
  - HealthResponse моделях

### 🧪 Тестування:

- ✅ Версія відображається в Swagger UI (`/docs`)
- ✅ API endpoint `GET /` повертає `{"version": "1.0.0"}`
- ✅ API endpoint `GET /api/v1/health` повертає версію
- ✅ Локально протестовано читання версії з файлу

### 📊 Файли:

- `VERSION` (новий)
- `yield-data-service/app/__version__.py` (новий)
- `yield-data-service/app/main.py` (оновлено)
- `yield-data-service/app/models/response.py` (оновлено)
- `yield-data-service/app/api/routes.py` (оновлено)
- `docs/VERSIONING_GUIDE.md` (новий)

### 🔄 Оновлення версії в майбутньому:

Для оновлення версії достатньо змінити файл `VERSION`:

```bash
echo "1.0.1" > VERSION
docker-compose restart yield-api
```
````

### 📝 Документація:

Детальний гайд: `docs/VERSIONING_GUIDE.md`

````

---

### **Приклад 5: Додавання нового API endpoint**

**Гілка:** `feature/add-priority-products-endpoint` → `staging`

**Контекст:** Потрібно додати новий API endpoint для отримання пріоритетних продуктів (BTC, ETH, SOL, USDT) для кожної біржі.

**Опис PR:**
```markdown
## feat: додано API endpoint для пріоритетних продуктів

### 🎯 Мета:
Оптимізувати вивід основних продуктів (BTC, ETH, SOL, USDT) через окремий endpoint.

### ✅ Що зроблено:
- ✅ Створено таблицю `priority_products` в БД
- ✅ Створено модель `PriorityProductDB` в `yield-data-service/app/db/models.py`
- ✅ Створено CRUD операції в `yield-data-service/app/db/crud.py`
- ✅ Створено сервіс `priority_products_service.py` для оновлення даних
- ✅ Додано endpoint `GET /api/v1/priority-products/{exchange}` в `routes.py`
- ✅ Інтегровано з scheduler для автоматичного оновлення
- ✅ Додано міграцію БД `003_create_priority_products_table.sql`

### 🔧 Технічні деталі:
- Endpoint: `GET /api/v1/priority-products/{exchange}`
- Повертає завжди 4 продукти (BTC, ETH, SOL, USDT) в правильному порядку
- Якщо продукт не знайдено - повертає з APY=0.0
- Дані оновлюються автоматично через scheduler

### 🧪 Тестування:
- ✅ Endpoint працює для всіх бірж: `/api/v1/priority-products/binance`
- ✅ Повертає правильний порядок: BTC → ETH → SOL → USDT
- ✅ Обробляє випадок, коли продукт не знайдено (APY=0.0)
- ✅ Scheduler оновлює дані автоматично
- ✅ Telegram бот використовує новий endpoint

### 📊 Приклад відповіді:
```json
{
  "success": true,
  "data": [
    {"symbol": "BTC", "apy": 2.5, "exchange": "binance"},
    {"symbol": "ETH", "apy": 3.1, "exchange": "binance"},
    {"symbol": "SOL", "apy": 4.2, "exchange": "binance"},
    {"symbol": "USDT", "apy": 5.0, "exchange": "binance"}
  ]
}
````

### 🔗 Пов'язані файли:

- `yield-data-service/app/db/models.py`
- `yield-data-service/app/db/crud.py`
- `yield-data-service/app/services/priority_products_service.py`
- `yield-data-service/app/api/routes.py`
- `yield-data-service/app/db/migrations/003_create_priority_products_table.sql`
- `yield-telegram-bot/bot/services/api_client.py`
- `yield-telegram-bot/bot/handlers/main_menu.py`

````

---

### **Приклад 6: Виправлення помилки в Telegram боті**

**Гілка:** `bugfix/fix-telegram-bot-commands` → `staging`

**Контекст:** Команди `/start` та `/help` перестали працювати після останніх змін.

**Опис PR:**
```markdown
## fix: виправлено роботу команд /start та /help в Telegram боті

### 🐛 Проблема:
Після останніх змін команди `/start` та `/help` перестали працювати в Telegram боті.

**Помилка в логах:**
````

SyntaxError: invalid syntax. Perhaps you forgot a comma?
File: yield-telegram-bot/bot/handlers/main_menu.py, line 45

````

### 🔍 Причина:
Синтаксична помилка в `main_menu.py` - неправильне використання функції `_format_exchange_display_name()` всередині аргументів `await message.answer()`.

### ✅ Виправлення:
- ✅ Виправлено синтаксис в `yield-telegram-bot/bot/handlers/main_menu.py`
- ✅ Виправлено синтаксис в `yield-telegram-bot/bot/handlers/exchange_products.py`
- ✅ Виправлено синтаксис в `yield-telegram-bot/bot/handlers/callback_handlers.py`
- ✅ Переміщено виклик `_format_exchange_display_name()` на окремий рядок перед використанням

### 🔧 Технічні деталі:
**Було (неправильно):**
```python
await message.answer(
    text=f"{_format_exchange_display_name(provider)} продукти",
    ...
)
````

**Стало (правильно):**

```python
display_name = _format_exchange_display_name(provider)
await message.answer(
    text=f"{display_name} продукти",
    ...
)
```

### 🧪 Тестування:

- ✅ Команда `/start` працює коректно
- ✅ Команда `/help` працює коректно
- ✅ Всі інші команди працюють
- ✅ Відображення назв бірж коректне
- ✅ Локально протестовано в Docker

### 📊 Вплив:

- Виправлено файлів: 3
- Відновлено роботу 2 основних команд
- Всі інші команди працюють коректно

### ⚠️ Важливо:

- Перевірити, що бот працює на staging перед мерджем в production
- Перезапустити бот після мерджу

````

---

### **Приклад 7: Production Release (Staging → Main)**

**Гілка:** `staging` → `main`

**Контекст:** Готуємо реліз версії 1.0.0 з усіма накопиченими змінами.

**Опис PR:**
```markdown
## 🚀 Release v1.0.0 - Initial Stable Release

### 📦 Основні зміни:

#### Нова функціональність:
- ✅ Додано централізовану версійність проекту
- ✅ Додано інтеграцію з 9 біржами (Binance, Bybit, BitMart, OKX, Gate, Bitget, Kraken, KuCoin, HTX, MEXC)
- ✅ Додано оптимізацію через priority_products таблицю
- ✅ Додано автоматичний scheduler для оновлення даних

#### Виправлення:
- ✅ Виправлено відображення APY для Gate біржі
- ✅ Виправлено роботу команд Telegram бота
- ✅ Виправлено інтервали scheduler для оптимізації

#### Оптимізації:
- ✅ Оптимізовано інтервали scheduler (кеш та БД кожні 12 год)
- ✅ Додано кешування через Redis
- ✅ Оптимізовано запити до БД

### 🧪 Тестування на Staging:
- ✅ Всі API endpoints працюють коректно (24 endpoints)
- ✅ Telegram бот працює без помилок
- ✅ Scheduler виконує задачі вчасно
- ✅ Моніторинг показує healthy статус
- ✅ Версія відображається в API responses
- ✅ Всі біржі синхронізуються коректно
- ✅ Тестування тривало 3 дні на staging

### 📊 Метрики:
- **Змінено файлів:** 45
- **Додано рядків:** +2,340
- **Видалено рядків:** -890
- **Нових endpoints:** 3
- **Нових бірж:** 9
- **Покриття тестами:** 78%

### 🚀 Deployment план:
1. ✅ Змерджити PR
2. ✅ Створити тег v1.0.0
3. ✅ Запустити deployment на production
4. ✅ Перевірити health check endpoints
5. ✅ Моніторити логи перші 24 години

### 🔄 Rollback план:
Якщо щось піде не так:
```bash
# 1. Відкотити до попереднього коміту
git revert 51313ec15e5d40bdf80f3a6cfc347cca660ad36e

# 2. Перезапустити сервіси
docker-compose -f docker-compose.prod.yml restart

# 3. Перевірити статус
curl https://api.earnaggregator.com/health
````

### 📝 Документація:

- ✅ Оновлено README.md
- ✅ Додано VERSIONING_GUIDE.md
- ✅ Оновлено API_ENDPOINTS_GUIDE.md
- ✅ Додано SCHEDULER_ANALYSIS_REPORT.md

### ⚠️ Потенційні ризики:

- Перший production реліз - потрібен ретельний моніторинг
- Міграція БД потрібна для priority_products таблиці
- Перевірити, що всі секрети налаштовані на production

### ✅ Чек-лист перед мерджем:

- [x] Всі тести пройдені на staging
- [x] Staging працює стабільно 3 дні
- [x] Версія оновлена в VERSION файлі
- [x] Документація оновлена
- [x] Rollback план готовий
- [x] Моніторинг налаштований
- [x] Health checks працюють

````

---

### **Приклад 8: Hotfix - Критичне виправлення в Production**

**Гілка:** `hotfix/fix-critical-api-error` → `main`

**Контекст:** Виявлено критичну помилку в production - API повертає 500 помилку для деяких запитів.

**Опис PR:**
```markdown
## 🚨 HOTFIX: виправлено критичну помилку в API endpoint

### 🐛 Критична проблема:
API endpoint `/api/v1/yield/{symbol}` повертає 500 помилку для символів з спеціальними символами.

**Помилка:**
````

Internal Server Error: KeyError: 'symbol'
File: yield-data-service/app/api/routes.py, line 123

````

### 🔍 Причина:
Відсутня обробка випадку, коли символ містить спеціальні символи або не існує в кеші.

### ✅ Виправлення:
- ✅ Додано валідацію символу перед обробкою
- ✅ Додано обробку помилок для відсутніх символів
- ✅ Додано fallback логіку для спеціальних символів
- ✅ Додано тести для edge cases

### 🧪 Тестування:
- ✅ Протестовано з різними символами (BTC, ETH, SOL, USDT)
- ✅ Протестовано з неіснуючими символами
- ✅ Протестовано зі спеціальними символами
- ✅ Локально протестовано

### ⚡ Швидкий deployment:
Це hotfix - потрібен швидкий мердж та deployment.

### 🔄 Rollback:
Якщо щось піде не так:
```bash
git revert <hotfix-commit-sha>
docker-compose -f docker-compose.prod.yml restart
````

### 📊 Вплив:

- Виправлено файлів: 1
- Виправлено критичну помилку
- Відновлено роботу API для всіх символів

````

---

### **Приклад 9: Додавання міграції БД**

**Гілка:** `feature/add-priority-products-migration` → `staging`

**Контекст:** Потрібно додати нову таблицю `priority_products` в БД через міграцію.

**Опис PR:**
```markdown
## feat: додано міграцію БД для таблиці priority_products

### 🎯 Мета:
Створити таблицю `priority_products` для оптимізації виводу основних продуктів.

### ✅ Що зроблено:
- ✅ Створено міграцію `003_create_priority_products_table.sql`
- ✅ Додано таблицю з полями: id, exchange, symbol, apy, is_active, product_id, lock_period_days, created_at, updated_at
- ✅ Додано унікальний індекс на (exchange, symbol)
- ✅ Додано індекси для швидкого пошуку
- ✅ Додано автоматичне оновлення updated_at через тригер

### 🔧 Технічні деталі:
```sql
CREATE TABLE priority_products (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    apy FLOAT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    product_id VARCHAR(255),
    lock_period_days INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol)
);
````

### 🧪 Тестування:

- ✅ Міграція виконується без помилок
- ✅ Таблиця створюється коректно
- ✅ Індекси працюють
- ✅ Унікальне обмеження працює
- ✅ Тестовано на staging БД

### 📊 Вплив:

- Створено нову таблицю
- Додано індекси для оптимізації
- Не впливає на існуючі таблиці

### ⚠️ Важливо:

- Міграцію потрібно виконати на production після мерджу
- Перевірити, що немає конфліктів з існуючими даними
- Зробити backup БД перед міграцією на production

````

---

### **Приклад 10: Оновлення Telegram бота (локалізація)**

**Гілка:** `feature/add-nexo-placeholder-localization` → `staging`

**Контекст:** Потрібно додати заглушку для Nexo біржі з локалізацією для всіх мов (UA, RU, EN).

**Опис PR:**
```markdown
## feat: додано локалізовану заглушку для Nexo біржі

### 🎯 Мета:
Додати заглушку для команди `/all_nexo_products` з локалізацією та реферальним посиланням.

### ✅ Що зроблено:
- ✅ Додано обробку Nexo в `yield-telegram-bot/bot/handlers/exchange_products.py`
- ✅ Додано локалізацію в `yield-telegram-bot/bot/localization/texts/messages.json`:
  - UA: "Продукти біржі Nexo будуть додані пізніше..."
  - RU: "Продукты биржи Nexo будут добавлены позже..."
  - EN: "Nexo exchange products will be added later..."
- ✅ Додано генерацію трекінгового посилання з реферальним URL
- ✅ Додано HTML форматування для посилання

### 🔧 Технічні деталі:
- Використовується функція `_get_tracking_link()` для генерації посилання
- Реферальне посилання береться з `.env` файлу (`REFERRAL_NEXO`)
- Локалізація працює для всіх підтримуваних мов

### 🧪 Тестування:
- ✅ Команда `/all_nexo_products` працює для UA мови
- ✅ Команда `/all_nexo_products` працює для RU мови
- ✅ Команда `/all_nexo_products` працює для EN мови
- ✅ Трекінгове посилання генерується коректно
- ✅ Реферальне посилання працює
- ✅ Локально протестовано в Docker

### 📊 Файли:
- `yield-telegram-bot/bot/handlers/exchange_products.py` (оновлено)
- `yield-telegram-bot/bot/localization/texts/messages.json` (оновлено)

### 🔗 Приклад повідомлення:
**UA:**
````

Продукти біржі <a href="https://tracking.earnaggregator.com/ref?exchange=nexo&user_id=123">Nexo</a> будуть додані пізніше...

```

### ⚠️ Важливо:
- Перевірити, що `REFERRAL_NEXO` налаштовано в `.env` файлі
- Перевірити, що tracking сервер працює
```

---

## ⚠️ Важливі правила

### **1. Ніколи не мерджити без PR:**

```bash
# ❌ НЕПРАВИЛЬНО:
git checkout main
git merge staging
git push origin main

# ✅ ПРАВИЛЬНО:
# Створити PR через GitHub UI
# Дождатися рев'ю та тестів
# Змерджити через GitHub UI
```

### **2. Завжди оновлювати base гілку перед PR:**

```bash
# Перед створенням PR:
git checkout staging
git pull origin staging
git checkout feature/my-feature
git merge staging  # або git rebase staging
git push origin feature/my-feature
```

### **3. Використовувати зрозумілі назви PR:**

```bash
# ❌ Погано:
"fix"
"update"
"changes"

# ✅ Добре:
"feat: додано інтеграцію з Kraken"
"fix: виправлено відображення APY для Gate"
"docs: оновлено API документацію"
```

### **4. Додавати опис до PR:**

- Що зроблено
- Чому це потрібно
- Як тестувати
- Потенційні ризики

---

## 🔄 Типовий workflow для вашого проекту

### **День 1: Розробка нової функції**

```bash
# 1. Створити feature гілку
git checkout staging
git pull origin staging
git checkout -b feature/add-mexc-exchange

# 2. Розробка
# ... редагуєш код ...

# 3. Коміти
git add .
git commit -m "feat: додано API клієнт для MEXC"
git commit -m "feat: додано MEXC в exchange_registry"
git commit -m "test: додано тести для MEXC"

# 4. Push (без PR поки що)
git push origin feature/add-mexc-exchange
```

### **День 2: Тестування та PR**

```bash
# 1. Локальне тестування
docker-compose up -d
# Тестуєш API, перевіряєш логи

# 2. Створити PR через GitHub UI
# feature/add-mexc-exchange → staging

# 3. Очікувати рев'ю (якщо є команда)
# Або самостійно перевірити та змерджити
```

### **День 3: Мердж в staging**

```bash
# Після мерджу PR:
git checkout staging
git pull origin staging

# Перевірити, що все працює
docker-compose -f docker-compose.staging.yml up -d
```

### **День 4: Release в production**

```bash
# 1. Створити PR staging → main
# Через GitHub UI

# 2. Після мерджу:
git checkout main
git pull origin main

# 3. Створити тег
git tag -a v1.1.0 -m "Release v1.1.0 - MEXC integration"
git push origin v1.1.0

# 4. Deployment на production
# (автоматично через CI/CD або вручну)
```

---

## 🛠️ Корисні команди для PR

### **Перевірка статусу перед PR:**

```bash
# Подивитися різницю між гілками
git diff staging..feature/my-feature

# Подивитися список комітів
git log staging..feature/my-feature

# Перевірити, чи немає конфліктів
git checkout staging
git pull origin staging
git checkout feature/my-feature
git merge staging --no-commit --no-ff
# Якщо конфліктів немає:
git merge --abort
```

### **Після мерджу PR:**

```bash
# Оновити локальні гілки
git checkout staging
git pull origin staging

# Видалити локальну feature гілку
git branch -d feature/my-feature

# Видалити remote feature гілку (якщо потрібно)
git push origin --delete feature/my-feature
```

---

## 📊 Checklist перед створенням PR

### **Для Feature PR:**

- [ ] Код відповідає стандартам проекту
- [ ] Додано/оновлено тести
- [ ] Оновлено документацію (якщо потрібно)
- [ ] Локально протестовано
- [ ] Немає конфліктів з base гілкою
- [ ] Коміти мають зрозумілі повідомлення
- [ ] Додано опис до PR

### **Для Production Release PR:**

- [ ] Всі тести пройдені на staging
- [ ] Staging працює стабільно мінімум 1-2 дні
- [ ] Версія оновлена в VERSION файлі
- [ ] CHANGELOG.md оновлений
- [ ] Документація оновлена
- [ ] Rollback план готовий
- [ ] Моніторинг налаштований

---

## 🎓 Висновок

**Коли робити PR:**

1. ✅ Feature → Staging (нова функція)
2. ✅ Staging → Main (production release)
3. ✅ Hotfix → Main (критичне виправлення)
4. ✅ Bugfix → Staging (виправлення помилки)

**Коли НЕ робити PR:**

1. ❌ Локальні коміти в feature гілку
2. ❌ Push в свою feature гілку

**Головне правило:**

> **Завжди мерджити через PR, ніколи напряму в main або staging!**


