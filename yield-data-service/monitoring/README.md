# Monitoring Setup 

## Огляд

Ця директорія містить конфігурації для моніторингу EarnAggregator Data Service через Prometheus та Grafana.

## Файли

- **`prometheus.yml`** - конфігурація Prometheus для збору метрик
- **`alert_rules.yml`** - правила для alerting при проблемах
- **`grafana_dashboard.json`** - готовий dashboard для Grafana

## Швидкий старт

### 1. Запуск Prometheus

```bash
# З Docker
docker run -d \
  --name prometheus \
  --network earnaggregator_backend_net \
  -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v $(pwd)/monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml \
  prom/prometheus:latest
```

### 2. Запуск Grafana

```bash
# З Docker
docker run -d \
  --name grafana \
  --network earnaggregator_backend_net \
  -p 3000:3000 \
  grafana/grafana:latest
```

### 3. Налаштування Grafana

1. Відкрити http://localhost:3000
2. Login: `admin` / `admin`
3. Додати Prometheus data source:
   - URL: `http://prometheus:9090`
4. Імпортувати dashboard:
   - Upload `grafana_dashboard.json`

## Метрики

### Scheduler Metrics

**Endpoint:** `/api/v1/scheduler/metrics`

Metrics:

- `jobs_executed_total` - загальна кількість виконаних задач
- `jobs_failed_total` - провалені задачі
- `cache_updates_total` - оновлення кешу
- `db_syncs_total` - синхронізації БД
- `api_calls_total` - API виклики
- `average_execution_time_ms` - середній час виконання

### Cache Metrics

**Endpoint:** `/api/v1/cache/stats`

Metrics:

- `cache_hits` - попадання в кеш
- `cache_misses` - промахи
- `cache_hit_rate_percent` - відсоток попадань
- `redis_memory_used` - використана пам'ять Redis

### Health Metrics

**Endpoint:** `/api/v1/health`

Metrics:

- `database_status` - стан БД (healthy/unhealthy)
- `cache_status` - стан кешу (healthy/degraded/unhealthy)
- `api_status_binance` - стан Binance API
- `api_status_bybit` - стан Bybit API

## Alerts

### Critical Alerts (🚨)

- **BinanceAPIDown** - Binance API недоступний більше 10 хв
- **BybitAPIDown** - Bybit API недоступний більше 10 хв
- **DatabaseUnhealthy** - БД недоступна більше 5 хв
- **NoProductsInDatabase** - БД порожня
- **SchedulerNotRunning** - Scheduler зупинено

### Warning Alerts (⚠️)

- **HighSchedulerErrorRate** - >10 помилок за 5 хв
- **CacheUnhealthy** - Redis недоступний
- **LowCacheHitRate** - <30% hit rate протягом 30 хв
- **SlowAPIResponse** - >10 секунд виконання
- **DatabaseSyncFailed** - синхронізація не працює 2 години

### Info Alerts (ℹ️)

- **HighAPICallRate** - >100 викликів за хвилину

## Dashboard Panels

### Panel 1: Service Health Status

Показує стан усіх компонентів:

- Database: ✅/❌
- Cache: ✅/❌
- Binance API: ✅/❌
- Bybit API: ✅/❌

### Panel 2: Cache Hit Rate

Графік ефективності кешування (0-100%)

### Panel 3: Scheduler Jobs Status

- Виконано задач
- Провалено задач
- Success rate

### Panel 4: API Response Times

Графік швидкості відповіді API бірж

### Panel 5: Database Sync Statistics

Графік синхронізацій per minute

### Panel 6: Total Products

Кількість продуктів в БД (з кольоровими thresholds)

### Panel 7: Cache Memory Usage

Використання пам'яті Redis

### Panel 8: Average Execution Time

Середній час виконання задач

### Panel 9: API Calls Rate

Кількість API викликів per minute

### Panel 10: Recent Errors

Останні помилки та alerts з логів

## Тестування

### Перевірка метрик

```bash
# Prometheus метрики
curl http://localhost:8000/api/v1/scheduler/metrics | python3 -m json.tool

# Cache статистика
curl http://localhost:8000/api/v1/cache/stats | python3 -m json.tool

# Health check
curl http://localhost:8000/api/v1/health | python3 -m json.tool
```

### Перевірка Prometheus

```bash
# Відкрити UI
open http://localhost:9090

# Перевірити targets
open http://localhost:9090/targets

# Query приклад
jobs_executed_total
```

### Перевірка Grafana

```bash
# Відкрити UI
open http://localhost:3000

# Dashboard
open http://localhost:3000/d/earnaggregator
```

## Troubleshooting

### Prometheus не бачить метрики

**Проблема:** No data in Prometheus

**Рішення:**

```bash
# Перевірити чи Prometheus може досягти API
curl http://yield-api:8000/api/v1/scheduler/metrics

# Перевірити Prometheus targets
curl http://localhost:9090/api/v1/targets

# Перевірити logs
docker logs prometheus
```

### Alerts не спрацьовують

**Проблема:** Немає notifications

**Рішення:**

1. Перевірити `alert_rules.yml` синтаксис
2. Налаштувати Alertmanager
3. Додати receivers (email, Slack, etc.)

### Dashboard порожній

**Проблема:** No data in Grafana

**Рішення:**

1. Перевірити Prometheus data source
2. Перевірити що metrics збираються
3. Refresh dashboard

## Production Deployment

### Docker Compose Integration

Додати до `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: earn-prometheus
    volumes:
      - ./yield-data-service/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./yield-data-service/monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - backend_net
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: earn-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - backend_net
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

### Запуск

```bash
docker-compose up -d prometheus grafana
```

---

## Підсумок

✅ Prometheus конфігурація готова
✅ Alert rules налаштовані
✅ Grafana dashboard створено
✅ Всі метрики доступні через API
✅ Документація повна

**Система моніторингу готова до використання!** 📊
