# Scheduler - РОЗДІЛ 3.3: Автоматичне оновлення даних

## Огляд

Scheduler (`DataScheduler`) забезпечує автоматичне оновлення даних з API бірж та підтримання кешу в актуальному стані.

## Основні задачі

### 1. Оновлення кешу (кожну годину)

**Функція:** `update_cache_job()`

**Що робить:**

- Очищує кеш для популярних монет (BTC, ETH, USDT, USDC, BNB, SOL, ADA, DOT, MATIC, AVAX)
- Очищує топ кеш (`top:*`)
- Очищує кеш бірж (`exchange:*`)

**Розклад:** Кожну годину (interval: 1 hour)

**Логування:**

```
🔄 Початок оновлення кешу...
🗑️ Очищено кеш для BTC
🗑️ Очищено топ кеш
🗑️ Очищено кеш бірж
✅ Оновлення кешу завершено за 125.45мс
```

### 2. Оновлення БД (кожну годину)

**Функція:** `update_database_job()`

**Що робить:**

- Синхронізує продукти з Binance API
- Синхронізує продукти з Bybit API
- Оновлює існуючі продукти
- Створює нові продукти

**Розклад:** Кожну годину (interval: 1 hour)

**Логування:**

```
🔄 Початок синхронізації БД з API бірж...
📥 Синхронізація Binance...
✅ Binance: 10 створено, 90 оновлено, 0 помилок
📥 Синхронізація Bybit...
✅ Bybit: 5 створено, 248 оновлено, 0 помилок
✅ Синхронізація БД завершена: 15 створено, 338 оновлено, 0 помилок
```

### 3. Health Check (кожні 15 хвилин)

**Функція:** `health_check_job()`

**Що робить:**

- Перевіряє доступність Binance API
- Перевіряє доступність Bybit API
- Логує response time для кожного API
- **Alerting при падінні API** - логує помилки з префіксом 🚨

**Розклад:** Кожні 15 хвилин

**Логування:**

```
🏥 Перевірка здоров'я API бірж...
✅ Binance API: 563.9ms
✅ Bybit API: 1173.3ms
```

**Alerting:**

```
🚨 ALERT: Binance API недоступний! Connection timeout
🚨 ALERT: Bybit API недоступний! Rate limit exceeded
```

### 4. Прогрів кешу (кожні 30 хвилин)

**Функція:** `update_popular_symbols_job()`

**Що робить:**

- Отримує дані для 10 популярних монет
- Кешує результати для швидкого доступу
- Зменшує навантаження при peak traffic

**Розклад:** Кожні 30 хвилин

**Популярні монети:**
`BTC, ETH, USDT, USDC, BNB, SOL, ADA, DOT, MATIC, AVAX`

---

## Обробка помилок

### Graceful Degradation

**Правило:** Scheduler НЕ зупиняється при помилках

**Поведінка:**

```python
try:
    # Виконання задачі
    await sync_binance()
except Exception as e:
    # Логуємо помилку
    logger.error(f"❌ Помилка: {e}")
    # НЕ зупиняємо scheduler - продовжуємо роботу
    # Наступна спроба через інтервал
```

**Приклади обробки:**

- **Помилка Binance API** → продовжуємо з Bybit
- **Помилка синхронізації** → логуємо та чекаємо наступного циклу
- **Помилка кешу** → використовуємо fallback
- **Критична помилка** → логуємо, записуємо в метрики, продовжуємо

---

## Моніторинг задач

### Метрики (Prometheus compatible)

**SchedulerMetrics:**

```python
{
  "jobs_executed_total": 245,      # Всього виконано задач
  "jobs_failed_total": 3,          # Провалених задач
  "cache_updates_total": 120,      # Оновлень кешу
  "db_syncs_total": 100,           # Синхронізацій БД
  "api_calls_total": 200,          # API викликів
  "average_execution_time_ms": 1523.45,  # Середній час
  "last_execution": "2025-10-21T16:32:32Z",
  "last_error": null,              # Остання помилка
  "uptime_jobs": 245               # Історія виконань
}
```

### Cache Hit Rate (Prometheus)

```python
{
  "cache": {
    "hits": 1250,
    "misses": 350,
    "total_requests": 1600,
    "hit_rate_percent": 78.13,      # Ефективність кешу
    "redis_connected": true,
    "redis_memory_used": "2.45M"
  }
}
```

---

## API Endpoints для моніторингу

### GET `/api/v1/scheduler/status`

Отримати статус scheduler та його задач.

