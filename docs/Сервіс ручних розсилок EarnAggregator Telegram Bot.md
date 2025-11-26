Сервіс ручних розсилок - це безпечна, масштабована система для відправки повідомлень користувачам Telegram-бота з можливістю сегментації, планування та моніторингу. Підтримує текст, HTML, фото, документи з inline-клавіатурами.

🔧 Архітектура
Broadcast Admin API (порт 8081): REST API для керування розсилками
Broadcast Worker: окремий процес для відправки повідомлень через Telegram API
Redis Queue: асинхронна черга для надійної доставки
PostgreSQL: зберігання користувачів, розсилок, логів та аудит

⚡ Ключові особливості
✅ Сегментація аудиторії: фільтри за мовою, тегами, активністю, telegram_id
✅ Планування: відправка в заданий час
✅ Схвалення: обов'язкове підтвердження великих розсилок
✅ Retry policy: автоматичні повторні спроби при помилках
✅ Rate limiting: захист від блокування Telegram API
✅ Моніторинг: Prometheus метрики, логи всіх дій

**Крок 1: Запуск системи**
Через Docker Compose (рекомендовано)

# Запуск всіх сервісів

docker compose -f docker-compose.yml up -d

# Перевірка стану

docker compose ps

# Логи сервісів

docker compose logs broadcast-admin
docker compose logs broadcast-worker

**Важливо: Конфігурація змінних середовища**
Створіть файл .env у корені проекту з обов'язковими змінними:

# База даних

DATABASE_URL=postgresql+asyncpg://earn:password@postgres:5432/earn_db

# Redis

REDIS_URL=redis://redis:6379/1

# Telegram Bot

BOT_TOKEN=your_bot_token_here

# Broadcast Admin

BROADCAST_ADMIN_API_KEY=super_secret_admin_key_64_chars
BROADCAST_ADMIN_BASE_URL=http://localhost:8081

# Broadcast налаштування

BROADCAST_QUEUE_NAME=broadcasts
BROADCAST_RATE_DELAY=0.1
BROADCAST_RETRY_BASE_DELAY=1.0
BROADCAST_RETRY_MAX_DELAY=300.0
BROADCAST_SCHEDULER_INTERVAL=60

**Міграція бази даних**

# Запуск міграцій

docker compose exec telegram-bot alembic upgrade head

**Крок 2: Створення адміністраторів**
Додавання першого адміністратора

# Підключитися до БД контейнера

docker compose exec postgres psql -U earn -d earn_db

# SQL для створення адміністратора

INSERT INTO admin_users (email, password_hash, role, api_key, is_active)
VALUES (
'admin@example.com',
'$2b$12$hashed_password_here', -- згенерувати через passlib
'owner',
'super_secret_admin_key_64_chars',
true
);

Генерація API ключа

# Python скрипт для генерації ключа

import secrets
print(secrets.token_hex(32)) # 64 символи

**Крок 3: Використання через API**

http://localhost:8081

Заголовки для всіх запитів

Content-Type: application/json
x-admin-api-key: your_super_secret_key

**Створення розсилки**
POST /broadcasts

curl -X POST http://localhost:8081/broadcasts \
 -H "Content-Type: application/json" \
 -H "x-admin-api-key: your_key" \
 -d '{
"title": "Щотижневий дайджест",
"content_type": "text",
"content": {
"text": "Привіт! Новий тиждень розпочався з цікавими новинами...",
"parse_mode": "HTML"
},
"filters": {
"is_subscribed": true,
"languages": ["ua"],
"tags_all": ["premium"]
},
"channel": "web_ui",
"requires_approval": false,
"batch_size": 100
}'

Відповідь:

{
"broadcast_id": 123,
"status": "queued",
"total_recipients": 1500
}

Перевірка статусу
GET /broadcasts/{id}/status

curl -H "x-admin-api-key: your_key" \
 http://localhost:8081/broadcasts/123/status

Відповідь:

{
"broadcast_id": 123,
"status": "running",
"scheduled_at": null,
"started_at": "2025-11-24T10:00:00Z",
"completed_at": null,
"total_recipients": 1500,
"recipients": {
"sent": 1450,
"failed": 23,
"pending": 27
}
}

Скасування розсилки
POST /broadcasts/{id}/cancel

curl -X POST -H "x-admin-api-key: your_key" \
 http://localhost:8081/broadcasts/123/cancel

Повторення провалених повідомлень
POST /broadcasts/{id}/retry

curl -X POST -H "x-admin-api-key: your_key" \
 http://localhost:8081/broadcasts/123/retry

Попередній перегляд
POST /broadcasts/preview

curl -X POST http://localhost:8081/broadcasts/preview \
 -H "Content-Type: application/json" \
 -H "x-admin-api-key: your_key" \
 -d '{
"preview_chat_id": 123456789,
"content_type": "text",
"content": {
"text": "Тестове повідомлення",
"parse_mode": "HTML"
}
}'

Схвалення розсилки (якщо потрібне)
POST /broadcasts/{id}/approve

curl -X POST -H "x-admin-api-key: your_key" \
 http://localhost:8081/broadcasts/123/approve

