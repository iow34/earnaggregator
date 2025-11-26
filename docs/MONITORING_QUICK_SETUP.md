# Швидке налаштування моніторингу - 5 хвилин

## РОЗДІЛ 3.3: Prometheus + Grafana за 5 хвилин

---

## Крок 1: Запуск (1 хвилина)

```bash
# З кореневої директорії
cd /Users/user777/Documents/EarnAggregator

# Запустити Prometheus та Grafana
docker-compose up -d prometheus grafana

# Перевірити що працюють
docker ps | grep -E "prometheus|grafana"
```

**Очікуваний результат:**

```
earn-prometheus   Up (healthy)
earn-grafana      Up
```

---

## Крок 2: Відкрити Grafana (30 секунд)

**URL:** http://localhost:3000

**Login:**

- Username: `admin`
- Password: `admin`

**При першому вході:**

- Натиснути "Skip" або встановити новий пароль

---

## Крок 3: Додати Prometheus Data Source (1 хвилина)

### Автоматично (рекомендовано):

1. Клік на ☰ (меню) → **Connections** → **Data sources**
2. Клік **Add data source**
3. Вибрати **Prometheus**
4. Налаштування:
   ```
   Name: Prometheus
   URL:  http://prometheus:9090
   ```
5. Клік **Save & test**

**Очікуваний результат:** ✅ "Successfully queried the Prometheus API"

---

## Крок 4: Створити перший Dashboard (2 хвилини)

### Опція A: Швидкий тест з Prometheus metrics

1. Клік на ☰ → **Dashboards** → **New dashboard**
2. **Add visualization**
3. Select: **Prometheus**
4. Query: `up{job="earnaggregator-api"}`
5. Клік **Run query**
6. Title: "Service Status"
7. **Apply**
8. **Save dashboard**

### Опція B: Моніторинг через JSON (потрібен plugin)

**Встановити JSON API datasource:**

1. ☰ → **Administration** → **Plugins**
2. Шукати: "JSON API"
3. **Install plugin** (може вимагати перезапуск)
4. Після встановлення:
   - Додати new data source
   - Type: JSON API
   - URL: `http://yield-api:8000`
   - Save & test

**Створити панель:**

1. New dashboard → Add visualization
2. Select: JSON API
3. Path: `/api/v1/stats`
4. JSONPath: `$.total_products`
5. Title: "Total Products"
6. Apply & Save

---

## Крок 5: Перевірка (30 секунд)

### Prometheus

**Відкрити:** http://localhost:9090

**Перевірити:**

1. Status → Targets - всі мають бути UP
2. Graph → Query: `up`
3. Має показати "1" для всіх сервісів

### Grafana

**Відкрити:** http://localhost:3000

**Перевірити:**

1. Dashboard має показувати дані
2. Панелі не порожні
3. No data source errors

---

## Швидкі команди для перевірки

```bash
# Перевірити що всі сервіси працюють
docker ps | grep -E "yield-api|prometheus|grafana"

# Перевірити Prometheus targets
curl -s http://localhost:9090/api/v1/targets | \
  python3 -c "import sys, json; \
  data=json.load(sys.stdin); \
  print('Targets:'); \
  [print(f\"  {t['scrapePool']}: {t['health']}\") \
   for t in data['data']['activeTargets']]"

# Перевірити Grafana
curl -s http://localhost:3000/api/health | python3 -m json.tool

# Перевірити наші metrics endpoints
curl -s http://localhost:8000/api/v1/scheduler/metrics | \
  python3 -m json.tool | head -20
```

---

## Готові метрики для dashboard

### З наших JSON endpoints:

**1. Scheduler Status**

```
Endpoint: /api/v1/scheduler/status
JSONPath: $.data.running
Display:  true → "✅ Running", false → "❌ Stopped"
```

**2. Total Products**

```
Endpoint: /api/v1/stats
JSONPath: $.total_products
Display:  Число
```

**3. Cache Hit Rate**

```
Endpoint: /api/v1/cache/stats
JSONPath: $.data.hit_rate_percent
Display:  % (0-100)
```

**4. Jobs Executed**

```
Endpoint: /api/v1/scheduler/metrics
JSONPath: $.data.scheduler.jobs_executed_total
Display:  Число
```

**5. Database Status**

```
Endpoint: /api/v1/health
JSONPath: $.database_status
Display:  "healthy" → "✅", "unhealthy" → "❌"
```

---

## Альтернатива: Простий Dashboard без Grafana

Якщо не хочете налаштовувати Grafana, використовуйте наш скрипт:

```bash
# Автоматична перевірка статусу
./check_system_status.sh

# Моніторинг scheduler
./test_scheduler.sh

# Watch в реальному часі
watch -n 5 './check_system_status.sh'
```

---

## Наступні кроки

### Після базового налаштування:

**1. Додати більше панелей:**

- API Response times
- Error logs
- Sync statistics

**2. Налаштувати alerts:**

- Email notifications
- Slack integration
- PagerDuty для critical alerts

**3. Оптимізувати:**

- Налаштувати retention policies
- Додати recording rules
- Створити custom metrics

---

## Підсумок

✅ **Prometheus:** http://localhost:9090 - збір метрик
✅ **Grafana:** http://localhost:3000 - візуалізація
✅ **API endpoints:** готові для моніторингу
✅ **Базові alerts:** налаштовані

**Час налаштування:** ~5 хвилин
**Складність:** Початківець

**Система моніторингу готова!** 🎯
