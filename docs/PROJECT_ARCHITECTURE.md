# EarnAggregator Project Architecture

## Огляд Архітектури

**EarnAggregator** - це мікросервісна платформа для збору, агрегації та моніторингу даних про пасивний дохід (Yield/Earn продукти) з криптовалютних бірж.

**Основні компоненти:**

- **Yield Data Service** - основний backend сервіс (FastAPI + PostgreSQL + Redis)
- **Telegram Bot** - клієнтський інтерфейс (Aiogram)
- **Frontend** - веб-інтерфейс (Next.js)
- **Monitoring** - Prometheus + Grafana для моніторингу

---

## Структура Проекту

```
EarnAggregator/
├── docker-compose.yml          # Оркестрація всіх сервісів
├── Dockerfile                  # Docker для yield-data-service
├── requirements.txt            # Python залежності
├── README.md                   # Головна документація
├── venv/                       # Python virtual environment
│
├── docs/                       # Документація
│   ├── PROMETHEUS_GRAFANA_GUIDE.md
│   ├── MONITORING_QUICK_SETUP.md
│   ├── API_ENDPOINTS_GUIDE.md
│   ├── DOCKER_ENDPOINT_ACCESS_GUIDE.md
│   └── ...
│
├── logs/                       # Глобальні логи
│   ├── app.log
│   └── errors.log
│
├── server/                     # Frontend (Next.js)
│   ├── node_modules/
│   ├── package.json
│   └── ...
│
├── yield-data-service/         # Основний backend сервіс
│   ├── app/                    # Джерельний код FastAPI
│   │   ├── main.py             # Точка входу FastAPI
│   │   ├── config.py           # Налаштування (Pydantic Settings)
│   │   ├── api/                # REST API endpoints
│   │   │   └── routes.py       # Всі API endpoints
│   │   ├── db/                 # База даних
│   │   │   ├── database.py     # Підключення до PostgreSQL
│   │   │   ├── models.py       # SQLAlchemy моделі
│   │   │   └── crud.py         # CRUD операції
│   │   ├── models/             # Pydantic моделі
│   │   │   ├── response.py     # API відповіді
│   │   │   └── yield_product.py # Yield продукти
│   │   ├── services/           # Бізнес-логіка
│   │   │   ├── scheduler.py    # Автоматичні задачі
│   │   │   ├── aggregation_service.py # Агрегація даних
│   │   │   ├── binance_service.py     # Binance інтеграція
│   │   │   ├── bybit_service.py       # Bybit інтеграція
│   │   │   ├── cache.py               # Redis кеш
│   │   │   └── __init__.py
│   │   ├── utils/              # Допоміжні функції
│   │   │   ├── logger.py       # Логування
│   │   │   └── helpers.py      # Утиліти
│   │   └── __init__.py
│   │
│   ├── logs/                   # Логи сервісу
│   │   ├── app.log
│   │   └── errors.log
│   │
│   ├── monitoring/             # Моніторинг конфігурації
│   │   ├── prometheus.yml      # Prometheus config
│   │   ├── alert_rules.yml     # Alert правила
│   │   ├── grafana_dashboard.json # Dashboard шаблон
│   │   └── README.md
│   │
│   ├── tests/                  # Тести
│   │   ├── conftest.py         # Pytest конфігурація
│   │   ├── test_api_endpoints.py
│   │   ├── test_binance_integration.py
│   │   └── ...
│   │
│   └── __pycache__/            # Python кеш
│
└── yield-telegram-bot/         # Telegram бот
    ├── bot/                    # Код бота
    │   ├── main.py             # Точка входу бота
    │   ├── config.py           # Налаштування бота
    │   ├── handlers/           # Обробники команд
    │   │   ├── start.py        # /start
    │   │   ├── yield_cmd.py    # /yield
    │   │   ├── top.py          # /top
    │   │   └── help.py         # /help
    │   ├── keyboards/          # Клавіатури
    │   │   ├── inline.py       # Inline клавіатури
    │   │   └── reply.py        # Reply клавіатури
    │   ├── middleware/         # Middleware
    │   │   └── logging.py      # Логування запитів
    │   ├── services/           # Бізнес-логіка бота
    │   │   ├── api_client.py   # Клієнт для API
    │   │   └── recommendations.py # Рекомендації
    │   └── utils/              # Утиліти
    │       ├── formatters.py   # Форматування повідомлень
    │       └── logger.py       # Логування
    │
    └── logs/                   # Логи бота
```

