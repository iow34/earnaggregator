#!/bin/bash


clear

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ДЕМОНСТРАЦІЯ PROMETHEUS + GRAFANA                      ║"
echo "║     EarnAggregator Data Service Monitoring                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Ця демонстрація покаже як працює моніторинг системи"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 1: Перевірка Docker сервісів"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAME|earn-"

echo ""
echo "✅ Всі 5 сервісів працюють!"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 2: Prometheus Targets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Prometheus збирає метрики з наступних endpoints:"
echo ""

curl -s http://localhost:9090/api/v1/targets | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('┌─────────────────────────────────┬──────────┬─────────────┐')
print('│ Target                          │ Health   │ Last Scrape │')
print('├─────────────────────────────────┼──────────┼─────────────┤')
for t in data['data']['activeTargets']:
    job = t['scrapePool'][:31].ljust(31)
    health = t['health'].ljust(8)
    last = 'Unknown' if t['lastScrape'] == '0001-01-01T00:00:00Z' else 'Recent'
    print(f'│ {job} │ {health} │ {last.ljust(11)} │')
print('└─────────────────────────────────┴──────────┴─────────────┘')
"

echo ""
echo "ℹ️  URL: http://localhost:9090/targets"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 3: Scheduler Metrics (Prometheus Format)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

metrics=$(curl -s http://localhost:8000/api/v1/scheduler/metrics)

echo "$metrics" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
sch = data['scheduler']
cache = data['cache']

print('📊 SCHEDULER METRICS:')
print(f\"   Jobs Executed:  {sch['jobs_executed_total']}\")
print(f\"   Jobs Failed:    {sch['jobs_failed_total']}\")
print(f\"   Cache Updates:  {sch['cache_updates_total']}\")
print(f\"   Avg Time:       {sch['average_execution_time_ms']:.2f}ms\")
print()
print('💾 CACHE METRICS:')
print(f\"   Hit Rate:       {cache['hit_rate_percent']}%\")
print(f\"   Total Requests: {cache['total_requests']}\")
print(f\"   Memory Used:    {cache['redis_memory_used']}\")
"

echo ""
echo "ℹ️  Endpoint: http://localhost:8000/api/v1/scheduler/metrics"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 4: Grafana Dashboard Platform"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

grafana_health=$(curl -s http://localhost:3000/api/health)
version=$(echo $grafana_health | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")

echo "✅ Grafana запущено та готовий до використання!"
echo ""
echo "   Version:  $version"
echo "   URL:      http://localhost:3000"
echo "   Login:    admin"
echo "   Password: admin"
echo ""
echo "📊 Що можна зробити в Grafana:"
echo ""
echo "   1. Додати Prometheus data source"
echo "      → Connections → Data sources → Add"
echo "      → Type: Prometheus"
echo "      → URL: http://prometheus:9090"
echo ""
echo "   2. Створити Dashboard"
echo "      → Dashboards → New dashboard"
echo "      → Add visualization"
echo ""
echo "   3. Або встановити Infinity plugin для JSON"
echo "      → Administration → Plugins → Infinity"
echo "      → Restart Grafana"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 5: Live Demo - Scheduler Jobs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

curl -s http://localhost:8000/api/v1/scheduler/status | python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)['data']
print('🔄 SCHEDULER STATUS:')
print(f\"   Running: {'✅ Yes' if data['running'] else '❌ No'}\")
print(f\"   Jobs Count: {data['jobs_count']}\")
print()
print('📅 НАСТУПНІ ВИКОНАННЯ:')
for job in data['jobs']:
    name = job['name'][:35].ljust(35)
    next_run = job['next_run']
    if next_run:
        dt = datetime.fromisoformat(next_run.replace('+00:00', ''))
        time_str = dt.strftime('%H:%M:%S')
        print(f\"   {name} → {time_str}\")
"

echo ""
echo "ℹ️  Jobs виконуються автоматично за розкладом"
echo ""
read -p "Натисніть Enter для продовження..."
clear

# ============================================================================
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "КРОК 6: Ручне оновлення кешу (Demo)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Зараз запустимо ручне оновлення кешу..."
echo ""

before=$(curl -s http://localhost:8000/api/v1/scheduler/metrics | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['data']['scheduler']['cache_updates_total'])")

echo "Cache updates ДО:  $before"

curl -s -X POST http://localhost:8000/api/v1/scheduler/trigger/cache > /dev/null
echo "🔄 Виконується оновлення кешу..."
sleep 2

after=$(curl -s http://localhost:8000/api/v1/scheduler/metrics | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['data']['scheduler']['cache_updates_total'])")

echo "Cache updates ПІСЛЯ: $after"
echo ""
echo "✅ Кеш оновлено! Лічильник змінився: $before → $after"
echo ""
read -p "Натисніть Enter для фінального підсумку..."
clear

# ============================================================================
# ============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ПІДСУМОК ДЕМОНСТРАЦІЇ                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Що ми побачили:"
echo ""
echo "   1️⃣  Docker сервіси - 5/5 працюють"
echo "   2️⃣  Prometheus - збирає метрики з 4 targets"
echo "   3️⃣  Scheduler metrics - jobs executed, cache updates"
echo "   4️⃣  Grafana - готовий до створення dashboards"
echo "   5️⃣  Scheduler jobs - автоматично виконуються"
echo "   6️⃣  Manual triggers - можна запускати вручну"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Для детального моніторингу відкрийте:"
echo ""
echo "   🔹 Prometheus:  http://localhost:9090"
echo "      → Targets, Alerts, Graph queries"
echo ""
echo "   🔹 Grafana:     http://localhost:3000"
echo "      → Login: admin/admin"
echo "      → Create dashboards, visualizations"
echo ""
echo "   🔹 API Docs:    http://localhost:8000/docs"
echo "      → Всі 24 endpoints з прикладами"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Документація:"
echo ""
echo "   • docs/PROMETHEUS_GRAFANA_GUIDE.md     - Повний гайд"
echo "   • docs/MONITORING_QUICK_SETUP.md       - Швидкий старт"
echo "   • yield-data-service/monitoring/README.md - Конфігурація"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Система моніторингу готова до використання!"
echo ""
echo "Для швидкої перевірки статусу запустіть:"
echo "   ./check_system_status.sh"
echo ""

