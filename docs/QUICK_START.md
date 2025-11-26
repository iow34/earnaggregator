# EarnAggregator - Quick Start Guide

## 🚀 Швидкий старт

### 1. Запуск системи

```bash
# З кореневої директорії проекту
cd /Users/user777/Documents/EarnAggregator

# Запустити всі сервіси
docker-compose up -d

# Перевірити статус
./check_system_status.sh
```

### 2. Перевірка що все працює

```bash
# Health check
curl http://localhost:8000/api/v1/health | python3 -m json.tool

# Очікуваний результат:
# {
#   "database_status": "healthy",
#   "cache_status": "healthy",
#   "api_status": {
#     "binance": "success",
#     "bybit": "success"
#   }
# }
```

### 3. Синхронізація даних (якщо потрібно)

```bash
# Синхронізувати Binance
curl -X POST http://localhost:8000/api/v1/binance/sync

# Синхронізувати Bybit
curl -X POST http://localhost:8000/api/v1/bybit/sync

# Перевірити кількість продуктів
curl http://localhost:8000/api/v1/stats | python3 -m json.tool
```

## 📊 Основні endpoints

### Отримання даних

```bash
# Yield продукти для BTC
curl "http://localhost:8000/api/v1/yield/BTC?limit=10"

# Топ 20 пропозицій за APY
curl "http://localhost:8000/api/v1/top?limit=20"

# Дані з конкретної біржі
curl "http://localhost:8000/api/v1/exchanges?exchange=binance&limit=10"

# Список доступних бірж
curl "http://localhost:8000/api/v1/exchanges/list"
```

### Статистика

```bash
# Статистика БД
curl http://localhost:8000/api/v1/stats

# Статистика кешу
curl http://localhost:8000/api/v1/cache/stats

# Статистика агрегації
curl http://localhost:8000/api/v1/aggregation/stats
```

### Тестування

```bash
# Тест Binance API
curl http://localhost:8000/api/v1/binance/test

# Тест Bybit API
curl http://localhost:8000/api/v1/bybit/test

# Тест агрегації
curl "http://localhost:8000/api/v1/aggregation/test?strategy=fast_cache_first&limit=5"
```

## 🛠️ Корисні команди

### Docker

```bash
# Переглянути логи
docker logs earn-yield-api --tail 50 -f

# Перезапустити сервіс
docker restart earn-yield-api

# Перезібрати та запустити
docker-compose up -d --build yield-api

# Зупинити всі сервіси
docker-compose down
```

### База даних

```bash
# Підключитися до PostgreSQL
docker exec -it earn-postgres psql -U yield_user -d yield_db

# Перевірити таблиці
docker exec earn-postgres psql -U yield_user -d yield_db -c "\dt"

# Переглянути продукти
docker exec earn-postgres psql -U yield_user -d yield_db -c "SELECT COUNT(*) FROM yield_products;"
```

### Cache

```bash
# Очистити кеш
curl -X POST "http://localhost:8000/api/v1/cache/clear?pattern=*"

# Перевірити стан кешу
curl http://localhost:8000/api/v1/cache/health
```

## 📚 Документація

- **API Docs (Swagger):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Детальна документація:** [docs/DOCKER_ENDPOINT_ACCESS_GUIDE.md](docs/DOCKER_ENDPOINT_ACCESS_GUIDE.md)

## ✅ Поточний статус

Станом на 21.10.2025:

- ✅ **Database:** 353 products (healthy)
- ✅ **Cache:** Redis connected (healthy)
- ✅ **Binance API:** working (success)
- ✅ **Bybit API:** working (success)
- ✅ **Aggregation:** operational (31ms avg response)

**Всі системи працюють нормально!** 🎉

## 🔧 Troubleshooting

### Проблема: Database unhealthy

```bash
# Перевірити чи запущено PostgreSQL
docker ps | grep postgres

# Перезапустити PostgreSQL
docker restart earn-postgres

# Перевірити логи
docker logs earn-postgres
```

### Проблема: Cache unavailable

```bash
# Перевірити чи запущено Redis
docker ps | grep redis

# Перезапустити Redis
docker restart earn-redis
```

### Проблема: API не відповідає

```bash
# Перевірити статус контейнера
docker ps -a | grep yield-api

# Переглянути логи
docker logs earn-yield-api --tail 100

# Перезапустити
docker restart earn-yield-api
```

## 📞 Підтримка

Детальні звіти про виправлення:

- [ENDPOINTS_FIX_REPORT.md](yield-data-service/ENDPOINTS_FIX_REPORT.md)
- [FINAL_FIXES_REPORT.md](yield-data-service/FINAL_FIXES_REPORT.md)

Тести:

- [test_endpoints.sh](test_endpoints.sh) - тестування всіх endpoints
- [check_system_status.sh](check_system_status.sh) - швидка перевірка статусу
