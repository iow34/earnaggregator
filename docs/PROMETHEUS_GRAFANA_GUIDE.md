# Prometheus та Grafana - Повний гайд користування

## РОЗДІЛ 3.3: Dashboard моніторингу даних EarnAggregator

---

## Огляд

Цей гайд допоможе налаштувати та використовувати Prometheus та Grafana для моніторингу EarnAggregator Data Service.

### Що таке Prometheus?

**Prometheus** - система моніторингу та збору метрик з time-series базою даних.

**Використовується для:**

- Збір метрик з додатків
- Зберігання історичних даних
- Запити до метрик (PromQL)
- Alerting при проблемах

### Що таке Grafana?

**Grafana** - платформа для візуалізації даних та створення dashboards.

**Використовується для:**

- Створення красивих дашбордів
- Візуалізація метрик з Prometheus
- Налаштування alerts
- Real-time моніторинг

---

## Швидкий старт

### 1. Запуск Prometheus та Grafana

```bash
# З кореневої директорії проекту
cd /Users/user777/Documents/EarnAggregator

# Запустити Prometheus
docker-compose up -d prometheus

# Запустити Grafana (автоматично чекає на Prometheus)
docker-compose up -d grafana

# Перевірити статус
docker ps | grep -E "prometheus|grafana"
```

**Очікуваний результат:**

```
earn-prometheus   Up (healthy)    0.0.0.0:9090->9090/tcp
earn-grafana      Up              0.0.0.0:3000->3000/tcp
```

### 2. Відкрити інтерфейси

**Prometheus UI:**

```bash
open http://localhost:9090
# або
curl http://localhost:9090
```

**Grafana UI:**

```bash
open http://localhost:3000
# або
curl http://localhost:3000
```

---

## Prometheus - Детальна інструкція

### Доступ до Prometheus

**URL:** http://localhost:9090

**Немає авторизації** - відкритий доступ (для production налаштувати authentication)

### Основні розділи Prometheus UI

#### 1. Graph (Головна сторінка)

**URL:** http://localhost:9090/graph

**Що можна робити:**

- Виконувати PromQL запити
- Переглядати метрики в режимі Graph або Table
- Вибирати часовий діапазон

**Приклади запитів:**

```promql
# Всі метрики
{job="earnaggregator-api"}

# Перевірка доступності
up{job="earnaggregator-api"}

# Cache hit rate (коли буде exporter)
cache_hit_rate_percent
```

#### 2. Alerts

**URL:** http://localhost:9090/alerts

**Що показує:**

- Всі налаштовані alerts
- Поточний стан (Inactive/Pending/Firing)
- Коли alert останній раз спрацював

#### 3. Status → Targets

**URL:** http://localhost:9090/targets

**Що показує:**

- Всі endpoints які Prometheus scrape
- Статус кожного target (UP/DOWN)
- Останній час scrape
- Помилки scraping

**Перевірка:**

```bash
curl http://localhost:9090/api/v1/targets | python3 -m json.tool
```

#### 4. Status → Configuration

**URL:** http://localhost:9090/config

**Що показує:**

- Поточна конфігурація Prometheus
- Всі scrape jobs
- Alert rules

#### 5. Status → Rules

**URL:** http://localhost:9090/rules

**Що показує:**

- Всі alert rules
- Recording rules
- Стан правил

### Корисні PromQL запити

```promql
# 1. Перевірка доступності сервісу
up{job="earnaggregator-api"}

# 2. Кількість targets
count(up{job=~"earnaggregator.*"})

# 3. Час scraping
scrape_duration_seconds{job="earnaggregator-api"}

# 4. Розмір відповіді
scrape_samples_scraped{job="earnaggregator-api"}
```

### Troubleshooting Prometheus

#### Проблема: Target DOWN

**Симптоми:** Targets показують DOWN статус

**Рішення:**

```bash
# 1. Перевірити чи API доступний
curl http://localhost:8000/api/v1/scheduler/metrics

# 2. Перевірити з контейнера Prometheus
docker exec earn-prometheus wget -O- http://yield-api:8000/api/v1/health

# 3. Перевірити мережу
docker network inspect earn_backend | grep -A 5 "earn-prometheus\|earn-yield-api"
```

