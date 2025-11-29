# EarnAggregator - Платформа для пошуку кращих Yield пропозицій

**Версія:** 1.0.0

Повнофункціональна система для збору, агрегації та моніторингу даних про пасивний дохід (Yield/Earn продукти) з криптобірж.

## 🎯 Що це?

EarnAggregator - це мікросервісна платформа, яка:

- 📊 Збирає дані з Binance, Bybit та BitMart про Earn продукти
- 💾 Зберігає в PostgreSQL базі даних (440+ продукти)
- ⚡ Кешує в Redis для швидкого доступу
- 🔄 Автоматично оновлює дані кожну годину
- 📈 Моніторить стан через Prometheus + Grafana
- 🤖 Надає REST API для Telegram бота

## 🚀 Швидкий старт (1 хвилина)

```bash
# Клонувати репозиторій
git clone <repo>
cd EarnAggregator

# Запустити всі сервіси через Docker
docker-compose up -d

# Перевірити статус
./check_system_status.sh
```

**Готово!** Система працює на:

- 🌐 API: http://localhost:8000/docs
- 📊 Prometheus: http://localhost:9090
- 📈 Grafana: http://localhost:3000

Детальніше: [QUICK_START.md](QUICK_START.md)

## 🏗️ Архітектура

```
┌─────────────────────────────────────────────────────────┐
│               EarnAggregator Platform                    │
├─────────────────────────────────────────────────────────┤
│  🐳 Docker Services                                     │
│  ├─ PostgreSQL     (База даних - 353 products)          │
│  ├─ Redis          (Кеш - 1.13M)                        │
│  ├─ Yield API      (FastAPI - 24 endpoints)             │
│  ├─ Prometheus     (Metrics collection)                 │
│  └─ Grafana        (Visualization)                      │
├─────────────────────────────────────────────────────────┤
│  📡 API Endpoints                                       │
│  ├─ GET /api/v1/yield/{symbol}                         │
│  ├─ GET /api/v1/top                                    │
│  ├─ GET /api/v1/exchanges                              │
│  └─ GET /api/v1/health                                 │
├─────────────────────────────────────────────────────────┤
│  🔄 Data Flow                                          │
│  Exchange APIs → Scheduler → PostgreSQL → Redis → API │
└─────────────────────────────────────────────────────────┘
```

## 📦 Компоненти

### 1. Yield Data Service (FastAPI)

**Призначення:** REST API для отримання даних про Earn продукти

**Особливості:**
- 24 API endpoints
- Кешування через Redis
- Автоматичне оновлення даних
- Prometheus метрики

**Документація:** [API_ENDPOINTS_GUIDE.md](docs/API_ENDPOINTS_GUIDE.md)

### 2. Telegram Bot

**Призначення:** Інтерфейс для користувачів

**Особливості:**
- Пошук продуктів по символу
- Топ пропозиції за APY
- Фільтри по біржам
- Персоналізовані рекомендації

### 3. Monitoring Stack

**Компоненти:**
- Prometheus - збір метрик
- Grafana - візуалізація
- Логування в файли

**Документація:** [PROMETHEUS_GRAFANA_GUIDE.md](docs/PROMETHEUS_GRAFANA_GUIDE.md)

## 🛠️ Технології

- **Backend:** Python 3.13, FastAPI, SQLAlchemy, APScheduler
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Monitoring:** Prometheus, Grafana
- **Containerization:** Docker, Docker Compose
- **Bot:** aiogram 3.x

## 📚 Документація

- [Швидкий старт](docs/QUICK_START.md)
- [Архітектура проекту](docs/PROJECT_ARCHITECTURE.md)
- [API Endpoints](docs/API_ENDPOINTS_GUIDE.md)
- [Налаштування Docker](docs/docker-setup.md)
- [Моніторинг](docs/PROMETHEUS_GRAFANA_GUIDE.md)
- [Версійність](docs/VERSIONING_GUIDE.md)

