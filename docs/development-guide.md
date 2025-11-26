# 👨‍💻 EarnAggregator Development Guide

## 📋 Зміст

1. [Початок роботи](#початок-роботи)
2. [Структура проекту](#структура-проекту)
3. [Локальна розробка](#локальна-розробка)
4. [Docker розробка](#docker-розробка)
5. [Тестування](#тестування)
6. [Логування та відладка](#логування-та-відладка)
7. [Git Workflow](#git-workflow)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Початок роботи

### **Вимоги:**

- **Docker Desktop** (обов'язково)
- **Git** для версійного контролю
- **Cursor IDE** (рекомендовано) або VS Code
- **Terminal** (iTerm2, Alacritty)

### **Перший запуск:**

```bash
# 1. Клонувати репозиторій
git clone <repository-url>
cd EarnAggregator

# 2. Створити .env файл
cp .env.stage .env
# Відредагувати .env з вашими налаштуваннями

# 3. Запустити всі сервіси
docker-compose up -d --build

# 4. Перевірити статус
docker-compose ps
```

### **Перевірка роботи:**

```bash
# API працює
curl http://localhost:8000/health

# PostgreSQL доступна
docker-compose exec postgres psql -U yield_user -d yield_db -c "SELECT NOW();"

# Redis працює
docker-compose exec redis redis-cli ping
```

---

## 📁 Структура проекту

```
EarnAggregator/
├── 📁 yield-data-service/          # FastAPI сервіс
│   ├── 📁 app/
│   │   ├── 📄 main.py              # Точка входу FastAPI
│   │   ├── 📄 config.py            # Налаштування
│   │   ├── 📁 api/                 # API endpoints
│   │   ├── 📁 services/            # Бізнес-логіка
│   │   ├── 📁 db/                  # База даних
│   │   └── 📁 utils/               # Допоміжні функції
│   ├── 📁 tests/                   # Тести
│   └── 📁 logs/                    # Логи
├── 📁 yield-telegram-bot/          # Telegram бот (буде)
├── 📁 server/                      # Frontend (буде)
├── 📁 docs/                        # Документація
├── 📄 docker-compose.yml           # Docker оркестрація
├── 📄 Dockerfile                   # Docker образ
├── 📄 requirements.txt             # Python залежності
└── 📄 .env                         # Змінні середовища
```

---

## 💻 Локальна розробка

### **Коли використовувати локальну розробку:**

- Швидкі тести Python скриптів
- Розробка утиліт
- Аналіз даних

### **Налаштування локального середовища:**

```bash
# 1. Створити віртуальне середовище (опціонально)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 2. Встановити залежності
pip install -r requirements.txt

# 3. Запустити тести
python -m pytest tests/

# 4. Запустити скрипти
python yield-data-service/tests/simple_test_api.py
```

### **Важливо:**

- **PostgreSQL та Redis** завжди запускайте через Docker
- Локальний Python використовуйте тільки для тестів
- Основна розробка - в Docker контейнерах

---

## 🐳 Docker розробка

### **Основні команди розробки:**

#### **Запуск всіх сервісів:**

```bash
# Повний запуск з перезбіркою
docker-compose up -d --build

# Запуск без перезбірки
docker-compose up -d

# Запуск з логами
docker-compose up --build
```

#### **Робота з окремими сервісами:**

```bash
# Запуск тільки бази даних
docker-compose up -d postgres redis

# Перезапуск API сервісу
docker-compose restart yield-api

# Перегляд логів
docker-compose logs -f yield-api
```

#### **Вхід в контейнер:**

```bash
# Вхід в API контейнер
docker-compose exec yield-api bash

# Вхід в PostgreSQL
docker-compose exec postgres psql -U yield_user -d yield_db

# Вхід в Redis
docker-compose exec redis redis-cli
```

### **Розробка в контейнері:**

```bash
# 1. Вхід в контейнер
docker-compose exec yield-api bash

# 2. Встановлення додаткових пакетів
pip install ipython jupyter

# 3. Запуск Python REPL
python

# 4. Тестування API
python -c "
import requests
response = requests.get('http://localhost:8000/health')
print(response.json())
"
```

---

## 🧪 Тестування

### **Типи тестів:**

#### **1. Unit тести:**

```bash
# Запуск всіх тестів
docker-compose exec yield-api python -m pytest tests/

# Запуск конкретного тесту
docker-compose exec yield-api python -m pytest tests/test_api.py::test_health_check

# Запуск з coverage
docker-compose exec yield-api python -m pytest --cov=app tests/
```

#### **2. API тести:**

```bash
# Тест API endpoints
python yield-data-service/tests/simple_test_api.py

# Тест реальних даних з бірж
python yield-data-service/tests/test_exchanges_real_data.py
```

#### **3. Інтеграційні тести:**

```bash
# Тест підключення до БД
docker-compose exec yield-api python -c "
from app.db.database import engine
print('Database connection:', engine.url)
"

# Тест Redis
docker-compose exec yield-api python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print('Redis ping:', r.ping())
"
```

### **Приклад тесту:**

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_yield_endpoint():
    response = client.get("/api/v1/yield/BTC")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "success" in data
```

---

## 📝 Логування та відладка

### **Логи в Docker:**

```bash
# Всі логи
docker-compose logs

# Логи конкретного сервісу
docker-compose logs yield-api

# Логи в реальному часі
docker-compose logs -f yield-api

# Останні 100 рядків
docker-compose logs --tail=100 yield-api
```

### **Файли логів:**

```bash
# Логи додатку
tail -f logs/app.log

# Логи помилок
tail -f logs/errors.log

# Логи в контейнері
docker-compose exec yield-api tail -f /app/logs/app.log
```

### **Відладка в коді:**

```python
# Використання logger
from app.utils.logger import logger

logger.info("Processing request", extra={
    "user_id": 123,
    "symbol": "BTC"
})

logger.error("API error", extra={
    "exchange": "binance",
    "error": str(e)
})
```

### **Debug режим:**

```bash
# Запуск з debug логами
docker-compose exec yield-api python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from app.main import app
"
```

---

## 🔄 Git Workflow

### **Структура гілок:**

```
main                 # Стабільна версія
├── develop         # Розробка
├── feature/api     # Нова функція API
├── feature/bot     # Telegram бот
└── hotfix/bug      # Виправлення помилок
```

### **Робочий процес:**

```bash
# 1. Створити feature гілку
git checkout -b feature/new-api-endpoint

# 2. Розробка та тести
# ... робота з кодом ...
docker-compose up -d --build
python -m pytest tests/

# 3. Commit змін
git add .
git commit -m "feat: add new yield endpoint"

# 4. Push гілки
git push origin feature/new-api-endpoint

# 5. Створити Pull Request
# (через GitHub/GitLab інтерфейс)

# 6. Merge в develop
git checkout develop
git merge feature/new-api-endpoint
```

### **Commit конвенції:**

```bash
feat: нова функція
fix: виправлення помилки
docs: документація
style: форматування коду
refactor: рефакторинг
test: тести
chore: налаштування
```

---

## 🔧 Troubleshooting

### **Часті проблеми:**

#### **1. "Port already in use"**

```bash
# Знайти процес на порту
lsof -i :8000

# Зупинити процес
kill -9 <PID>

# Або змінити порт в docker-compose.yml
```

#### **2. "Module not found"**

```bash
# Перевірити PYTHONPATH
docker-compose exec yield-api echo $PYTHONPATH

# Перевірити структуру в контейнері
docker-compose exec yield-api ls -la /app/

# Перезбудувати образ
docker-compose build --no-cache yield-api
```

#### **3. "Database connection failed"**

```bash
# Перевірити статус PostgreSQL
docker-compose ps postgres

# Перевірити логи
docker-compose logs postgres

# Перевірити підключення
docker-compose exec yield-api python -c "
from app.config import settings
print('Database URL:', settings.database_url)
"
```

#### **4. "Redis connection failed"**

```bash
# Перевірити Redis
docker-compose exec redis redis-cli ping

# Перевірити налаштування
docker-compose exec yield-api python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print('Redis ping:', r.ping())
"
```

### **Очищення Docker:**

```bash
# Зупинити всі контейнери
docker-compose down

# Видалити volumes (ОБЕРЕЖНО - втратите дані!)
docker-compose down -v

# Очистити невикористовувані образи
docker system prune -a

# Повне очищення
docker-compose down -v
docker system prune -a --volumes
```

---

## 📚 Корисні команди

### **Docker команди:**

```bash
# Швидкі alias (додати в ~/.zshrc)
alias dcup='docker-compose up -d'
alias dcdown='docker-compose down'
alias dcbuild='docker-compose up -d --build'
alias dcps='docker-compose ps'
alias dclogs='docker-compose logs -f'
alias dcexec='docker-compose exec'
```

### **Розробка команди:**

```bash
# Швидкий тест API
curl http://localhost:8000/health

# Тест бази даних
docker-compose exec postgres psql -U yield_user -d yield_db -c "SELECT COUNT(*) FROM earn_products;"

# Тест Redis
docker-compose exec redis redis-cli keys "*"

# Перегляд логів
tail -f logs/app.log
```

---

## 🎯 Наступні кроки

1. **✅ Docker Setup** - завершено
2. **✅ PostgreSQL** - налаштовано
3. **✅ FastAPI** - працює
4. **🔄 Наступний етап:** Інтеграція з Binance/Bybit API
5. **🔄 Потім:** Telegram Bot розробка
6. **🔄 Потім:** Frontend розробка

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Готово до розробки