**Крок 4: Використання через CLI**
Шлях до CLI скрипта

cd yield-telegram-bot
python -m bot.broadcasts.cli --help

Базова команда

python -m bot.broadcasts.cli \
 --title "Тестова розсилка" \
 --text "Привіт всім користувачам!" \
 --languages "ua,en" \
 --tags "premium" \
 --api-key "your_admin_key"

Розширені опції

python -m bot.broadcasts.cli \
 --title "Запланована розсилка" \
 --text "<b>Важлива новина!</b> Деталі на сайті..." \
 --content-type "html" \
 --languages "ua" \
 --telegram-ids "123456789,987654321" \
 --preview-chat-id "111111111" \
 --scheduled-at "2025-11-24T15:00:00" \
 --requires-approval \
 --api-key "your_key" \
 --base-url "http://localhost:8081"

Перевірка статусу через CLI

# Використовуємо curl або створюємо окремий CLI для цього

curl -H "x-admin-api-key: your_key" \
 http://localhost:8081/broadcasts/123/status | jq

**Крок 5: Моніторинг та управління**

Prometheus метрики
http://localhost:8001/metrics

Ключові метрики:
broadcast_messages_total: загальна кількість відправлених повідомлень
broadcast_failures_total: кількість помилок доставки
broadcast_queue_depth: розмір черги
broadcast_in_progress: кількість активних розсилок

Логи сервісів

# Логи admin API

docker compose logs -f broadcast-admin

# Логи worker процеса

docker compose logs -f broadcast-worker

# Логи бота

docker compose logs -f telegram-bot

Перевірка черги Redis

docker compose exec redis redis-cli LLEN broadcasts
docker compose exec redis redis-cli LRANGE broadcasts 0 -1

**Веб-інтерфейс Broadcast Admin Web**

1. `cd broadcast-admin-web && npm install`
2. `npm run dev` → http://localhost:5173
3. Введіть `x-admin-api-key` (з `.env`) на екрані авторизації.
4. **Dashboard** – метрики (active / scheduled / sent / failed), останні розсилки (оновлення 10с).
5. **Broadcasts** – таблиця з пагінацією, фільтр за статусом, кнопка переходу в detail.
6. **Detail** – статус/статистика/контент, авто-оновлення поки розсилка не завершена.
7. **Create** – форма для текстових повідомлень (title, HTML message, languages, ids, schedule, approval).

**Docker запуск веб-UI**

```bash
# .env
VITE_BROADCAST_API_URL=http://localhost:8081
BROADCAST_WEB_PORT=4173

docker compose up --build broadcast-web
```

У prod-білді фронтенд доступний на http://localhost:4173 (Nginx, SPA fallback).

**Приклади використання**
Приклад 1: Швидка розсилка всім українським користувачам

curl -X POST http://localhost:8081/broadcasts \
 -H "Content-Type: application/json" \
 -H "x-admin-api-key: your_key" \
 -d '{
"title": "Швидке оголошення",
"content_type": "text",
"content": {"text": "Система буде недоступна 10 хвилин для обслуговування"},
"filters": {"languages": ["ua"]},
"batch_size": 200
}'

Приклад 2: Планування розсилки з HTML та кнопками

curl -X POST http://localhost:8081/broadcasts \
 -H "Content-Type: application/json" \
 -H "x-admin-api-key: your_key" \
 -d '{
"title": "Преміум новина",
"content_type": "html",
"content": {
"text": "<b>🎉 Нова функція!</b>\nТепер доступний аналіз портфеля...",
"buttons": [
{"text": "Дізнатись більше", "url": "https://example.com/premium"}
]
},
"filters": {
"tags_all": ["premium"],
"is_subscribed": true
},
"scheduled_at": "2025-11-24T09:00:00Z",
"requires_approval": true
}'

Приклад 3: Розсилка конкретним користувачам

python -m bot.broadcasts.cli \
 --title "Особисте повідомлення" \
 --text "Дякуємо за участь у бета-тестуванні!" \
 --telegram-ids "123456789,987654321,555666777" \
 --api-key "your_key"

Приклад 4: Розсилка з фото

curl -X POST http://localhost:8081/broadcasts \
 -H "Content-Type: application/json" \
 -H "x-admin-api-key: your_key" \
 -d '{
"title": "Графік доходів",
"content_type": "photo",
"content": {
"media_file_id": "AgACAgIAAxkBAAIBBm...",
"text": "Ваш портфель за місяць 📈"
},
"filters": {"tags_any": ["investor", "trader"]},
"preview_chat_id": 123456789
}'

Рекомендації по сегментації

{
"filters": {
"is_subscribed": true, // тільки активні підписники
"languages": ["ua", "en"], // кілька мов
"tags_all": ["premium"], // всі теги обов'язкові
"tags_any": ["vip", "gold"], // хоча б один тег
"last_active_after": "2025-11-01T00:00:00Z" // активні останні місяці
}
}

Моніторинг продуктивності