## 🔄 Оновлення версії

Версія проекту керується через файл `VERSION` в корені проекту.

**Поточна версія:** 1.0.0

Детальніше: [VERSIONING_GUIDE.md](docs/VERSIONING_GUIDE.md)

## 📝 Ліцензія

MIT License

## 👥 Автори

<<<<<<< HEAD
### ✅ РОЗДІЛ 3.2: Бізнес-логіка

- Сервіс агрегації даних з 3 стратегіями
- Об'єднання даних з Binance та Bybit
- Кешування з fallback логікою
- Валідація якості даних (quality score)

### ✅ РОЗДІЛ 3.3: Scheduler

- 4 автоматичні задачі
- Оновлення кешу кожну годину
- Синхронізація БД кожну годину
- Health check кожні 15 хв
- Prometheus metrics

### ✅ Bonus: Моніторинг

- Prometheus для збору метрик
- Grafana для візуалізації
- Alert rules для критичних помилок
- Dashboard template

## 📊 Prometheus та Grafana - Як користуватися

### Prometheus (http://localhost:9090)

**Що це:** Система збору та зберігання метрик

**Як використовувати:**

1. Відкрити http://localhost:9090/targets - перевірити що всі targets UP
2. Відкрити http://localhost:9090/graph - виконати PromQL запити
3. Приклад запиту: `up{job="earnaggregator-api"}` - перевірка доступності

**Корисні розділи:**

- **Targets** - статус endpoints які Prometheus моніторить
- **Alerts** - активні alerts (якщо щось не так)
- **Graph** - візуалізація метрик

### Grafana (http://localhost:3000)

**Що це:** Платформа для створення dashboards та візуалізації

**Перше налаштування (2 хвилини):**

1. Відкрити http://localhost:3000
2. Login: `admin` / `admin`
3. Додати Prometheus data source:
   - ☰ → Connections → Data sources → Add
   - Type: **Prometheus**
   - URL: `http://prometheus:9090`
   - Save & test
4. Створити Dashboard:
   - ☰ → Dashboards → New
   - Add visualization
   - Query: `up{job="earnaggregator-api"}`
   - Apply → Save

**Для візуалізації наших JSON metrics:**

1. Встановити Infinity plugin:
   ```bash
   docker exec earn-grafana grafana-cli plugins install yesoreyeram-infinity-datasource
   docker restart earn-grafana
   ```
2. Додати Infinity data source:
   - URL: `http://yield-api:8000`
3. Створити панелі з нашими endpoints:
   - `/api/v1/stats` - Total Products
   - `/api/v1/cache/stats` - Cache Hit Rate
   - `/api/v1/scheduler/metrics` - Scheduler Metrics

**Детальний гайд:** [docs/PROMETHEUS_GRAFANA_GUIDE.md](docs/PROMETHEUS_GRAFANA_GUIDE.md)

**Швидке налаштування:** [docs/MONITORING_QUICK_SETUP.md](docs/MONITORING_QUICK_SETUP.md)

### Dashboard моніторингу

**Рекомендовані панелі:**

1. **Service Health** - статус БД, кешу, API бірж
2. **Total Products** - кількість продуктів в БД
3. **Cache Hit Rate** - ефективність кешування
4. **Scheduler Jobs** - виконані/провалені задачі
5. **API Response Times** - швидкість API
6. **BitMart Metrics** - `bitmart_products_count`, `bitmart_api_calls_total`, `bitmart_sync_duration_seconds`

**Приклад створення панелі:**

```
1. New Dashboard → Add visualization
2. Data source: Infinity (або Prometheus)
3. URL: /api/v1/stats
4. JSONPath: $.total_products
5. Visualization: Stat
6. Title: "Total Products"
7. Apply & Save
```

### Демонстрація

```bash
# Запустити інтерактивну демонстрацію
./demo_monitoring.sh
```

## 📈 Поточний статус системи