**Приклад:**

```bash
curl http://localhost:8000/api/v1/scheduler/status
```

**Відповідь:**

```json
{
  "success": true,
  "data": {
    "status": "running",
    "running": true,
    "jobs_count": 4,
    "jobs": [
      {
        "id": "update_cache",
        "name": "Оновлення кешу",
        "next_run": "2025-10-21T17:32:05Z",
        "trigger": "interval[1:00:00]"
      }
    ]
  }
}
```

### GET `/api/v1/scheduler/metrics`

Prometheus метрики для моніторингу.

**Приклад:**

```bash
curl http://localhost:8000/api/v1/scheduler/metrics
```

**Відповідь:** Метрики scheduler + cache stats

### POST `/api/v1/scheduler/trigger/cache`

Ручне оновлення кешу.

**Приклад:**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/cache
```

### POST `/api/v1/scheduler/trigger/sync`

Ручна синхронізація БД.

**Приклад:**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/sync
```

### POST `/api/v1/scheduler/trigger/healthcheck`

Ручна перевірка здоров'я API.

**Приклад:**

```bash
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/healthcheck
```

---

## Використання в коді

### Інтеграція в main.py

```python
from app.services.scheduler import start_scheduler_async, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await start_scheduler_async()

    yield

    # Shutdown
    stop_scheduler()
```

### Ручний виклик задач (для тестування)

```python
from app.services.scheduler import (
    trigger_cache_update,
    trigger_db_sync,
    trigger_health_check
)

# Оновити кеш
await trigger_cache_update()

# Синхронізувати БД
await trigger_db_sync()

# Перевірити здоров'я
await trigger_health_check()
```

---

## Налаштування

### Популярні монети

Змінити список в `DataScheduler.__init__()`:

```python
self.priority_symbols = ["BTC", "ETH", "USDT", "USDC", "BNB"]
```

### Інтервали виконання

Змінити в `start()`:

```python
# Оновлення кешу кожні 30 хвилин
self.scheduler.add_job(
    self.update_cache_job,
    trigger=IntervalTrigger(minutes=30),  # Було: hours=1
    ...
)
```

---

## Alerting при падінні API

### Логування

Scheduler автоматично логує критичні помилки з префіксом 🚨:

```
🚨 ALERT: Binance API недоступний! Connection timeout
🚨 ALERT: Bybit API недоступний! Rate limit exceeded
```

### Інтеграція з моніторингом

Для production рекомендується:

1. **Логування → файл** → аналіз через ELK/Grafana
2. **Метрики → Prometheus** → Grafana dashboards
3. **Alerts → PagerDuty/Slack** при критичних помилках

---

## Dashboard для візуалізації

### Prometheus Metrics Endpoints

**Scheduler metrics:**

```
GET /api/v1/scheduler/metrics
```

**Cache metrics:**

```
GET /api/v1/cache/stats
```

**Aggregation metrics:**

```
GET /api/v1/aggregation/stats
```

### Grafana Dashboard (рекомендовано)

**Панелі:**

1. **Cache Hit Rate** - ефективність кешування
2. **Jobs Executed** - кількість виконаних задач
3. **API Response Times** - швидкість API бірж
4. **Error Rate** - кількість помилок
5. **Database Sync Stats** - створені/оновлені продукти

**Query приклади:**

```promql
# Cache hit rate
(scheduler_metrics_cache_hits_total / scheduler_metrics_cache_requests_total) * 100

# Jobs success rate
(scheduler_metrics_jobs_executed_total /
 (scheduler_metrics_jobs_executed_total + scheduler_metrics_jobs_failed_total)) * 100

# Average execution time
scheduler_metrics_average_execution_time_ms
```

---

## Lifecycle Events

### Startup

```
🚀 Запуск scheduler...
✅ Додано задачу: Оновлення кешу (кожну годину)
✅ Додано задачу: Синхронізація БД (кожну годину)
✅ Додано задачу: Health Check (кожні 15 хв)
✅ Додано задачу: Прогрів кешу (кожні 30 хв)
✅ Scheduler запущено успішно
🔄 Запуск першого оновлення...
🏥 Перевірка здоров'я API бірж...
🔥 Прогрів кешу для популярних монет...
✅ Початкове оновлення завершено
```

### Running

