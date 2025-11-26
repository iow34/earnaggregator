#!/bin/bash

# Швидка перевірка статусу всієї системи EarnAggregator

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     EarnAggregator - Перевірка статусу системи            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Кольори
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Health Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
health_response=$(curl -s "http://localhost:8000/api/v1/health")
db_status=$(echo $health_response | python3 -c "import sys, json; print(json.load(sys.stdin)['database_status'])")
cache_status=$(echo $health_response | python3 -c "import sys, json; print(json.load(sys.stdin)['cache_status'])")
binance_status=$(echo $health_response | python3 -c "import sys, json; print(json.load(sys.stdin)['api_status']['binance'])")
bybit_status=$(echo $health_response | python3 -c "import sys, json; print(json.load(sys.stdin)['api_status']['bybit'])")

echo -n "Database: "
if [ "$db_status" = "healthy" ]; then
    echo -e "${GREEN}✅ $db_status${NC}"
else
    echo -e "${RED}❌ $db_status${NC}"
fi

echo -n "Cache:    "
if [ "$cache_status" = "healthy" ]; then
    echo -e "${GREEN}✅ $cache_status${NC}"
else
    echo -e "${RED}❌ $cache_status${NC}"
fi

echo -n "Binance:  "
if [ "$binance_status" = "success" ]; then
    echo -e "${GREEN}✅ $binance_status${NC}"
else
    echo -e "${YELLOW}⚠️  $binance_status${NC}"
fi

echo -n "Bybit:    "
if [ "$bybit_status" = "success" ]; then
    echo -e "${GREEN}✅ $bybit_status${NC}"
else
    echo -e "${YELLOW}⚠️  $bybit_status${NC}"
fi

echo ""

# 2. Database Stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  DATABASE STATISTICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
stats_response=$(curl -s "http://localhost:8000/api/v1/stats")
total_products=$(echo $stats_response | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_products', 0))")
active_products=$(echo $stats_response | python3 -c "import sys, json; print(json.load(sys.stdin).get('active_products', 0))")

echo -e "Total Products:  ${GREEN}$total_products${NC}"
echo -e "Active Products: ${GREEN}$active_products${NC}"
echo ""

# 3. Cache Stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  CACHE STATISTICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cache_stats=$(curl -s "http://localhost:8000/api/v1/cache/stats")
redis_connected=$(echo $cache_stats | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['redis_connected'])")
hit_rate=$(echo $cache_stats | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['hit_rate_percent'])")
memory_used=$(echo $cache_stats | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['redis_memory_used'])")

echo -n "Redis Connected: "
if [ "$redis_connected" = "True" ]; then
    echo -e "${GREEN}✅ Yes${NC}"
else
    echo -e "${RED}❌ No${NC}"
fi
echo -e "Hit Rate:        ${YELLOW}$hit_rate%${NC}"
echo -e "Memory Used:     ${YELLOW}$memory_used${NC}"
echo ""

# 4. Aggregation Service
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  AGGREGATION SERVICE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
agg_test=$(curl -s "http://localhost:8000/api/v1/aggregation/test?limit=5&strategy=fast_cache_first")
products_found=$(echo $agg_test | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['aggregation_result']['products_found'])")
response_time=$(echo $agg_test | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['aggregation_result']['total_response_time_ms'])")
quality=$(echo $agg_test | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['aggregation_result']['data_quality_score'])")

echo -e "Products Found:  ${GREEN}$products_found${NC}"
echo -e "Response Time:   ${YELLOW}${response_time}ms${NC}"
echo -e "Quality Score:   ${YELLOW}$quality${NC}"
echo ""

# 5. Sample Data Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  SAMPLE DATA TEST (BTC)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
btc_data=$(curl -s "http://localhost:8000/api/v1/yield/BTC?limit=3")
btc_count=$(echo $btc_data | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")

echo -e "BTC Products Found: ${GREEN}$btc_count${NC}"
echo ""

# Final Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ПІДСУМОК                                ║"
echo "╚════════════════════════════════════════════════════════════╝"

if [ "$db_status" = "healthy" ] && [ "$cache_status" = "healthy" ] && [ "$binance_status" = "success" ] && [ "$bybit_status" = "success" ]; then
    echo -e "${GREEN}✅ ВСІ СИСТЕМИ ПРАЦЮЮТЬ НОРМАЛЬНО!${NC}"
    echo -e "${GREEN}🚀 Система готова до використання!${NC}"
else
    echo -e "${RED}⚠️  Деякі системи потребують уваги${NC}"
fi

echo ""
echo "Для детальної інформації:"
echo "  • Health:      curl http://localhost:8000/api/v1/health"
echo "  • Stats:       curl http://localhost:8000/api/v1/stats"
echo "  • API Docs:    http://localhost:8000/docs"
echo ""

