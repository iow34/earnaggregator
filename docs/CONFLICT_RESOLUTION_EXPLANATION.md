# 🔀 Пояснення конфліктів та їх вирішення

## 📊 Аналіз конфліктів у вашому проекті

### Причина конфліктів

Конфлікти виникли тому, що:
1. **Обидві гілки (staging та main) були змінені одночасно**
2. **Зміни торкалися одних і тих же рядків коду**
3. **Git не міг автоматично визначити, яку версію залишити**

---

## 🔍 Детальний аналіз кожного конфлікту

### Конфлікт 1: Docstring (порожній конфлікт)

**Що сталося:**
```
<<<<<<< staging
=======
>>>>>>> main
```

**Причина:** Порожній конфлікт - обидві гілки мали однаковий docstring.

**Рішення:** Залишити docstring без змін.

---

### Конфлікт 2: FastAPI description

**Що було:**
```python
<<<<<<< staging
    description="API для агрегації даних про Yield продукти з криптовалютних бірж",
=======
    description="API для отримання даних про Earn продукти з криптобірж",
>>>>>>> main
```

**Аналіз:**
- **Staging:** "агрегації даних про Yield продукти" - більш точний опис
- **Main:** "отримання даних про Earn продукти" - менш точний

**Рішення:** Використати версію з staging, бо:
- "агрегації" точніше описує функцію (збір з різних джерел)
- "Yield продукти" - правильна термінологія

**Результат:**
```python
    description="API для агрегації даних про Yield продукти з криптовалютних бірж",
```

---

### Конфлікт 3: Root endpoint (`/`)

**Що було:**
```python
<<<<<<< staging
        "docs": "/docs",
        "health": "/api/v1/health"
=======
        "version": __version__
>>>>>>> main
```

**Аналіз:**
- **Staging:** Повертає корисні посилання (`docs`, `health`)
- **Main:** Повертає тільки версію

**Рішення:** Об'єднати обидва підходи - додати всі корисні поля.

**Результат:**
```python
    return {
        "name": "EarnAggregator Data Service",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
```

---

### Конфлікт 4: Реєстрація роутерів

**Що було:**
```python
<<<<<<< staging
# Підключаємо роутери
app.include_router(api_router, prefix="/api/v1", tags=["api"])
app.include_router(tracking_router, prefix="/tracking", tags=["tracking"])
app.include_router(redirect_router, prefix="/ref", tags=["redirect"])
=======
@app.get("/api/v1/health")
async def api_health_check():
    # ... код endpoint ...
>>>>>>> main
```

**Аналіз:**
- **Staging:** Додає `prefix="/api/v1"` при реєстрації `api_router`
- **Main:** Не додає prefix, але має додатковий endpoint `/api/v1/health`

**Важливо:** Роутер `api_router` вже має `prefix="/api/v1"` в файлі `routes.py`:
```python
router = APIRouter(prefix="/api/v1", tags=["yield"])
```

**Рішення:** 
1. Не додавати prefix для `api_router` (бо він вже є)
2. Залишити endpoint `/api/v1/health` з main
3. Додати prefix для інших роутерів (tracking, redirect)

**Результат:**
```python
# Підключаємо роутери
# Примітка: api_router вже має prefix="/api/v1" в routes.py, тому не додаємо prefix тут
app.include_router(api_router, tags=["api"])
app.include_router(tracking_router, prefix="/tracking", tags=["tracking"])
app.include_router(redirect_router, prefix="/ref", tags=["redirect"])

# API Health check endpoint (додатковий до основного /health)
@app.get("/api/v1/health")
async def api_health_check():
    # ... код endpoint ...
```

---

## 🛠️ Як вирішувати конфлікти самостійно

### Крок 1: Знайти конфліктні файли

```bash
# Перевірити статус
git status

# Подивитися на конфліктні файли
git diff --name-only --diff-filter=U
```

### Крок 2: Відкрити конфліктний файл

Git позначає конфлікти маркерами:
```
<<<<<<< staging
Код з staging гілки
=======
Код з main гілки
>>>>>>> main
```

### Крок 3: Зрозуміти різницю

**Питання для аналізу:**
1. Що робить код з staging?
2. Що робить код з main?
3. Чи можна об'єднати обидві версії?
4. Яка версія більш актуальна?

### Крок 4: Вирішити конфлікт

**Варіант 1: Прийняти версію з staging**
```python
# Видалити маркери та залишити код з staging
Код з staging гілки
```