---

## Архітектура Сервісів

### 1. Yield Data Service (Основний Backend)

**Технології:** FastAPI, PostgreSQL, Redis, SQLAlchemy

**Відповідальність:**

- Збір даних з Binance та Bybit API
- Кешування в Redis
- Збереження в PostgreSQL
- Автоматична синхронізація
- REST API для інших сервісів

**Ключові компоненти:**

- **API Layer** (`api/routes.py`) - 24 endpoints
- **Business Logic** (`services/`) - агрегація, інтеграції
- **Scheduler** (`services/scheduler.py`) - фонові задачі
- **Database** (`db/`) - PostgreSQL + SQLAlchemy
- **Cache** (`services/cache.py`) - Redis

### 2. Telegram Bot Service

**Технології:** Aiogram 3.x, httpx

**Відповідальність:**

- Клієнтський інтерфейс для користувачів
- Спілкування з Data Service API
- Форматування та відображення даних

**Ключові компоненти:**

- **Handlers** - обробка команд (/yield, /top, /help)
- **Keyboards** - інтерактивні клавіатури
- **API Client** - HTTP клієнт для Data Service
- **Formatters** - форматування відповідей

### 3. Frontend Service (В розробці)

**Технології:** Next.js

**Відповідальність:**

- Веб-інтерфейс для користувачів
- Візуалізація даних з API
- Інтерактивні дашборди

### 4. Monitoring Stack

**Технології:** Prometheus, Grafana

**Відповідальність:**

- Збір метрик з сервісів
- Візуалізація стану системи
- Alerting при проблемах

**Ключові компоненти:**

- **Prometheus** - збір метрик
- **Grafana** - візуалізація
- **Alert Rules** - правила для alerts

---

## Зв'язки Між Компонентами

### Data Flow

```
Telegram Bot → Yield Data Service API → Database/Cache
Frontend     → Yield Data Service API → Database/Cache
Scheduler    → Exchange APIs → Database/Cache
Monitoring   → All Services → Grafana Dashboards
```

### API Dependencies

**Yield Data Service** не залежить від інших сервісів - є основним джерелом даних.

**Telegram Bot** залежить від:

- Yield Data Service API (http://yield-api:8000)

**Frontend** буде залежати від:

- Yield Data Service API (http://yield-api:8000)

**Monitoring** залежить від:

- Yield Data Service (для метрик)

### Database Schema

**Таблиці:**

- `yield_products` - основні дані продуктів
- `exchange_data` - дані по біржах
- `cache_metadata` - метадані кешу

**Зв'язки:** Всі таблиці зв'язані через символи криптовалют та ідентифікатори бірж.

### Cache Strategy

**Redis ключі:**

- `yield:{symbol}` - дані по монеті
- `top:yields:{limit}` - топ продукти
- `exchange:{exchange}:{symbol}` - дані з конкретної біржі

---

## Налаштування та Конфігурація

### Environment Variables

**Обов'язкові:**

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `BINANCE_API_KEY` - API ключ Binance
- `BYBIT_API_KEY` - API ключ Bybit

### Docker Services

**Основні сервіси:**

- `postgres` - база даних
- `redis` - кеш
- `yield-api` - основний API
- `prometheus` - моніторинг
- `grafana` - візуалізація

**Мережі:**

- `backend_net` - внутрішня мережа для всіх сервісів

---

## Розгортання

### Development

```bash
# Запуск всіх сервісів
docker-compose up -d

# Перевірка статусу
docker ps

# Логи сервісів
docker logs earn-yield-api
```

### Production

**Потрібно додати:**

- Environment variables для production
- Secrets management
- Health checks для всіх сервісів
- Backup стратегії

---

## Примітки

**Зрозумілі аспекти:**

- ✅ Зв'язки між сервісами через Docker networks
- ✅ API dependencies чітко визначені
- ✅ Data flow логічний: Bot → API → Database
- ✅ Cache integration зрозуміла
- ✅ Планується періодичне додавання нових бірж з API (наприклад: OKX, Coinbase та інших)