#### Проблема: No data

**Симптоми:** Запити не повертають даних

**Причина:** Наші endpoints повертають JSON, а не Prometheus format

**Рішення:** Для повноцінних метрик потрібно:

1. Додати Prometheus exporter
2. Або змінити endpoints на Prometheus format
3. Або використовувати JSON exporter

---

## Grafana - Детальна інструкція

### Доступ до Grafana

**URL:** http://localhost:3000

**Логін:**

- Username: `admin`
- Password: `admin` (при першому вході запропонує змінити)

### Перше налаштування Grafana

#### Крок 1: Login

1. Відкрити http://localhost:3000
2. Ввести `admin` / `admin`
3. (Опціонально) Змінити пароль або Skip

#### Крок 2: Додати Prometheus Data Source

**Шлях:** Configuration → Data Sources → Add data source

**Налаштування:**

```
Name:               Prometheus
Type:               Prometheus
URL:                http://prometheus:9090  # Важливо: ім'я Docker сервісу
Access:             Server (default)
Scrape interval:    30s
```

**Збережіть:** Save & test

**Очікуваний результат:** ✅ "Data source is working"

#### Крок 3: Створити Dashboard

**Варіант A: Імпортувати готовий dashboard**

1. Dashboards → Import
2. Upload JSON file
3. Вибрати: `yield-data-service/monitoring/grafana_dashboard.json`
4. Select Prometheus data source
5. Import

**Варіант B: Створити вручну**

1. Dashboards → New Dashboard
2. Add visualization
3. Select Prometheus data source
4. Написати PromQL query
5. Налаштувати візуалізацію
6. Save dashboard

### Створення панелей Grafana

#### Panel 1: Service Health (Stat)

**Query:**

```promql
up{job="earnaggregator-api"}
```

**Візуалізація:**

- Type: Stat
- Value mappings:
  - 1 → "✅ Healthy"
  - 0 → "❌ Down"
- Thresholds:
  - Red: 0
  - Green: 1

#### Panel 2: API Response Time (Graph)

**Примітка:** Поки що показуватиме scrape duration

**Query:**

```promql
scrape_duration_seconds{job="earnaggregator-api"} * 1000
```

**Візуалізація:**

- Type: Time series
- Unit: ms (milliseconds)
- Legend: API Response Time

#### Panel 3: Uptime (Stat)

**Query:**

```promql
count(up{job=~"earnaggregator.*"} == 1)
```

**Візуалізація:**

- Type: Stat
- Title: "Active Services"
- Color: Green

### Корисні функції Grafana

#### Variables (змінні)

Створити змінну для динамічної зміни job:

**Settings → Variables → New variable**

```
Name:   job
Type:   Query
Query:  label_values(up, job)
```

Використання в панелях:

```promql
up{job="$job"}
```

#### Annotations (анотації)

Показувати події на графіках:

**Dashboard settings → Annotations**

```
Name:       Alerts
Data source: Prometheus
Query:      ALERTS{job="earnaggregator-api"}
```

#### Alerts в Grafana

Налаштувати alerts безпосередньо в Grafana:

1. Edit panel
2. Alert tab
3. Create alert rule
4. Налаштувати умови
5. Додати notification channels

---

## Моніторинг EarnAggregator через Prometheus

### Поточні targets

```bash
# Перевірити targets через API
curl http://localhost:9090/api/v1/targets | python3 -m json.tool
```

**Налаштовані jobs:**

1. **earnaggregator-api** - scheduler metrics (кожні 30с)
2. **earnaggregator-cache** - cache stats (кожні 15с)
3. **earnaggregator-aggregation** - aggregation stats (кожну хв)
4. **earnaggregator-health** - health check (кожні 30с)

### Доступні metrics endpoints

```bash
# 1. Scheduler metrics
curl http://localhost:8000/api/v1/scheduler/metrics | python3 -m json.tool

# 2. Cache stats
curl http://localhost:8000/api/v1/cache/stats | python3 -m json.tool

# 3. Aggregation stats
curl http://localhost:8000/api/v1/aggregation/stats | python3 -m json.tool

# 4. Health check
curl http://localhost:8000/api/v1/health | python3 -m json.tool
```

