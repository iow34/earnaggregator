# Керування версійністю проекту EarnAggregator

## Огляд

Версійність проекту керується через централізований файл `VERSION` в корені проекту. Поточна версія: **1.0.0**

## Структура версійності

### Файли версійності

1. **`VERSION`** (корінь проекту)
   - Основний файл з версією проекту
   - Формат: `MAJOR.MINOR.PATCH` (наприклад, `1.0.0`)
   - Простий текстовий файл з однією строкою

2. **`yield-data-service/app/__version__.py`**
   - Python модуль для імпорту версії в коді
   - Автоматично читає версію з `VERSION` файлу
   - Надає функцію `get_version()` та змінну `__version__`

## Використання версії в коді

### Імпорт версії

```python
from app.__version__ import __version__

# Використання
app = FastAPI(version=__version__)
```

### Де використовується версія

1. **FastAPI додаток** (`yield-data-service/app/main.py`)
   - Метадані API (Swagger/OpenAPI)
   - Автоматично відображається в `/docs`

2. **API endpoints**
   - `GET /` - кореневий endpoint
   - `GET /api/v1/health` - health check
   - Всі відповіді з інформацією про версію

3. **Pydantic моделі** (`yield-data-service/app/models/response.py`)
   - `HealthResponse` - містить версію сервісу

## Семантичне версіонування (SemVer)

Проект використовує [Semantic Versioning 2.0.0](https://semver.org/):

**Формат:** `MAJOR.MINOR.PATCH`

- **MAJOR** (1.x.x) - зміни, що ламають сумісність API
- **MINOR** (x.1.x) - нові функції, зворотно сумісні
- **PATCH** (x.x.1) - виправлення помилок, зворотно сумісні

### Приклади

- `1.0.0` → `1.0.1` - виправлення багів
- `1.0.1` → `1.1.0` - додано нову функцію (наприклад, нову біржу)
- `1.1.0` → `2.0.0` - зміни, що ламають сумісність (наприклад, зміна формату API)

## Оновлення версії

### Крок 1: Оновити файл VERSION

```bash
# Відкрити файл
nano VERSION

# Змінити версію (наприклад, з 1.0.0 на 1.0.1)
1.0.1
```

### Крок 2: Перезапустити сервіс

```bash
docker-compose restart yield-api
```

### Крок 3: Перевірити версію

```bash
curl http://localhost:8000/
# Відповідь містить нову версію
```

## Автоматичне оновлення версії

Версія автоматично читається з `VERSION` файлу при:
- Запуску FastAPI додатку
- Імпорті модуля `app.__version__`
- Створенні Pydantic моделей з версією

**Не потрібно** вручну оновлювати версію в коді - достатньо змінити файл `VERSION`.

## Git теги для версій

Рекомендується створювати Git теги для кожного релізу:

```bash
# Створити тег для версії
git tag -a v1.0.0 -m "Release version 1.0.0"

# Пуш тегів
git push origin v1.0.0
```

## CI/CD інтеграція

Версія може використовуватися в CI/CD пайплайнах:

```yaml
# Приклад для GitHub Actions
- name: Get version
  run: |
    VERSION=$(cat VERSION)
    echo "VERSION=$VERSION" >> $GITHUB_ENV
```

## Перевірка версії в runtime

### Через API

```bash
# Отримати версію через кореневий endpoint
curl http://localhost:8000/

# Отримати версію через health check
curl http://localhost:8000/api/v1/health
```

### Через Python код

```python
from app.__version__ import get_version, __version__

# Використання функції
version = get_version()

# Використання змінної
print(f"Current version: {__version__}")
```

## Відображення версії

Версія відображається в:

1. **Swagger UI** (`/docs`)
   - В заголовку API документації
   - В OpenAPI схемі

2. **API відповідях**
   - `GET /` - `{"version": "1.0.0"}`
   - `GET /api/v1/health` - `{"version": "1.0.0"}`

3. **Логах** (опціонально)
   - Можна додати версію в стартові логи

## Рекомендації

1. **Оновлюйте версію** перед кожним релізом
2. **Створюйте Git теги** для відстеження версій
3. **Документуйте зміни** в CHANGELOG.md для кожної версії
4. **Використовуйте SemVer** для зрозумілості змін
5. **Не комітьте** зміни версії без реальних змін в коді

## Приклад workflow оновлення версії

```bash
# 1. Зробити зміни в коді
git checkout -b feature/new-feature

# 2. Після завершення feature, оновити версію
echo "1.1.0" > VERSION

# 3. Закомітити зміни
git add VERSION
git commit -m "chore: bump version to 1.1.0"

# 4. Створити тег
git tag -a v1.1.0 -m "Release version 1.1.0"

# 5. Пуш змін та тегів
git push origin feature/new-feature
git push origin v1.1.0
```
<<<<<<< HEAD

=======
>>>>>>> 838651ea112ede6673d9ce4f82e973a4b448a2f6
