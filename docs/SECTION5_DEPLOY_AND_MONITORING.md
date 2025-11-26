# РОЗДІЛ 5: Деплой та моніторинг (Docker Compose + Telegram Alerts)

## 1. Підготовка

1) Заповніть `.env.production` (секрети, БД, Redis, Telegram):
```bash
nano .env.production
```

2) Переконайтеся, що файли існують:
- `docker-compose.prod.yml`
- `yield-data-service/monitoring/prometheus.yml`
- `yield-data-service/monitoring/alert_rules.yml`
- `yield-data-service/monitoring/alertmanager.yml`
- `yield-data-service/monitoring/grafana/datasources.yml`
- `yield-data-service/monitoring/grafana/dashboards.yml`
- `yield-data-service/monitoring/grafana/dashboards/earn_overview.json`
- `scripts/backup.sh`, `scripts/restore.sh`

## 2. Запуск продакшну

```bash
# З кореня проекту
docker-compose -f docker-compose.prod.yml up -d --build

# Перевірити статус
docker-compose -f docker-compose.prod.yml ps
```

## 3. Перевірки здоров’я

- API: `curl http://localhost:8000/health`
- Prometheus: `http://localhost:9090` → Status → Targets (усі UP)
- Grafana: `http://localhost:3000` (admin/admin або змінені креденшли)
- Alertmanager: `http://localhost:9093`

## 4. Алерти в Telegram

1) Створіть бота через @BotFather та отримайте токен
2) Дізнайтесь `chat_id` (через @userinfobot або власний спосіб)
3) Заповніть у `.env.production`:
```
ALERTMANAGER_TELEGRAM_BOT_TOKEN=...
ALERTMANAGER_TELEGRAM_CHAT_ID=...
```
4) Перезапустіть Alertmanager/Prometheus:
```bash
docker-compose -f docker-compose.prod.yml restart alertmanager prometheus
```
5) Форс-тест: тимчасово підвищити поріг правил або зупинити `yield-api` на 2-3 хвилини.

## 5. Дашборди Grafana

- Data source: Prometheus (налаштовано provisioning)
- Імпортований дашборд: `EarnAggregator Overview`
- Основні панелі:
  - Service Health (up)
  - HTTP p95 latency
  - Requests/sec
  - 5xx rate
  - Container CPU (cadvisor)

## 6. Бекапи БД

- Розклад: щодня 03:00 (cron у `db-backup`)
- Шлях: `./backups/pg_<db>_<timestamp>.sql.gz`

Ручний запуск:
```bash
docker-compose -f docker-compose.prod.yml exec db-backup /usr/local/bin/backup.sh
```
Відновлення:
```bash
docker-compose -f docker-compose.prod.yml exec -T db-backup /usr/local/bin/restore.sh /backups/pg_yield_db_20250101_120000.sql.gz
```

## 7. Траблшутінг

- Targets DOWN у Prometheus:
  - Перевірити `yield-api`/`cadvisor` контейнери
  - Перевірити мережу `earn_backend`
  - Перевірити `prometheus.yml` та `/-/reload`

- Немає алертів у Telegram:
  - Перевірити `ALERTMANAGER_*` у `.env.production`
  - Перезавантажити `alertmanager`
  - Переглянути лог `earn-alertmanager`

- Grafana не бачить Prometheus:
  - Переконатися, що URL `http://prometheus:9090` у `datasources.yml`
  - Перевірити мережу контейнерів

## 8. Команди

```bash
# Повний деплой/перезапуск
docker-compose -f docker-compose.prod.yml up -d --build

# Оновити лише конфіг Prometheus (без рестарту)
curl -X POST http://localhost:9090/-/reload

# Логи сервісів
docker logs -f earn-yield-api
docker logs -f earn-prometheus
docker logs -f earn-alertmanager
```

---
Готово до продакшну з моніторингом та Telegram-алертами.