**Варіант 2: Прийняти версію з main**
```python
# Видалити маркери та залишити код з main
Код з main гілки
```

**Варіант 3: Об'єднати обидві версії**
```python
# Об'єднати код з обох гілок
Код з staging гілки
+ Код з main гілки (додатковий)
```

### Крок 5: Видалити маркери конфлікту

**Обов'язково видалити:**
- `<<<<<<< staging`
- `=======`
- `>>>>>>> main`

**Якщо залишити маркери** - код не скомпілюється!

### Крок 6: Перевірити синтаксис

```bash
# Перевірити Python синтаксис
python -m py_compile yield-data-service/app/main.py

# Або запустити linter
pylint yield-data-service/app/main.py
```

### Крок 7: Закомітити вирішення

```bash
# Додати вирішені файли
git add yield-data-service/app/main.py

# Закомітити вирішення
git commit -m "fix: вирішено конфлікти між staging та main"
```

---

## 📝 Приклади вирішення конфліктів

### Приклад 1: Простий конфлікт (вибрати одну версію)

**Було:**
```python
<<<<<<< staging
    port = 8000
=======
    port = 8080
>>>>>>> main
```

**Стало (вибрали staging):**
```python
    port = 8000
```

---

### Приклад 2: Об'єднання конфлікту

**Було:**
```python
<<<<<<< staging
    return {
        "status": "ok",
        "version": "1.0"
    }
=======
    return {
        "status": "ok",
        "docs": "/docs"
    }
>>>>>>> main
```

**Стало (об'єднали):**
```python
    return {
        "status": "ok",
        "version": "1.0",
        "docs": "/docs"
    }
```

---

### Приклад 3: Складний конфлікт (різні підходи)

**Було:**
```python
<<<<<<< staging
app.include_router(api_router, prefix="/api/v1")
=======
app.include_router(api_router)
>>>>>>> main
```

**Аналіз:**
- Потрібно перевірити, чи роутер вже має prefix
- Якщо має - не додавати prefix (main правильний)
- Якщо не має - додати prefix (staging правильний)

**Стало (перевірили, що роутер має prefix):**
```python
app.include_router(api_router)  # prefix вже є в роутері
```

---

## ⚠️ Типові помилки

### Помилка 1: Залишити маркери конфлікту

**Неправильно:**
```python
<<<<<<< staging
    port = 8000
=======
    port = 8080
>>>>>>> main
```

**Правильно:**
```python
    port = 8000  # або port = 8080
```

### Помилка 2: Видалити весь код

**Неправильно:**
```python
# Порожньо (видалили весь код)
```

**Правильно:**
```python
    port = 8000  # Залишили одну з версій або об'єднали
```

### Помилка 3: Не перевірити синтаксис

**Неправильно:**
```bash
git add file.py
git commit -m "fix: вирішено конфлікт"
# Не перевірили синтаксис - код не працює
```

**Правильно:**
```bash
python -m py_compile file.py  # Перевірили синтаксис
git add file.py
git commit -m "fix: вирішено конфлікт"
```

---

## 🎯 Стратегія вирішення конфліктів

### 1. Прочитати обидві версії
- Зрозуміти, що змінилося в staging
- Зрозуміти, що змінилося в main

### 2. Визначити правильну версію
- Яка більш актуальна?
- Яка більш правильна технічно?
- Чи можна об'єднати?

### 3. Об'єднати якщо потрібно
- Взяти найкращі частини з обох
- Переконатися, що код логічний

### 4. Перевірити синтаксис
- Запустити компіляцію
- Перевірити linter

### 5. Закомітити
- Додати файл
- Закомітити з описом

---

## 🔧 Корисні команди Git

```bash
# Перевірити конфлікти
git status

# Подивитися деталі конфлікту
git diff

# Прийняти версію з staging для конкретного файлу
git checkout --theirs yield-data-service/app/main.py

# Прийняти версію з main для конкретного файлу
git checkout --ours yield-data-service/app/main.py

# Скасувати merge (якщо щось пішло не так)
git merge --abort

# Продовжити merge після вирішення конфліктів
git add .
git commit
```

---

## 📚 Додаткові ресурси

- [Git Merge Conflicts](https://git-scm.com/docs/git-merge#_how_conflicts_are_presented)
- [Resolving Merge Conflicts](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts)
- [Git Conflict Resolution](https://www.atlassian.com/git/tutorials/using-branches/merge-conflicts)