```
# Кожні 15 хвилин
🏥 Перевірка здоров'я API бірж...
✅ Binance API: 563.9ms
✅ Bybit API: 1173.3ms

# Кожні 30 хвилин
🔥 Прогрів кешу...
✅ BTC: 5 продуктів закешовано
✅ ETH: 3 продукти закешовано

# Кожну годину
🔄 Оновлення кешу...
🗑️ Очищено кеш для популярних монет
✅ Оновлення завершено

🔄 Синхронізація БД...
✅ Binance: 2 створено, 98 оновлено
✅ Bybit: 5 створено, 248 оновлено
```

### Shutdown

```
🛑 Зупинка scheduler...
✅ Scheduler зупинено
```

---

## Troubleshooting

### Scheduler не запускається

**Симптоми:** Логи не показують "Scheduler запущено"

**Рішення:**

```bash
# Перевірити логи
docker logs earn-yield-api | grep scheduler

# Перевірити статус через API
curl http://localhost:8000/api/v1/scheduler/status
```

### Задачі не виконуються

**Симптоми:** `jobs_executed_total` не зростає

**Рішення:**

```bash
# Перевірити що scheduler running
curl http://localhost:8000/api/v1/scheduler/status | grep running

# Подивитись наступне виконання
curl http://localhost:8000/api/v1/scheduler/status | grep next_run

# Запустити вручну для тестування
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/sync
```

### API бірж недоступні

**Симптоми:** Логи містять 🚨 ALERT

**Рішення:**

```bash
# Перевірити API ключі
docker exec earn-yield-api cat /app/.env | grep API

# Тестувати підключення
curl http://localhost:8000/api/v1/binance/test
curl http://localhost:8000/api/v1/bybit/test
```

---

## Приклади використання

### Перевірка статусу

```bash
# Загальний статус
curl http://localhost:8000/api/v1/scheduler/status | python3 -m json.tool

# Метрики Prometheus
curl http://localhost:8000/api/v1/scheduler/metrics | python3 -m json.tool
```

### Ручне оновлення

```bash
# Оновити кеш зараз
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/cache

# Синхронізувати БД зараз
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/sync

# Перевірити здоров'я API
curl -X POST http://localhost:8000/api/v1/scheduler/trigger/healthcheck
```

### Моніторинг через watch

```bash
# Постійний моніторинг метрик
watch -n 5 'curl -s http://localhost:8000/api/v1/scheduler/metrics | python3 -m json.tool | head -30'

# Моніторинг логів
docker logs -f earn-yield-api | grep "scheduler\|ALERT\|✅"
```

---

## Інтеграція з Production

### 1. Prometheus Scraping

**Конфігурація `prometheus.yml`:**

```yaml
scrape_configs:
  - job_name: "earnaggregator"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/api/v1/scheduler/metrics"
    scrape_interval: 30s
```

### 2. Grafana Dashboards

**Імпорт метрик:**

- Додати Prometheus data source
- Створити dashboard з панелями
- Налаштувати alerts

**Приклад панелі:**

```json
{
  "title": "Cache Hit Rate",
  "targets": [
    {
      "expr": "cache_hit_rate_percent"
    }
  ]
}
```

### 3. Alerting Rules

**Prometheus alerts:**

```yaml
groups:
  - name: earnaggregator
    rules:
      - alert: HighErrorRate
        expr: jobs_failed_total > 10
        for: 5m
        annotations:
          summary: "Високий рівень помилок у scheduler"

      - alert: APIDown
        expr: api_status_binance != "success"
        for: 10m
        annotations:
          summary: "Binance API недоступний"
```

---

## Структура даних

### SchedulerMetrics (Prometheus format)

```python
{
  "jobs_executed_total": int,          # Counter
  "jobs_failed_total": int,            # Counter
  "cache_updates_total": int,          # Counter
  "db_syncs_total": int,               # Counter
  "api_calls_total": int,              # Counter
  "average_execution_time_ms": float,  # Gauge
  "last_execution": datetime,          # Timestamp
  "last_error": Optional[str],         # Info
  "uptime_jobs": int                   # Gauge
}
```

---

## Поточний статус

**Станом на 21.10.2025:**

```
✅ Scheduler: running
✅ Jobs count: 4
✅ Jobs executed: 2
✅ Jobs failed: 0
✅ Cache updates: 0 (будуть після першого циклу)
✅ DB syncs: 0 (будуть після першого циклу)
✅ Average time: 12683.82ms (початкове оновлення)
```

**Наступні виконання:**

- Health Check: кожні 15 хв
- Прогрів кешу: кожні 30 хв
- Оновлення кешу: кожну годину
- Синхронізація БД: кожну годину

**Система працює стабільно та автоматично оновлює дані!** 🚀
