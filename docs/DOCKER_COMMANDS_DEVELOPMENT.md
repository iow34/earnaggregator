# 🐳 Docker Commands Guide - Development

## 📋 Зміст

1. [Початок Роботи](#початок-роботи)
2. [10 Основних Сценаріїв](#10-основних-сценаріїв)
3. [Додаткові Інструменти для macOS](#додаткові-інструменти-для-macos)
4. [Docker vs venv](#docker-vs-venv)
5. [Troubleshooting](#troubleshooting)

---

**### Швидке налаштування**

**# Шлях до проекту**
cd /Users/user777/Documents/EarnAggregator

**# Запустити всі сервіси**
docker-compose up -d

**# Перевірити запущені контейнери**
docker-compose ps

**# Перевірити логи**
docker-compose logs yield-api

**#Перезапустити з перебудовою**
docker-compose up --build -d

**# Зупинити всі контейнери**
docker-compose down

**#Статистика контейнерів**
docker stats

**#Перевірити логи контейнера**
docker-compose logs yield-api

**# Перевірити конфігурацію**
docker-compose config

**# Показати усі запущеніконтейнери**
docker ps

**# Показати всі (запущені та зупинені)**
docker ps -a

**# Перевірити образи (images)**
docker images | grep mcp

---

## 🚀 Початок Роботи

### Передумови на macOS

**1. Встановіть Docker Desktop:**

```bash
# Завантажте з docker.com або через Homebrew
brew install --cask docker

# Запустіть Docker Desktop
open -a Docker
```

**2. Перевірте встановлення:**

```bash
docker --version
docker-compose --version
```

**3. Перейдіть до проекту:**

```bash
cd /Users/user777/Documents/EarnAggregator
```

---

## 🎯 10 Основних Сценаріїв

### Сценарій 1: Перший запуск проекту

**Коли:** Ви тільки клонували проект або вперше працюєте з ним.

```bash
# 1. Перевірте чи є .env файл
ls -la .env

# 2. Запустіть всі сервіси
docker-compose up -d

# 3. Перевірте статус
docker-compose ps

# 4. Перевірте логи
docker-compose logs yield-api
```

**Очікуваний результат:**

```
NAME            SERVICE     STATUS
earn-postgres   postgres    Up (healthy)
earn-redis      redis       Up (healthy)
earn-yield-api  yield-api   Up (healthy)
```

### Сценарій 2: Розробка з hot reload

**Коли:** Ви редагуєте код і хочете бачити зміни автоматично.

```bash
# Запустіть тільки API сервіс з автоперезавантаженням
docker-compose up yield-api

# В іншому терміналі запустіть БД та Redis
docker-compose up -d postgres redis
```

**Переваги:**

- ✅ Зміни в коді відображаються автоматично
- ✅ Детальні логи помилок
- ✅ Швидка ітерація розробки

### Сценарій 3: Тестування API endpoints

**Коли:** Потрібно перевірити роботу API.

```bash
# 1. Перевірте що сервіс працює
curl http://localhost:8000/health

# 2. Відкрийте документацію API
open http://localhost:8000/docs

# 3. Тестуйте конкретні endpoints
curl http://localhost:8000/api/v1/status
```

**Очікувана відповідь:**

```json
{
  "status": "healthy",
  "service": "yield-data-service"
}
```

### Сценарій 4: Робота з базою даних

**Коли:** Потрібно виконати SQL запити або перевірити дані.

```bash
# 1. Підключіться до PostgreSQL
docker-compose exec postgres psql -U yield_user -d yield_db

# 2. Виконайте SQL запити
# \dt - список таблиць
# SELECT * FROM earn_products LIMIT 5;
# \q - вихід

# 3. Або через один рядок
docker-compose exec postgres psql -U yield_user -d yield_db -c "SELECT COUNT(*) FROM earn_products;"
```

### Сценарій 5: Перевірка логів

**Коли:** Щось не працює або потрібно відстедити помилки.

```bash
# 1. Всі логи одночасно
docker-compose logs

# 2. Логи конкретного сервісу
docker-compose logs yield-api
docker-compose logs postgres
docker-compose logs redis

# 3. Логи в реальному часі
docker-compose logs -f yield-api

# 4. Останні 50 рядків
docker-compose logs --tail=50 yield-api
```

### Сценарій 6: Зупинка та очищення

**Коли:** Завершуєте роботу або хочете почистити систему.

```bash
# 1. Зупинити всі контейнери
docker-compose down

# 2. Зупинити та видалити volumes (ВНИМАНИНЕ: втратите дані!)
docker-compose down -v

# 3. Видалити образи
docker-compose down --rmi all

# 4. Повне очищення (контейнери + volumes + мережі)
docker-compose down -v --remove-orphans
docker system prune -f
```

### Сценарій 7: Перезапуск після змін

**Коли:** Змінили docker-compose.yml або Dockerfile.

```bash
# 1. Перезапустити з перебудовою
docker-compose up --build -d

# 2. Перезапустити конкретний сервіс
docker-compose up --build yield-api

# 3. Примусове перебудовування (без кешу)
docker-compose build --no-cache yield-api
docker-compose up yield-api
```

### Сценарій 8: Відладка контейнера

**Коли:** Потрібно увійти в контейнер для діагностики.

```bash
# 1. Увійти в yield-api контейнер
docker-compose exec yield-api bash

# 2. Перевірити файлову систему
docker-compose exec yield-api ls -la /app

# 3. Перевірити змінні середовища
docker-compose exec yield-api env | grep -E "(POSTGRES|REDIS)"

# 4. Запустити Python в контейнері
docker-compose exec yield-api python -c "import sys; print(sys.path)"
```

### Сценарій 9: Моніторинг ресурсів

**Коли:** Потрібно перевірити використання ресурсів.

```bash
# 1. Статистика контейнерів
docker stats

# 2. Детальна інформація про контейнер
docker-compose exec yield-api cat /proc/meminfo

# 3. Використання диску
docker system df

# 4. Перевірка мереж
docker network ls
docker network inspect earn_backend
```

### Сценарій 10: Backup та Restore

**Коли:** Потрібно зберегти або відновити дані.

```bash
# 1. Backup бази даних
docker-compose exec postgres pg_dump -U yield_user yield_db > backup_$(date +%Y%m%d).sql

# 2. Restore бази даних
docker-compose exec -T postgres psql -U yield_user yield_db < backup_20241016.sql

# 3. Backup Redis
docker-compose exec redis redis-cli BGSAVE
docker cp earn-redis:/data/dump.rdb ./redis_backup.rdb

# 4. Restore Redis
docker cp ./redis_backup.rdb earn-redis:/data/dump.rdb
docker-compose restart redis
```

---

## 🛠️ Додаткові Інструменти для macOS

### 1. **Docker Desktop Dashboard**

**Встановлення:** Вже включено в Docker Desktop

**Використання:**

- Відкрийте Docker Desktop
- Перейдіть на вкладку "Containers"
- Переглядайте логи, ресурси, налаштування

**Переваги:**

- ✅ Графічний інтерфейс
- ✅ Моніторинг ресурсів
- ✅ Управління контейнерами
- ✅ Перегляд логів

### 2. **LazyDocker** (Термінальний інтерфейс)

**Встановлення:**

```bash
brew install lazygit
```

**Використання:**

```bash
lazydocker
```

**Переваги:**

- ✅ Красивий термінальний інтерфейс
- ✅ Швидкий доступ до команд
- ✅ Моніторинг в реальному часі

### 3. **Portainer** (Веб-інтерфейс)

**Встановлення:**

```bash
docker run -d -p 9000:9000 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock portainer/portainer-ce
```

**Доступ:** http://localhost:9000

**Переваги:**

- ✅ Повний веб-інтерфейс
- ✅ Управління образами та контейнерами
- ✅ Моніторинг мереж та volumes

### 4. **Docker Compose VSCode Extension**

**Встановлення:**

- Відкрийте VSCode
- Встановіть розширення "Docker"
- Встановіть розширення "Docker Compose"

**Переваги:**

- ✅ Інтеграція з редактором
- ✅ Швидкий запуск команд
- ✅ Перегляд логів в VSCode

---

## 🤔 Docker vs venv - Пояснення

### **Docker - Що це?**

Docker створює **ізольовані контейнери** з повним середовищем:

- ✅ Операційна система (Linux)
- ✅ Python інтерпретатор
- ✅ Всі залежності (pip packages)
- ✅ База даних (PostgreSQL)
- ✅ Кеш (Redis)
- ✅ Мережа між сервісами

### **venv - Що це?**

venv створює **ізольоване Python середовище**:

- ✅ Python інтерпретатор
- ✅ pip packages
- ❌ Немає ОС
- ❌ Немає бази даних
- ❌ Немає мережі

### **Коли використовувати Docker:**

```bash
# ✅ КОЛИ ПРАЦЮЄТЕ З ПРОЕКТОМ
docker-compose up -d

# ✅ КОЛИ ТЕСТУЄТЕ API
curl http://localhost:8000/health

# ✅ КОЛИ РОЗРОБЛЯЄТЕ
docker-compose up yield-api
```

### **Коли використовувати venv:**

```bash
# ❌ НЕ ПОТРІБНО для цього проекту!
# venv використовується коли:
# - Запускаєте Python скрипти локально
# - Розробляєте без Docker
# - Тестуєте окремі модулі
```

### **Зв'язок Docker та venv:**

**Docker КОНТЕЙНЕР вже містить venv!**

```bash
# Всередині Docker контейнера:
/app/yield-data-service/venv/  # Python venv
/app/                          # Код проекту
/usr/local/lib/python3.11/     # Python системний
```

**Висновок:**

- 🐳 **Docker** - для розробки проекту (рекомендовано)
- 🐍 **venv** - для локальних Python скриптів (опціонально)

---

## 🚨 Troubleshooting

### Проблема 1: "Port already in use"

**Симптоми:**

```
ERROR: for yield-api  Cannot start service yield-api: driver failed programming external connectivity
```

**Рішення:**

```bash
# 1. Знайдіть процес що використовує порт
lsof -ti:8000

# 2. Вбийте процес
kill -9 $(lsof -ti:8000)

# 3. Або змініть порт в docker-compose.yml
```

### Проблема 2: "Container keeps restarting"

**Симптоми:**

```
earn-yield-api  | Exited (1) 2 seconds ago
earn-yield-api  | Restarting...
```

**Рішення:**

```bash
# 1. Перевірте логи
docker-compose logs yield-api

# 2. Перевірте конфігурацію
docker-compose config

# 3. Перезапустіть з чистим образом
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Проблема 3: "Database connection failed"

**Симптоми:**

```
psycopg2.OperationalError: could not connect to server
```

**Рішення:**

```bash
# 1. Перевірте що PostgreSQL запущений
docker-compose ps postgres

# 2. Перевірте підключення
docker-compose exec postgres psql -U yield_user -d yield_db -c "SELECT 1;"

# 3. Перевірте .env файл
cat .env | grep DATABASE_URL
```

### Проблема 4: "Docker Desktop not running"

**Симптоми:**

```
Cannot connect to the Docker daemon
```

**Рішення:**

```bash
# 1. Запустіть Docker Desktop
open -a Docker

# 2. Дочекайтесь повного запуску (іконка в меню)
# 3. Перевірте статус
docker ps
```

---

## 📚 Корисні Аліаси

Додайте в `~/.zshrc` або `~/.bash_profile`:

```bash
# Docker aliases
alias dc="docker-compose"
alias dcu="docker-compose up -d"
alias dcd="docker-compose down"
alias dcl="docker-compose logs -f"
alias dcb="docker-compose up --build"
alias dce="docker-compose exec"

# EarnAggregator specific
alias earn-up="cd /Users/user777/Documents/EarnAggregator && docker-compose up -d"
alias earn-down="cd /Users/user777/Documents/EarnAggregator && docker-compose down"
alias earn-logs="cd /Users/user777/Documents/EarnAggregator && docker-compose logs -f yield-api"
alias earn-db="cd /Users/user777/Documents/EarnAggregator && docker-compose exec postgres psql -U yield_user -d yield_db"
```

Перезавантажте термінал:

```bash
source ~/.zshrc
```

Тепер можна використовувати:

```bash
earn-up    # Запустити проект
earn-logs  # Дивитись логи
earn-db    # Підключитись до БД
```

---

## 🎯 Швидкий Старт

**Щоденна робота з проектом:**

```bash
# 1. Відкрити термінал
cd /Users/user777/Documents/EarnAggregator

# 2. Запустити проект
docker-compose up -d

# 3. Перевірити статус
docker-compose ps

# 4. Відкрити API документацію
open http://localhost:8000/docs

# 5. Зупинити проект
docker-compose down
```

**Готово! 🚀**

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Готово до використання

---

## 🚀 Docker Compose: Розробка vs Продакшн

### Що таке `docker-compose.yml` vs `docker-compose.prod.yml`?

| Аспект         | `docker-compose.yml` (Розробка)                          | `docker-compose.prod.yml` (Продакшн)                 |
| -------------- | -------------------------------------------------------- | ---------------------------------------------------- |
| **Мета**       | Розробка, тестування, швидка ітерація                    | Стабільна робота в продакшні                         |
| **Сервіси**    | Основні: postgres, redis, yield-api, prometheus, grafana | Повний стек: + alertmanager, cadvisor, db-backup     |
| **Конфіг**     | `.env` (локальні змінні)                                 | `.env.production` (секрети, прод-налаштування)       |
| **Логи**       | Детальні (INFO, DEBUG)                                   | Структуровані JSON-логи з ротацією                   |
| **Моніторинг** | Базовий (Prometheus + Grafana)                           | Повний (алерти в Telegram, бекапи, метрики ресурсів) |
| **Безпека**    | Відкритий доступ                                         | Закриті порти, обмеження доступу                     |
| **Рестарти**   | `unless-stopped`                                         | `unless-stopped` з health checks                     |
| **Volumes**    | Основні дані                                             | + бекапи, ротація логів                              |

### 🔄 Коли використовувати який файл?

#### ✅ Використовуйте `docker-compose.yml` (розробка):

- **Розробка нових функцій** - швидкий запуск, hot reload
- **Тестування** - локальні тести, відлагодження
- **Перше знайомство** - вивчення проекту
- **Швидкі зміни** - коли треба швидко перезапустити
- **Локальна розробка** - робота без продакшн конфігів

#### ✅ Використовуйте `docker-compose.prod.yml` (продакшн):

- **Розгортання на сервері** - продакшн environment
- **Моніторинг та алерти** - Telegram сповіщення
- **Автоматичні бекапи** - щоденні резервні копії БД
- **Стабільна робота** - з health checks та recovery
- **Масштабування** - готовність до навантаження

### 📋 Покрокові інструкції

#### Сценарій 1: Розробка (docker-compose.yml)

```bash
# 1. Перейти до проекту
cd /Users/user777/Documents/EarnAggregator

# 2. Запустити для розробки
docker-compose up -d

# 3. Перевірити що працює
docker-compose ps

# 4. Відкрити API документацію
open http://localhost:8000/docs

# 5. Дивитися логи в режимі реального часу
docker-compose logs -f yield-api

# 6. Зупинити після роботи
docker-compose down
```

#### Сценарій 2: Продакшн (docker-compose.prod.yml)

```bash
# 1. Перевірити .env.production (секрети!)
nano .env.production
# Заповнити: DATABASE_URL, API ключі, Telegram токен

# 2. Запустити продакшн стек
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Перевірити всі сервіси
docker-compose -f docker-compose.prod.yml ps

# 4. Перевірити здоров'я
curl http://localhost:8000/health

# 5. Перевірити моніторинг
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9093  # Alertmanager

# 6. Тест алертів (зупинити API на 2 хвилини)
docker-compose -f docker-compose.prod.yml stop yield-api
sleep 120
docker-compose -f docker-compose.prod.yml start yield-api
# Перевірити Telegram на алерт

# 7. Перевірити бекапи
docker-compose -f docker-compose.prod.yml exec db-backup ls -la /backups/

# 8. Зупинити продакшн
docker-compose -f docker-compose.prod.yml down
```

#### Сценарій 3: Перехід з розробки в продакшн

```bash
# 1. Зупинити розробку
docker-compose down

# 2. Підготувати продакшн конфіг
cp .env .env.production  # скопіювати як базу
nano .env.production     # відредагувати секрети

# 3. Запустити продакшн
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Міграція даних (якщо потрібно)
# Дані автоматично перенесені через volumes
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U yield_user yield_db > migration.sql
docker-compose -f docker-compose.prod.yml exec postgres psql -U yield_user yield_db < migration.sql
```

#### Сценарій 4: Оновлення продакшн сервісу

```bash
# 1. Підтягнути зміни з Git
git pull origin main

# 2. Перебудувати та перезапустити
docker-compose -f docker-compose.prod.yml up -d --build yield-api

# 3. Перевірити що працює
curl http://localhost:8000/health

# 4. Якщо помилки - rollback
docker-compose -f docker-compose.prod.yml up -d --build --no-deps yield-api
```

#### Сценарій 5: Відновлення з бекапу

```bash
# 1. Зупинити сервіси
docker-compose -f docker-compose.prod.yml stop postgres yield-api

# 2. Знайти останній бекап
ls -la backups/ | tail -5

# 3. Відновити базу
docker-compose -f docker-compose.prod.yml exec -T db-backup /usr/local/bin/restore.sh /backups/pg_yield_db_20241020_030000.sql.gz

# 4. Перезапустити сервіси
docker-compose -f docker-compose.prod.yml start postgres yield-api

# 5. Перевірити дані
curl http://localhost:8000/api/v1/stats
```

### 🛠️ Найпоширеніші команди

#### Для розробки:

```bash
# Швидкий старт
docker-compose up -d

# Розробка з hot reload
docker-compose up yield-api

# Логи всіх сервісів
docker-compose logs

# Очистити все
docker-compose down -v --remove-orphans
```

#### Для продакшну:

```bash
# Повний запуск
docker-compose -f docker-compose.prod.yml up -d --build

# Оновити конфіг Prometheus (без перезапуску)
curl -X POST http://localhost:9090/-/reload

# Ручний бекап
docker-compose -f docker-compose.prod.yml exec db-backup /usr/local/bin/backup.sh

# Перевірити алерти
docker logs earn-alertmanager | tail -20

# Зупинити все
docker-compose -f docker-compose.prod.yml down -v
```

### ⚠️ Важливі застереження

#### Для розробки (`docker-compose.yml`):

- ✅ **Використовуйте завжди** для розробки
- ❌ **Не використовуйте** на продакшн сервері
- ❌ **Не комітьте** справжні секрети в `.env`

#### Для продакшну (`docker-compose.prod.yml`):

- ✅ **Заповніть** `.env.production` перед запуском
- ✅ **Налаштуйте** Telegram бот для алертів
- ✅ **Перевіряйте** бекапи регулярно
- ❌ **Не запускайте** на тій самій машині що і розробка
- ❌ **Не видаляйте** volumes з даними без бекапу

### 🔄 Переключення між режимами

```bash
# З розробки в продакшн
docker-compose down
docker-compose -f docker-compose.prod.yml up -d --build

# З продакшну в розробку
docker-compose -f docker-compose.prod.yml down
docker-compose up -d
```

### 📊 Статус сервісів

#### Розробка (docker-compose.yml):

```bash
docker-compose ps
# NAME           SERVICE     STATUS
# earn-postgres   postgres    Up (healthy)
# earn-redis      redis       Up (healthy)
# earn-yield-api  yield-api   Up (healthy)
# earn-prometheus prometheus  Up (healthy)
# earn-grafana    grafana     Up
```

#### Продакшн (docker-compose.prod.yml):

```bash
docker-compose -f docker-compose.prod.yml ps
# NAME               SERVICE       STATUS
# earn-postgres       postgres      Up (healthy)
# earn-redis          redis         Up (healthy)
# earn-yield-api      yield-api     Up (healthy)
# earn-prometheus     prometheus    Up (healthy)
# earn-grafana        grafana       Up
# earn-alertmanager   alertmanager  Up (healthy)
# earn-cadvisor       cadvisor      Up
# earn-db-backup      db-backup     Up
```

---

## 💡 Рекомендації

### Для щоденної роботи:

1. **Використовуйте Docker Desktop** - найзручніший інтерфейс
2. **Створіть aliases** - швидкий доступ до команд
3. **Моніторьте логи** - перевіряйте помилки

### Для розробки:

1. **Hot reload режим** - `docker-compose up yield-api`
2. **LazyDocker** - красивий термінальний інтерфейс
3. **VSCode Docker extension** - інтеграція з редактором

**Успішної роботи з Docker! 🐳**

### Варіанти налаштування PostgreSQL через MCP

1. Стандартне підключення через MCP PostgreSQL

   "postgres": {
   "command": "npx",
   "args": [
   "-y",
   "@modelcontextprotocol/server-postgres",
   "postgresql://yield_user:yield_secure_password_2024@localhost:5432/yield_db"
   ]
   }

2. Підключення через Docker MCP Toolkit

   "postgres-docker": {
   "command": "docker",
   "args": [
   "run",
   "-i",
   "--rm",
   "--network=host",
   "mcp/postgres",
   "postgresql://yield_user:yield_secure_password_2024@host.docker.internal:5432/yield_db"
   ]
   }
