# 🔧 Виправлення помилки Dockerfile для Railway

**Дата:** 2025-11-28  
**Проблема:** Помилка при розгортанні проекту на Railway з GitHub Repo

---

## ❌ Помилка

```
ERROR: failed to build: failed to solve: failed to compute cache key: 
failed to calculate checksum of ref 87gl9nwzm8gsra72yp6h6lhh1::p42vardevw0l1okn3mv7j5yz5: 
"/yield-data-service/bot": not found
```

**Місце помилки:**
```dockerfile
COPY yield-data-service/bot /app/bot
```

---

## 🔍 Причина

Dockerfile намагався скопіювати директорію `yield-data-service/bot`, яка **не існує** в проекті.

**Реальна структура проекту:**
```
EarnAggregator/
├── yield-data-service/
│   └── app/              # ✅ Існує - для yield-api
├── yield-telegram-bot/
│   └── bot/              # ✅ Існує - для telegram-bot
└── Dockerfile
```

**Помилковий шлях в Dockerfile:**
- ❌ `yield-data-service/bot` - не існує
- ✅ `yield-telegram-bot/bot` - правильний шлях

---

## ✅ Рішення

Виправлено Dockerfile, змінивши шлях копіювання:

**Було:**
```dockerfile
# Копіюємо код проекту
# Структура проекту:
# - yield-data-service/app/ -> /app/app/
# - yield-data-service/bot/ -> /app/bot/
COPY yield-data-service/app /app/app
COPY yield-data-service/bot /app/bot  # ❌ Помилка
```

**Стало:**
```dockerfile
# Копіюємо код проекту
# Структура проекту:
# - yield-data-service/app/ -> /app/app/ (для yield-api)
# - yield-telegram-bot/bot/ -> /app/bot/ (для telegram-bot)
COPY yield-data-service/app /app/app
COPY yield-telegram-bot/bot /app/bot  # ✅ Виправлено
```

---

## 📋 Зміни в Dockerfile

**Файл:** `Dockerfile`  
**Рядок 57:** Змінено шлях копіювання

```diff
- COPY yield-data-service/bot /app/bot
+ COPY yield-telegram-bot/bot /app/bot
```

---

## ✅ Перевірка

Після виправлення Dockerfile повинен успішно:

1. ✅ Скопіювати `yield-data-service/app` → `/app/app` (для yield-api)
2. ✅ Скопіювати `yield-telegram-bot/bot` → `/app/bot` (для telegram-bot)
3. ✅ Запустити сервіс залежно від `SERVICE_NAME`:
   - `yield-api` → `python -m uvicorn app.main:app`
   - `telegram-bot` → `python -m bot.main`

---

## 🚀 Наступні кроки

1. ✅ Виправлено Dockerfile
2. ⏳ Закомітити зміни в GitHub
3. ⏳ Railway автоматично перезбере образ після push

---

## 📝 Примітки

- Dockerfile є **універсальним** і підтримує обидва сервіси через змінну `SERVICE_NAME`
- Обидві директорії копіюються в образ, але використовується тільки одна залежно від `SERVICE_NAME`
- Це дозволяє використовувати один Dockerfile для обох сервісів на Railway

---

**Останнє оновлення:** 2025-11-28

