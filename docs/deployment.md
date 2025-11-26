# 🚀 EarnAggregator Deployment Guide

## 📋 Зміст

1. [Огляд deployment](#огляд-deployment)
2. [Development Environment](#development-environment)
3. [Staging Environment](#staging-environment)
4. [Production Environment](#production-environment)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Моніторинг](#моніторинг)
7. [Backup та Recovery](#backup-та-recovery)

---

## 🎯 Огляд Deployment

EarnAggregator підтримує кілька середовищ для різних етапів розробки та використання.

### **Середовища:**

| Середовище      | Призначення               | URL                          | Статус        |
| --------------- | ------------------------- | ---------------------------- | ------------- |
| **Development** | Локальна розробка         | `localhost:8000`             | ✅ Активне    |
| **Staging**     | Тестування перед продакшн | `staging.earnaggregator.com` | 🔄 Планується |
| **Production**  | Продакшн сервіс           | `api.earnaggregator.com`     | 🔄 Планується |

---

## 💻 Development Environment

### **Поточна конфігурація (Docker Compose):**

**Файли:**

- `docker-compose.yml` - оркестрація сервісів
- `Dockerfile` - образ FastAPI додатку
- `.env` - змінні середовища

**Сервіси:**

```yaml
services:
  postgres: # PostgreSQL 15
  redis: # Redis 7
  yield-api: # FastAPI додаток
```

### **Запуск Development:**

```bash
# 1. Клонувати репозиторій
git clone <repository-url>
cd EarnAggregator

# 2. Налаштувати .env
cp .env.stage .env
# Відредагувати з локальними налаштуваннями

# 3. Запустити сервіси
docker-compose up -d --build

# 4. Перевірити статус
docker-compose ps
curl http://localhost:8000/health
```

### **Development URLs:**

- **API:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`
- **PostgreSQL:** `localhost:5432`
- **Redis:** `localhost:6379`

---

## 🧪 Staging Environment

### **Призначення:**

- Тестування нових функцій
- Інтеграційні тести
- Performance тести
- User Acceptance Testing (UAT)

### **Планувана архітектура:**

```
┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Staging API   │
│   (Nginx)       │────│   (FastAPI)     │
└─────────────────┘    └─────────┬───────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   PostgreSQL    │    │      Redis      │    │   Monitoring    │
│   (Staging DB)  │    │   (Staging)     │    │   (Prometheus)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Staging конфігурація:**

```yaml
# docker-compose.staging.yml
version: "3.8"
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - yield-api

  yield-api:
    build: .
    environment:
      - ENVIRONMENT=staging
      - DATABASE_URL=postgresql://user:pass@postgres:5432/yield_staging
      - REDIS_URL=redis://redis:6379/1
    deploy:
      replicas: 2

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=yield_staging
      - POSTGRES_USER=staging_user
      - POSTGRES_PASSWORD=staging_password
    volumes:
      - staging_db_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - staging_redis_data:/data

volumes:
  staging_db_data:
  staging_redis_data:
```

### **Deployment процес:**

```bash
# 1. Підготовка staging
docker-compose -f docker-compose.staging.yml up -d --build

# 2. Міграції БД
docker-compose exec yield-api alembic upgrade head

# 3. Тести
docker-compose exec yield-api python -m pytest tests/

# 4. Health check
curl http://staging.earnaggregator.com/health
```

---

## 🌐 Production Environment

### **Планувана архітектура:**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CDN           │    │   Load Balancer │    │   API Gateway   │
│   (CloudFlare)  │────│   (Nginx)       │────│   (Kong)        │
└─────────────────┘    └─────────────────┘    └─────────┬───────┘
                                                        │
          ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
          │                                             │                                             │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   API Service   │    │   API Service   │    │   API Service   │    │   API Service   │
│   (Instance 1)  │    │   (Instance 2)  │    │   (Instance 3)  │    │   (Instance 4)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │                      │
          └──────────────────────┼──────────────────────┼──────────────────────┘
                                 │                      │
                    ┌─────────────▼─────────────┐    ┌───▼─────────────┐
                    │   PostgreSQL Cluster     │    │   Redis Cluster │
                    │   (Primary + Replicas)   │    │   (Sentinel)    │
                    └───────────────────────────┘    └─────────────────┘
```

### **Production конфігурація:**

```yaml
# docker-compose.production.yml
version: "3.8"
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - yield-api

  yield-api:
    build: .
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${PROD_DATABASE_URL}
      - REDIS_URL=${PROD_REDIS_URL}
      - LOG_LEVEL=INFO
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${PROD_DB_NAME}
      - POSTGRES_USER=${PROD_DB_USER}
      - POSTGRES_PASSWORD=${PROD_DB_PASSWORD}
    volumes:
      - prod_db_data:/var/lib/postgresql/data
      - ./backups:/backups
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - prod_redis_data:/data
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  prod_db_data:
  prod_redis_data:
```

### **Production змінні середовища:**

```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
PROD_DATABASE_URL=postgresql://user:password@postgres:5432/yield_prod
PROD_DB_NAME=yield_prod
PROD_DB_USER=prod_user
PROD_DB_PASSWORD=secure_production_password

# Redis
PROD_REDIS_URL=redis://redis:6379/0

# API Keys
BINANCE_API_KEY=your_production_binance_key
BINANCE_API_SECRET=your_production_binance_secret
BYBIT_API_KEY=your_production_bybit_key
BYBIT_API_SECRET=your_production_bybit_secret

# Security
SECRET_KEY=your_super_secret_key_here
JWT_SECRET=your_jwt_secret_here

# Monitoring
PROMETHEUS_ENDPOINT=http://prometheus:9090
GRAFANA_ENDPOINT=http://grafana:3000
```

---

## 🔄 CI/CD Pipeline

### **GitHub Actions Workflow:**

```yaml
# .github/workflows/deploy.yml
name: Deploy EarnAggregator

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          python -m pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          docker build -t earnaggregator/api:latest .
          docker tag earnaggregator/api:latest earnaggregator/api:${{ github.sha }}

      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push earnaggregator/api:latest
          docker push earnaggregator/api:${{ github.sha }}

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          # SSH to staging server
          ssh staging-server "cd /opt/earnaggregator && docker-compose -f docker-compose.staging.yml pull && docker-compose -f docker-compose.staging.yml up -d"

  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # SSH to production server
          ssh production-server "cd /opt/earnaggregator && docker-compose -f docker-compose.production.yml pull && docker-compose -f docker-compose.production.yml up -d"
```

### **Deployment стратегія:**

1. **Blue-Green Deployment** - безпечне оновлення
2. **Rolling Updates** - поступове оновлення
3. **Health Checks** - автоматичний rollback при помилках

---

## 📊 Моніторинг

### **Production метрики:**

- **API Response Time** - час відповіді
- **Request Rate** - кількість запитів/сек
- **Error Rate** - відсоток помилок
- **Database Performance** - час виконання запитів
- **Cache Hit Rate** - ефективність кешу
- **Memory/CPU Usage** - використання ресурсів

### **Alerting правила:**

```yaml
# prometheus-alerts.yml
groups:
  - name: earnaggregator
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
```

### **Логування:**

```yaml
# docker-compose.production.yml
services:
  yield-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 💾 Backup та Recovery

### **Database Backup:**

```bash
# Щоденний backup
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U yield_user yield_db > backup_${DATE}.sql

# Автоматичний backup (cron)
0 2 * * * /opt/earnaggregator/scripts/backup.sh
```

### **Redis Backup:**

```bash
# Redis persistence
docker-compose exec redis redis-cli BGSAVE
```

### **Recovery процес:**

```bash
# 1. Зупинити сервіси
docker-compose down

# 2. Відновити базу даних
docker-compose exec postgres psql -U yield_user yield_db < backup_20241016_020000.sql

# 3. Перезапустити сервіси
docker-compose up -d

# 4. Перевірити статус
curl http://localhost:8000/health
```

---

## 🔒 Безпека

### **Production безпека:**

- **HTTPS** - SSL/TLS сертифікати
- **Firewall** - обмеження доступу
- **API Keys** - ротація ключів
- **Database** - шифрування даних
- **Secrets** - управління секретами

### **Docker Security:**

```dockerfile
# Використання non-root користувача
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Мінімальний образ
FROM python:3.11-slim

# Оновлення пакетів
RUN apt-get update && apt-get upgrade -y
```

---

## 📈 Масштабування

### **Горизонтальне масштабування:**

```yaml
# docker-compose.production.yml
services:
  yield-api:
    deploy:
      replicas: 4
      update_config:
        parallelism: 2
        delay: 10s
        failure_action: rollback
```

### **Load Balancing:**

```nginx
# nginx.conf
upstream api_backend {
    server yield-api_1:8000;
    server yield-api_2:8000;
    server yield-api_3:8000;
    server yield-api_4:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Готово до deployment