### Перевірка збору метрик

**Через Prometheus UI:**

1. Відкрити http://localhost:9090/targets
2. Перевірити що всі targets "UP"
3. Перевірити "Last Scrape" - має бути недавно

**Через API:**

```bash
# Перевірити всі targets
curl -s http://localhost:9090/api/v1/targets | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  [print(f\"{t['scrapePool']}: {t['health']}\") for t in data['data']['activeTargets']]"
```

---

## Dashboard моніторингу даних

### Рекомендована структура Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  EarnAggregator - Data Service Monitoring                   │
├─────────────────────────────────────────────────────────────┤
│  Row 1: Service Status                                      │
│  ┌──────────┬──────────┬──────────┬──────────┐            │
│  │ Database │  Cache   │ Binance  │  Bybit   │            │
│  │  ✅ UP   │  ✅ UP   │  ✅ UP   │  ✅ UP   │            │
│  └──────────┴──────────┴──────────┴──────────┘            │
├─────────────────────────────────────────────────────────────┤
│  Row 2: Database & Cache                                    │
│  ┌──────────────────────┬──────────────────────┐           │
│  │  Total Products      │  Cache Hit Rate      │           │
│  │      353             │      78.5%           │           │
│  │  ────────────────    │  ════════════════    │           │
│  │  Graph over time     │  Graph trend         │           │
│  └──────────────────────┴──────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  Row 3: Scheduler Performance                               │
│  ┌────────────────────────────────────────────┐            │
│  │  Jobs Executed / Failed                    │            │
│  │  245 / 0  (100% success rate)              │            │
│  │  ────────────────────────────────────      │            │
│  │  [Graph showing jobs over time]            │            │
│  └────────────────────────────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  Row 4: API Performance                                     │
│  ┌──────────────────────┬──────────────────────┐           │
│  │  Binance Response    │  Bybit Response      │           │
│  │      563ms           │      1173ms          │           │
│  │  Graph ──────        │  Graph ──────        │           │
│  └──────────────────────┴──────────────────────┘           │
├─────────────────────────────────────────────────────────────┤
│  Row 5: Recent Activity                                     │
│  ┌────────────────────────────────────────────┐            │
│  │  Logs & Errors                             │            │
│  │  [2025-10-21 16:47] ✅ Health check OK     │            │
│  │  [2025-10-21 16:45] 🔄 Cache updated       │            │
│  └────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Як створити кожну панель

#### Панель: Service Status (Stat)

**Додати панель:**

1. Dashboard → Add → Visualization
2. Select Prometheus data source
3. Query: `up{job="earnaggregator-api"}`
4. Visualization: Stat
5. Value mappings:
   - `1` → `✅ Healthy`
   - `0` → `❌ Down`
6. Title: "Service Status"
7. Apply

#### Панель: Total Products (Stat + Graph)

**Примітка:** Поки що через JSON API

**Створити змінну:**

```bash
# Endpoint для отримання кількості
curl http://localhost:8000/api/v1/stats | jq .total_products
```

**В Grafana:**

- Використати **JSON API datasource plugin**
- Або **Infinity datasource** для JSON endpoints

**Query приклад (з Infinity plugin):**

```
URL:    http://yield-api:8000/api/v1/stats
Parser: JSON
Path:   $.total_products
```

#### Панель: Cache Hit Rate (Gauge)

**З JSON API datasource:**

```
URL:    http://yield-api:8000/api/v1/cache/stats
Parser: JSON
Path:   $.data.hit_rate_percent
```

**Візуалізація:**

- Type: Gauge
- Min: 0
- Max: 100
- Unit: percent (0-100)
- Thresholds:
  - Red: 0-30
  - Yellow: 30-60
  - Green: 60-100

---

## Використання без Prometheus Exporter

### Проблема

Наші endpoints повертають JSON, а Prometheus очікує metrics в спеціальному форматі.

