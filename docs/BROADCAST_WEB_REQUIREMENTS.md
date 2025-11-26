# Broadcast Admin Web — Вимоги та API

## 1. Сценарії адміністраторів
- **Огляд активних розсилок**: статус, автор, канал, запланований час, кількість одержувачів.
- **Моніторинг прогресу**: графік/таблиця «відправлено / failed / pending», перегляд логів подій.
- **Створення розсилки**: конструктор контенту (text / HTML / media + inline-кнопки), сегменти аудиторії, планування, вимога approval.
- **Попередній перегляд / тест**: надсилання тестового повідомлення на контрольний chat_id.
- **Адміністрування**: скасування, повторний запуск, approval, зміна batch size до запуску.
- **Історія та аудит**: пошук за датою, автором, тегами, завантаження списку отримувачів з результатом.

Документи-джерела: `docs/Сервіс ручних розсилок EarnAggregator Telegram Bot.md`, `docs/BROADCAST_SERVICE_SETUP_REPORT.md`, ТЗ у `docs/ТЗ/...`.

## 2. Існуючий REST API
| Endpoint | Опис | Статус |
|----------|------|--------|
| `POST /broadcasts` | створення розсилки | ✅ |
| `GET /broadcasts/{id}/status` | агрегований статус | ✅ |
| `POST /broadcasts/{id}/cancel` | скасування | ✅ |
| `POST /broadcasts/{id}/retry` | повтор | ✅ |
| `POST /broadcasts/{id}/approve` | approval (owner) | ✅ |
| `POST /broadcasts/preview` | тестове повідомлення | ✅ |

## 3. Прогалини для веб-інтерфейсу
1. **Список розсилок**  
   - `GET /broadcasts?status=&author=&page=` — коротка інформація + пагінація.  
2. **Деталі розсилки**  
   - `GET /broadcasts/{id}` — контент, фільтри, таймінги, налаштування.  
   - `GET /broadcasts/{id}/events` — audit log.  
   - `GET /broadcasts/{id}/recipients?status=&page=` — список отримувачів (message_id, attempts, error_code).  
3. **Статистика для dashboard**  
   - `GET /metrics/summary` або використати Prometheus proxy (active, scheduled, failed today, avg send rate).  
4. **CORS / Authentication**  
   - Додати CORS у `bot/admin_app.py`, whitelist для веб-домена.  
   - Механізм керування API key у фронтенді (локальне зберігання, можливість re-enter).  
5. **Health/info endpoints**  
   - `GET /admin/info` — версія, налаштування, список ролей (опціонально).  

## 4. Дані, потрібні фронтенду

### 4.1 DTO списку розсилок
```json
{
  "id": 12,
  "title": "Weekly digest",
  "status": "running",
  "channel": "web_ui",
  "total_recipients": 1800,
  "sent": 950,
  "failed": 12,
  "scheduled_at": "2025-11-25T09:00:00Z",
  "started_at": "2025-11-25T09:00:10Z",
  "requires_approval": false,
  "author": {
    "id": 3,
    "email": "admin@example.com",
    "role": "operator"
  }
}
```

### 4.2 DTO деталей
```json
{
  "broadcast": { ... },
  "content": {
    "type": "html",
    "text": "<b>Hello</b>",
    "media": null,
    "buttons": [{ "text": "Open", "url": "https://..." }]
  },
  "filters": {
    "languages": ["en", "ua"],
    "tags_all": ["premium"],
    "tags_any": ["vip"],
    "telegram_ids": [],
    "is_subscribed": true,
    "last_active_after": "2025-10-01T00:00:00Z"
  },
  "stats": {
    "sent": 1200,
    "failed": 34,
    "pending": 566
  }
}
```

### 4.3 DTO отримувачів
```json
{
  "items": [
    {
      "telegram_id": 974695210,
      "language": "ru",
      "status": "sent",
      "message_id": "3041",
      "attempts": 1,
      "last_attempt_at": "2025-11-24T20:56:13.293Z",
      "error_code": null
    }
  ],
  "page": 1,
  "per_page": 50,
  "total": 1500
}
```

## 5. Критерії нефункціональних вимог
- **Latency**: 95-й перцентиль < 500 мс для GET endpoints, < 1.5 c для POST /broadcasts з валідацією.
- **Security**: API key only, HTTPS за проксі, можливе додавання SSO / JWT у майбутньому.
- **Observability**: логування запитів у FastAPI, client-side error tracking (Sentry).
- **Localization**: інтерфейс англійською, готовність до i18n.

## 6. Артефакти для наступних етапів
- Специфікація API (OpenAPI оновлення) після додавання GET endpointів.
- Wireframes для 5 ключових сторінок (figma/креслення).
- Тестові сценарії (happy path + edge cases) перед розробкою UI.