```
✅ Database:     440+ products (healthy)
✅ Cache:        Redis 1.13M (healthy)
✅ Binance API:  100 products (success)
✅ Bybit API:    253 products (success)
✅ BitMart API:  90 products (success)
✅ Scheduler:    4 jobs running
✅ Prometheus:   4 targets UP
✅ Grafana:      Ready for dashboards
```

## 🛠️ Корисні команди

### Швидка перевірка

```bash
./check_system_status.sh    # Статус всіх систем
./test_endpoints.sh          # Тест всіх endpoints
./test_scheduler.sh          # Тест scheduler
./demo_monitoring.sh         # Демо моніторингу
```

### Docker

```bash
docker-compose up -d         # Запустити всі сервіси
docker-compose down          # Зупинити всі сервіси
docker ps                    # Перевірити статус
docker logs earn-yield-api   # Переглянути логи
```

### Моніторинг

```bash
# Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Scheduler metrics
curl http://localhost:8000/api/v1/scheduler/metrics | python3 -m json.tool

# System health
curl http://localhost:8000/api/v1/health | python3 -m json.tool
```

## 📖 Документація

### Гайди

- [QUICK_START.md](QUICK_START.md) - Швидкий старт
- [docs/PULL_REQUEST_GUIDE.md](docs/PULL_REQUEST_GUIDE.md) - Гайд по Pull Requests з прикладами
- [docs/VERSIONING_GUIDE.md](docs/VERSIONING_GUIDE.md) - Керування версійністю проекту
- [docs/PROMETHEUS_GRAFANA_GUIDE.md](docs/PROMETHEUS_GRAFANA_GUIDE.md) - Повний гайд моніторингу
- [docs/MONITORING_QUICK_SETUP.md](docs/MONITORING_QUICK_SETUP.md) - Налаштування за 5 хв
- [docs/DOCKER_ENDPOINT_ACCESS_GUIDE.md](docs/DOCKER_ENDPOINT_ACCESS_GUIDE.md) - Docker та endpoints

### Звіти

- [SECTION_3_FINAL_REPORT.md](SECTION_3_FINAL_REPORT.md) - Підсумок РОЗДІЛУ 3
- [yield-data-service/SECTION_3_COMPLETE_REPORT.md](yield-data-service/SECTION_3_COMPLETE_REPORT.md) - Детальний звіт

### Компоненти

- [yield-data-service/app/services/README_aggregation.md](yield-data-service/app/services/README_aggregation.md) - Сервіс агрегації
- [yield-data-service/app/services/README_scheduler.md](yield-data-service/app/services/README_scheduler.md) - Scheduler
- [yield-data-service/monitoring/README.md](yield-data-service/monitoring/README.md) - Моніторинг

## 🎯 Статус проекту

**РОЗДІЛ 3: API та бізнес-логіка** - ✅ 100% ЗАВЕРШЕНО

- ✅ 3.1 API Routes (24 endpoints)
- ✅ 3.2 Business Logic (aggregation)
- ✅ 3.3 Scheduler (automated tasks)
- ✅ Prometheus + Grafana monitoring

**Наступний:** РОЗДІЛ 4 - Тестування та оптимізація

## 🤝 Контакти

Детальна документація в директорії `/docs`

---

# Yield Telegram Bot

Telegram бот для пошуку найкращих пропозицій пасивного доходу.

## Технології

- Aiogram 3.x - Telegram Bot framework
- httpx - HTTP клієнт
- PostgreSQL - база даних

## Команди

- /start - початок роботи
- /yield <SYMBOL> - інформація про монету
- /top [N] - топ N пропозицій
- /help - допомога

## Встановлення

1. Клонувати репозиторій
2. Створити бота через @BotFather
3. Створити .env файл з токеном
4. Встановити залежності: `pip install -r requirements.txt`
5. Запустити: `python -m bot.main`
=======
EarnAggregator Team
>>>>>>> 838651ea112ede6673d9ce4f82e973a4b448a2f6