### Рішення 1: JSON API Datasource (найпростіше)

**Установка:**

1. В Grafana: Configuration → Plugins
2. Шукати "JSON API" або "Infinity"
3. Install plugin
4. Restart Grafana

**Додати datasource:**

```
Name: EarnAggregator JSON API
Type: JSON API
URL:  http://yield-api:8000
```

**Створити панель:**

```
Query:    /api/v1/scheduler/metrics
JSONPath: $.data.scheduler.jobs_executed_total
```

### Рішення 2: Prometheus Exporter (складніше, але краще)

**Створити `/metrics` endpoint:**

```python
# В app/main.py або окремому файлі
from prometheus_client import Counter, Gauge, generate_latest

# Metrics
jobs_executed = Counter('jobs_executed_total', 'Total jobs executed')
cache_hit_rate = Gauge('cache_hit_rate_percent', 'Cache hit rate')

@app.get("/metrics")
async def prometheus_metrics():
    # Оновити metrics
    jobs_executed.inc(data_scheduler.metrics.jobs_executed)
    cache_hit_rate.set(await cache_manager.get_hit_rate())

    # Повернути в Prometheus format
    return Response(generate_latest(), media_type="text/plain")
```

### Рішення 3: Використання логів (базове)

Grafana може візуалізувати логи:

```bash
# Налаштувати Loki для логів
docker run -d --name=loki --network=earn_backend \
  -p 3100:3100 grafana/loki:latest

# Додати Loki datasource в Grafana
```

---

## Створення Dashboard - Покроковий гайд

### Створення нового Dashboard

#### Крок 1: Створити Dashboard

