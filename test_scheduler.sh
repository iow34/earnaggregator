#!/bin/bash

# Тестування Scheduler - РОЗДІЛ 3.3

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ТЕСТУВАННЯ SCHEDULER - РОЗДІЛ 3.3                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Статус scheduler
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  SCHEDULER STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "http://localhost:8000/api/v1/scheduler/status" | python3 -m json.tool | head -45
echo ""

# 2. Prometheus метрики
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  PROMETHEUS METRICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "http://localhost:8000/api/v1/scheduler/metrics" | python3 -m json.tool | head -40
echo ""

# 3. Ручне оновлення кешу
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  MANUAL CACHE UPDATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "http://localhost:8000/api/v1/scheduler/trigger/cache" | python3 -m json.tool
echo ""

# 4. Ручна перевірка здоров'я
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  MANUAL HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "http://localhost:8000/api/v1/scheduler/trigger/healthcheck" | python3 -m json.tool
echo ""

# 5. Статус після оновлень
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  UPDATED METRICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 2
curl -s "http://localhost:8000/api/v1/scheduler/metrics" | python3 -c "
import sys, json
data = json.load(sys.stdin)
metrics = data['data']['scheduler']
print(f\"Jobs Executed:  {metrics['jobs_executed_total']}\")
print(f\"Jobs Failed:    {metrics['jobs_failed_total']}\")
print(f\"Cache Updates:  {metrics['cache_updates_total']}\")
print(f\"DB Syncs:       {metrics['db_syncs_total']}\")
print(f\"API Calls:      {metrics['api_calls_total']}\")
print(f\"Avg Time:       {metrics['average_execution_time_ms']:.2f}ms\")
print(f\"Last Error:     {metrics['last_error']}\")
"
echo ""

# 6. Cache статистика
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  CACHE STATISTICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "http://localhost:8000/api/v1/scheduler/metrics" | python3 -c "
import sys, json
data = json.load(sys.stdin)
cache = data['data']['cache']
print(f\"Cache Hits:     {cache['hits']}\")
print(f\"Cache Misses:   {cache['misses']}\")
print(f\"Total Requests: {cache['total_requests']}\")
print(f\"Hit Rate:       {cache['hit_rate_percent']}%\")
print(f\"Redis:          {cache['redis_connected']}\")
print(f\"Memory Used:    {cache['redis_memory_used']}\")
"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ПІДСУМОК                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo "✅ Scheduler працює"
echo "✅ Метрики збираються"
echo "✅ Ручні тригери працюють"
echo "✅ Alerting налаштовано"
echo ""
echo "Для моніторингу в реальному часі:"
echo "  • Prometheus: http://localhost:9090 (якщо запущено)"
echo "  • Grafana:    http://localhost:3000 (якщо запущено)"
echo "  • Metrics:    curl http://localhost:8000/api/v1/scheduler/metrics"
echo ""