Batch size: 50-200 повідомлень оптимально
Rate delay: 0.1-0.5 сек між повідомленнями
Великі розсилки: завжди з requires_approval: true
Монітор метрик: broadcast_failures_total не повинен зростати

**Troubleshooting**
Worker не запускається

# Перевірити логи

docker compose logs broadcast-worker

# Перевірити підключення до Redis

docker compose exec broadcast-worker redis-cli ping

Повідомлення не надсилаються

# Статус розсилки

curl http://localhost:8081/broadcasts/123/status

# Логи помилок

docker compose logs telegram-bot | grep ERROR

## 🌐 Веб-інтерфейс (Web UI)

**URL:** http://localhost:4173

### Доступ

1. Відкрити http://localhost:4173 у браузері
2. Ввести API Key при першому вході:

```
f64a5ba2ef81d1d97c4e6f915fc00c45a791ce07376f1d9db55591c9c213ef90
```

3. API Key зберігається в `localStorage` браузера

### Сторінки

#### Dashboard

- Загальна статистика (total broadcasts, active, scheduled, failed)
- Список останніх 5 розсилок
- Швидкі посилання на створення нової розсилки

#### Broadcasts (список)

- Таблиця всіх розсилок з фільтрами
- Пагінація (20 items per page)
- Фільтри за статусом: all, queued, running, completed, cancelled, failed
- Кнопки дій: View Details, Cancel, Retry

#### Broadcast Detail (деталі розсилки)

**Таби:**

1. **Overview** - загальна інформація
   - Title, Status, Author, Created/Started/Completed dates
   - Content (text, parse_mode, buttons)
   - Filters (languages, telegram_ids, tags)
2. **Recipients** - список отримувачів

   - Telegram ID, Language, Status, Attempts, Message ID
   - Фільтр за статусом: all, sent, failed, pending, skipped
   - Пагінація (50 per page)

3. **Events** - історія подій (audit log)
   - Event type (created, queued, started, completed, cancelled, approved)
   - Admin user, Payload, Timestamp
   - Пагінація (25 per page)

**Дії:**

- **Cancel** - скасування активної розсилки
- **Retry** - повтор failed/skipped recipients
- **Approve** - схвалення (тільки для owner, якщо requires_approval)
- **Send Preview** - тестова відправка на вказаний telegram_id

#### Create Broadcast (створення)

**Форма:**

```typescript
{
  title: string; // Назва розсилки
  message: string; // Текст повідомлення (HTML)
  languages: string; // Мови (comma-separated): "ua,en,ru"
  telegram_ids: string; // ID користувачів (опціонально)
  scheduled_at: string; // Дата/час запуску (ISO 8601)
  requires_approval: boolean; // Потрібне схвалення (для owner)
}
```

**Приклад:**

1. Title: `Новини платформи`
2. Message: `<b>Увага!</b> Нові монети додано до платформи 🎉`
3. Languages: `ua,en`
4. Telegram IDs: (залишити порожнім для всіх)
5. Scheduled At: `2025-11-25T10:00` (опціонально)
6. Requires Approval: ☑ (якщо потрібно схвалення)

**Результат:**

- Успішне створення → редірект на Broadcast Detail page
- Помилка → toast notification з описом проблеми

### Технічні деталі

#### API через Nginx Proxy

Всі API запити йдуть через Nginx proxy на шляху `/api/*`:

```
Browser → http://localhost:4173/api/broadcasts
         ↓
       Nginx (earn-broadcast-web)
         ↓
       http://broadcast-admin:8081/broadcasts
```

**Переваги:**

- ✅ Same-Origin Policy (немає CORS проблем)
- ✅ Один порт для всього (4173)
- ✅ Централізоване логування
- ✅ Можливість додати rate limiting та SSL

#### Auto-refresh

- Dashboard та Broadcast Detail: оновлення кожні 5 секунд (для активних розсилок)
- React Query кешує дані та автоматично інвалідує при мутаціях

#### Type Safety

Всі запити типізовані через TypeScript:

```typescript
interface CreateBroadcastPayload {
  title: string;
  content_type: "text" | "markdown" | "html";
  content: { text: string; parse_mode: "HTML" | "Markdown" };
  filters: { languages?: string[]; telegram_ids?: number[] };
  requires_approval?: boolean;
  scheduled_at?: string | null;
}
```

### Налаштування для розробки

**Локальна розробка (без Docker):**

1. Створити `.env.local` в `broadcast-admin-web/`:

```bash
VITE_BROADCAST_API_URL=http://localhost:8081
```

2. Запустити dev server:

```bash
cd broadcast-admin-web
npm install
npm run dev
```

3. Відкрити http://localhost:5173

**Production (Docker):**

- Використовується `/api` proxy автоматично
- Не потрібно задавати `VITE_BROADCAST_API_URL`

### Додаткова документація

- `docs/BROADCAST_WEB_REQUIREMENTS.md` - вимоги до веб-інтерфейсу
- `docs/BROADCAST_WEB_NETWORK_FIX.md` - виправлення Network Error
- `docs/BROADCAST_WEB_AUDIT_REPORT.md` - звіт про аудит реалізації