1. Відкрити Grafana (http://localhost:3000)
2. Клік на "+" → "Dashboard"
3. Клік "Add visualization"

#### Крок 2: Вибрати Data Source

- Select: "Prometheus" (або "JSON API" якщо встановлено)

#### Крок 3: Написати Query

**Для Prometheus:**

```promql
up{job="earnaggregator-api"}
```

**Для JSON API:**

```
Endpoint: /api/v1/scheduler/status
JSONPath: $.data.running
```

#### Крок 4: Налаштувати Visualization

**Опції:**

- **Time series** - графік з часом
- **Stat** - одне значення
- **Gauge** - шкала 0-100
- **Table** - таблиця даних
- **Logs** - перегляд логів

#### Крок 5: Налаштувати Display

**Для Stat:**

- Title: "Scheduler Status"
- Value mappings:
  - `true` → "✅ Running"
  - `false` → "❌ Stopped"
- Color scheme: Green/Red

#### Крок 6: Зберегти

1. Apply (застосувати зміни панелі)
2. Save dashboard (вгорі)
3. Назва: "EarnAggregator Monitoring"
4. Folder: General
5. Save

### Організація Dashboard

#### Rows (рядки) для групування

**Створити Row:**

1. Add → Row
2. Назва: "Service Status"
3. Перетягти панелі в row

**Рекомендована структура:**

```
Row 1: Service Health
  - Database Status
  - Cache Status
  - Binance API Status
  - Bybit API Status

Row 2: Data Metrics
  - Total Products
  - Active Products
  - Sync Statistics

Row 3: Cache Performance
  - Hit Rate
  - Memory Usage
  - Requests/sec

Row 4: Scheduler
  - Jobs Executed
  - Jobs Failed
  - Average Execution Time

Row 5: Logs & Errors
  - Recent Errors
  - Alerts
```

### Variables для Dashboard

**Створити змінну для динамічного фільтрування:**

**Settings → Variables → New variable**

**Variable 1: Time Range**

```
Name:     time_range
Type:     Interval
Values:   1m,5m,10m,30m,1h,6h,12h,1d
```

**Variable 2: Job**

```
Name:     job
Type:     Custom
Values:   earnaggregator-api,earnaggregator-cache
```

**Використання:**

```promql
up{job="$job"}
```

---

## Приклади Dashboard панелей

### 1. Cache Hit Rate (JSON API)

**Data Source:** JSON API

**Settings:**

```
URL:      /api/v1/cache/stats
Method:   GET
JSONPath: $.data.hit_rate_percent
```

**Visualization:**

```
Type:        Gauge
Min:         0
Max:         100
Unit:        percent (0-100)
Title:       Cache Hit Rate
Thresholds:
  - 0-30:    Red
  - 30-70:   Yellow
  - 70-100:  Green
```

### 2. Total Products (JSON API)

**Settings:**

```
URL:      /api/v1/stats
JSONPath: $.total_products
```

**Visualization:**

```
Type:   Stat
Title:  Total Products in Database
Color:  Green
Unit:   short
```

### 3. Scheduler Jobs (JSON API)

**Settings:**

```
URL:      /api/v1/scheduler/metrics
JSONPath: $.data.scheduler.jobs_executed_total
```

**Visualization:**

```
Type:   Graph (Time series)
Title:  Jobs Executed
Unit:   short
Legend: Jobs
```

### 4. API Health Status (JSON API)

**Settings:**

```
URL:      /api/v1/health
JSONPath: $.api_status
```

**Transform:** JSONPath для кожного API

- Binance: `$.api_status.binance`
- Bybit: `$.api_status.bybit`

**Visualization:**

```
Type:           Stat
Value mappings:
  - "success" → "✅ Online"
  - "error"   → "❌ Offline"
```

---

## Alerting в Grafana

### Створення Alert Rule

#### Крок 1: Edit Panel → Alert tab

#### Крок 2: Create alert rule

**Alert Conditions:**

```
WHEN: avg() OF query(A, 5m, now)
IS ABOVE: threshold_value
```

**Приклад для Cache Hit Rate:**

```
WHEN: avg() OF cache_hit_rate
IS BELOW: 30
FOR: 30m
```

#### Крок 3: Налаштувати Notifications

**Contact Points:**

1. Alerting → Contact points
2. New contact point
3. Type: Email / Slack / Webhook
4. Налаштувати credentials

**Приклад для Slack:**

```
Name:        Slack Alerts
Type:        Slack
Webhook URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
Channel:     #alerts
```

#### Крок 4: Notification Policy

**Alerting → Notification policies**

- Default policy → Edit
- Додати matcher:
  - Label: `severity`
  - Value: `critical`
- Route to: Slack Alerts

---

## Практичні приклади використання

### Сценарій 1: Щоденний моніторинг

**Що перевіряти:**

1. Відкрити Grafana dashboard
2. Перевірити Service Health - всі ✅
3. Перевірити Cache Hit Rate - має рости
4. Переглянути Recent Errors - має бути порожньо

### Сценарій 2: Дослідження проблеми

**Якщо щось не працює:**

**Крок 1: Health Check**

```bash
curl http://localhost:8000/api/v1/health | python3 -m json.tool
```

**Крок 2: Scheduler Status**

```bash
curl http://localhost:8000/api/v1/scheduler/status | python3 -m json.tool
```

**Крок 3: Prometheus Targets**

```bash
open http://localhost:9090/targets
# Перевірити чи всі UP
```

**Крок 4: Grafana Dashboard**

```bash
open http://localhost:3000
# Подивитись панелі на проблеми
```

**Крок 5: Логи**

```bash
docker logs -f earn-yield-api | grep "ERROR\|ALERT"
```

### Сценарій 3: Performance Tuning

**Метрики для аналізу:**

1. **Cache Hit Rate**

   - Мета: >70%
   - Якщо низький: збільшити TTL або warmup

2. **API Response Time**

   - Binance: <1000ms
   - Bybit: <2000ms
   - Якщо повільно: перевірити мережу

3. **Scheduler Jobs**
   - Success rate: 100%
   - Avg time: <30000ms
   - Якщо повільно: оптимізувати запити

---

## Grafana Dashboards Library

### Офіційні dashboards для Docker

**Імпорт готових dashboards:**

1. Dashboards → Import
2. Import via grafana.com
3. ID: **893** (Docker monitoring)
4. ID: **1860** (Node Exporter)

### Кастомні панелі для EarnAggregator

**Panel 1: Service Uptime**

```
Title:       Service Uptime
Type:        Stat
Data source: Prometheus
Query:       time() - process_start_time_seconds
Unit:        duration (s)
```

**Panel 2: Request Rate**

```
Title:       API Requests/sec
Type:        Graph
Query:       rate(http_requests_total[5m])
Unit:        reqps (requests per second)
```

---

## Корисні команди

### Prometheus

```bash
# Перевірити конфігурацію
docker exec earn-prometheus promtool check config /etc/prometheus/prometheus.yml

# Перевірити rules
docker exec earn-prometheus promtool check rules /etc/prometheus/alert_rules.yml

# Reload конфігурації без перезапуску
curl -X POST http://localhost:9090/-/reload

# Перевірити targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Перевірити alerts
curl http://localhost:9090/api/v1/alerts | python3 -m json.tool
```

### Grafana

```bash
# Перевірити стан
curl http://localhost:3000/api/health

# Список dashboards (потрібен API key)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:3000/api/dashboards

# Backup dashboard
curl http://localhost:3000/api/dashboards/uid/DASHBOARD_UID | \
  python3 -m json.tool > backup.json
```

---

## Troubleshooting

### Prometheus не збирає метрики

**Проблема:** Targets показують DOWN

**Рішення:**

```bash
# 1. Перевірити що API працює
curl http://localhost:8000/api/v1/health

# 2. Перевірити з Prometheus контейнера
docker exec earn-prometheus wget -O- http://yield-api:8000/api/v1/health

# 3. Перевірити мережу
docker network inspect earn_backend

# 4. Перевірити логи Prometheus
docker logs earn-prometheus --tail 20
```

### Grafana не може підключитися до Prometheus

**Проблема:** Data source test fails

**Рішення:**

```bash
# 1. Перевірити що Prometheus працює
curl http://localhost:9090/-/healthy

# 2. Використати Docker service name
URL: http://prometheus:9090  # НЕ localhost!

# 3. Перевірити що в тій самій мережі
docker network inspect earn_backend | grep -E "grafana|prometheus"

# 4. Тест з Grafana контейнера
docker exec earn-grafana wget -O- http://prometheus:9090/api/v1/status/config
```

### Dashboard порожній

**Проблема:** No data in Grafana panels

**Причина:** Наші endpoints повертають JSON, а не Prometheus metrics

**Рішення:**

1. Встановити JSON API datasource plugin
2. Створити панелі з JSON queries
3. Або додати `/metrics` endpoint в Prometheus форматі

---

## Production Deployment

### Безпека

**Prometheus:**

```yaml
# В docker-compose.yml додати basic auth
command:
  - "--web.external-url=https://prometheus.yourdomain.com"
  - "--web.enable-admin-api"
```

**Grafana:**

```yaml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${STRONG_PASSWORD}
  - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
  - GF_AUTH_DISABLE_LOGIN_FORM=false
```

### Persistent Storage

**Вже налаштовано в docker-compose.yml:**

```yaml
volumes:
  prometheus_data: # Зберігає метрики Prometheus
  grafana_data: # Зберігає dashboards та settings
```

### Backup

```bash
# Backup Prometheus data
docker run --rm -v earn_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus_backup.tar.gz /data

# Backup Grafana data
docker run --rm -v earn_grafana_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana_backup.tar.gz /data
```

---

## Підсумок

### ✅ Що працює зараз:

- ✅ Prometheus запущено та healthy
- ✅ Grafana запущено
- ✅ 4 scrape jobs налаштовані
- ✅ Health checks працюють
- ✅ Alert rules базові

### ⚠️ Що потрібно для повноцінного моніторингу:

- ⚠️ JSON API datasource plugin для Grafana
- ⚠️ Або `/metrics` endpoint в Prometheus форматі
- ⚠️ Налаштування notification channels

### 🚀 Як використовувати:

1. Відкрити http://localhost:9090 - переглянути targets
2. Відкрити http://localhost:3000 - створити dashboards
3. Встановити JSON plugin для візуалізації наших метрик
4. Використовувати наші API endpoints для даних

---

**Система моніторингу налаштована та готова до використання!** 📊
