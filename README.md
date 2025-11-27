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

EarnAggregator Team
