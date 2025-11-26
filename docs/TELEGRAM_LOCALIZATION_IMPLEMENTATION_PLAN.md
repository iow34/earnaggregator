# План Реалізації Мультимовності в Telegram Боті EarnAggregator

**Дата створення:** 22 листопада 2025 р.  
**Версія:** 1.0  
**Автор:** AI Assistant

## 📋 Загальна Інформація

### Мета Документу

Цей документ містить детальний план імплементації системи локалізації для Telegram бота EarnAggregator. Визначено всі тексти, що потребують перекладу, та файли, які потрібно створити або модифікувати.

### Підтримувані Мови

- 🇺🇦 **Українська (ua)** - мова за замовчуванням
- 🇷🇺 **Російська (ru)** - додаткова мова
- 🇬🇧 **English (en)** - міжнародна мова

### Статистика Проекту

- **200+ текстів** для перекладу на 3 мови = **600+ перекладів загалом**
- **30+ файлів** локалізації (JSON + txt файли)
- **15+ модулів** коду потребують модифікації
- **2500+ рядків** нового коду

---

## 📁 Структура Файлів Локалізації

### 1. Централізовані Файли Текстів (JSON)

#### 1.1 bot/localization/texts/ui.json

**Мета:** Основні елементи інтерфейсу користувача

| Ключ                        | Українська                     | Російська                               | English                         | Контекст використання |
| --------------------------- | ------------------------------ | --------------------------------------- | ------------------------------- | --------------------- |
| `menu.main.welcome`         | 👋 Вітаємо в ChainAdvisor Bot! | 👋 Добро пожаловать в ChainAdvisor Bot! | 👋 Welcome to ChainAdvisor Bot! | start.py:119          |
| `menu.main.language`        | 🌐 Language                        | 🌐 Language                                 | 🌐 Language                     | keyboards/reply.py    |
| `menu.main.exchanges`       | 🏦 Exchanges                       | 🏦 Exchanges                                | 🏦 Exchanges                    | keyboards/reply.py    |
| `menu.main.recommendations` | 🎯 Recommendations                | 🎯 Recommendations                         | 🎯 Recommendations              | keyboards/reply.py    |
| `menu.main.help`            | ❓ Help                     | ❓ Help                              | ❓ Help                         | keyboards/reply.py    |
| `menu.main.placeholder`     | Оберіть дію з меню             | Выберите действие из меню               | Select an action from the menu  | keyboards/reply.py    |
| `menu.back_to_main`         | ⬅️ На головну                  | ⬅️ На главную                           | ⬅️ Back to Main                 | Всі файли             |
| `menu.advanced_search`      | 🔍 Розширений пошук            | 🔍 Расширенный поиск                    | 🔍 Advanced Search              | main_menu.py          |
| `menu.filter`               | 🔍 Фільтр                      | 🔍 Фильтр                               | 🔍 Filter                       | keyboards/inline.py   |
| `menu.reset`                | ♻️ Скинути                     | ♻️ Сбросить                             | ♻️ Reset                        | main_menu.py          |

#### 1.2 bot/localization/texts/messages.json

**Мета:** Системні повідомлення та сповіщення

| Ключ                        | Українська                                            | Російська                                       | English                                            | Контекст використання |
| --------------------------- | ----------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------- | --------------------- |
| `loading.main_menu`         | 🔄 Завантаження головного меню, зачекайте...          | 🔄 Загрузка главного меню, подождите...         | 🔄 Loading main menu, please wait...               | start.py:52           |
| `loading.products`          | 🔄 Завантаження продуктів...                          | 🔄 Загрузка продуктов...                        | 🔄 Loading products...                             | exchange_products.py  |
| `loading.exchanges`         | 🔄 Завантаження списку бірж...                        | 🔄 Загрузка списка бирж...                      | 🔄 Loading exchanges list...                       | main_menu.py          |
| `loading.search`            | 🔍 Виконую пошук...                                   | 🔍 Выполняю поиск...                            | 🔍 Searching...                                    | main_menu.py          |
| `success.language_selected` | ✅ Мову змінено на {language}                         | ✅ Язык изменен на {language}                   | ✅ Language changed to {language}                  | language.py           |
| `success.product_selected`  | ✅ Обрано продукт: {product}                          | ✅ Выбран продукт: {product}                    | ✅ Product selected: {product}                     | main_menu.py          |
| `error.general`             | ❌ Сталася помилка. Спробуйте пізніше.                | ❌ Произошла ошибка. Попробуйте позже.          | ❌ An error occurred. Please try again later.      | Всі файли             |
| `error.loading_products`    | ❌ Помилка завантаження продуктів. Спробуйте пізніше. | ❌ Ошибка загрузки продуктов. Попробуйте позже. | ❌ Error loading products. Please try again later. | exchange_products.py  |
| `error.showing_help`        | ❌ Сталася помилка при показі довідки.                | ❌ Произошла ошибка при показе справки.         | ❌ Error displaying help.                          | help.py               |

#### 1.3 bot/localization/texts/errors.json

**Мета:** Повідомлення про помилки

| Ключ                           | Українська                           | Російська                              | English                           | Контекст використання |
| ------------------------------ | ------------------------------------ | -------------------------------------- | --------------------------------- | --------------------- |
| `error.api_unavailable`        | ⚠️ API тимчасово недоступний         | ⚠️ API временно недоступен             | ⚠️ API temporarily unavailable    | main_menu.py          |
| `error.data_unavailable`       | 📭 Дані тимчасово недоступні         | 📭 Данные временно недоступны          | 📭 Data temporarily unavailable   | main_menu.py          |
| `error.system_unavailable`     | ⚠️ Система тимчасово недоступна      | ⚠️ Система временно недоступна         | ⚠️ System temporarily unavailable | main_menu.py          |
| `error.empty_page`             | 📭 Ця сторінка порожня               | 📭 Эта страница пуста                  | 📭 This page is empty             | main_menu.py          |
| `error.nothing_found`          | 📭 Нічого не знайдено                | 📭 Ничего не найдено                   | 📭 Nothing found                  | filtered_products.py  |
| `error.try_different_criteria` | 💡 Спробуйте змінити критерії пошуку | 💡 Попробуйте изменить критерии поиска | 💡 Try changing search criteria   | filtered_products.py  |
| `error.invalid_product`        | ❌ Некоректний символ продукту       | ❌ Некорректный символ продукта        | ❌ Invalid product symbol         | main_menu.py          |

#### 1.4 bot/localization/texts/navigation.json

**Мета:** Навігаційні елементи та кнопки

| Ключ                    | Українська            | Російська             | English           | Контекст використання |
| ----------------------- | --------------------- | --------------------- | ----------------- | --------------------- |
| `nav.back_to_list`      | ⬅️ Назад до списку    | ⬅️ Назад к списку     | ⬅️ Back to List   | recommendations.py    |
| `nav.to_main`           | 🏠 На головну         | 🏠 На главную         | 🏠 To Main        | recommendations.py    |
| `nav.previous`          | ⬅️ Попередня          | ⬅️ Предыдущая         | ⬅️ Previous       | main_menu.py          |
| `nav.next`              | Наступна ➡️           | Следующая ➡️          | Next ➡️           | main_menu.py          |
| `nav.show_all_products` | Показати всі продукти | Показать все продукты | Show All Products | main_menu.py          |
| `nav.visit`             | перейти ↗️            | перейти ↗️            | visit ↗️          | main_menu.py          |
| `nav.page`              | сторінка              | страница              | page              | main_menu.py          |
| `nav.of`                | з                     | из                    | of                | main_menu.py          |
| `nav.exchanges`         | бірж                  | бирж                  | exchanges         | main_menu.py          |

#### 1.5 bot/localization/texts/tables.json

**Мета:** Заголовки та елементи таблиць

| Ключ                     | Українська                           | Російська                             | English                           | Контекст використання |
| ------------------------ | ------------------------------------ | ------------------------------------- | --------------------------------- | --------------------- |
| `table.header.number`    | №                                    | №                                     | №                                 | formatters.py         |
| `table.header.product`   | Продукт                              | Продукт                               | Product                           | formatters.py         |
| `table.header.exchange`  | Біржа                                | Биржа                                 | Exchange                          | formatters.py         |
| `table.header.apy`       | APY                                  | APY                                   | APY                               | formatters.py         |
| `table.header.type`      | Тип                                  | Тип                                   | Type                              | formatters.py         |
| `table.header.period`    | Період                               | Период                                | Period                            | formatters.py         |
| `table.product.flexible` | Flexible                             | Flexible                              | Flexible                          | formatters.py         |
| `table.product.locked`   | Locked                               | Locked                                | Locked                            | formatters.py         |
| `table.period.flexible`  | —                                    | —                                     | —                                 | formatters.py         |
| `table.empty`            | 📭 Немає продуктів для відображення  | 📭 Нет продуктов для отображения      | 📭 No products to display         | formatters.py         |
| `table.results.found`    | Знайдено {count} продуктів           | Найдено {count} продуктов             | Found {count} products            | formatters.py         |
| `table.results.shown`    | Показано {shown} з {total} продуктів | Показано {shown} из {total} продуктов | Shown {shown} of {total} products | formatters.py         |

#### 1.6 bot/localization/texts/search.json

**Мета:** Елементи пошуку та фільтрів

| Ключ                    | Українська                                          | Російська                                          | English                                     | Контекст використання |
| ----------------------- | --------------------------------------------------- | -------------------------------------------------- | ------------------------------------------- | --------------------- |
| `search.title`          | 🔍 Розширений пошук                                 | 🔍 Расширенный поиск                               | 🔍 Advanced Search                          | main_menu.py          |
| `search.product.label`  | 🪙 Продукт                                          | 🪙 Продукт                                         | 🪙 Product                                  | main_menu.py          |
| `search.product.all`    | Всі продукти                                        | Все продукты                                       | All Products                                | main_menu.py          |
| `search.exchange.label` | 🏦 Біржа                                            | 🏦 Биржа                                           | 🏦 Exchange                                 | main_menu.py          |
| `search.exchange.all`   | Всі біржі                                           | Все биржи                                          | All Exchanges                               | main_menu.py          |
| `search.type.label`     | ⚡ Тип                                              | ⚡ Тип                                             | ⚡ Type                                     | main_menu.py          |
| `search.type.all`       | Всі типи                                            | Все типы                                           | All Types                                   | main_menu.py          |
| `search.button.search`  | 🔍 Пошук                                            | 🔍 Поиск                                           | 🔍 Search                                   | main_menu.py          |
| `search.button.reset`   | ♻️ Скинути                                          | ♻️ Сбросить                                        | ♻️ Reset                                    | main_menu.py          |
| `search.manual_input`   | 🪙 Введення продукту вручну                         | 🪙 Ручной ввод продукта                            | 🪙 Manual Product Input                     | main_menu.py          |
| `search.manual_prompt`  | Введіть символ продукту (наприклад: BTC, ETH, SOL): | Введите символ продукта (например: BTC, ETH, SOL): | Enter product symbol (e.g.: BTC, ETH, SOL): | main_menu.py          |

#### 1.7 bot/localization/texts/sections.json

**Мета:** Заголовки секцій та блоків контенту

| Ключ                         | Українська                                             | Російська                                        | English                                    | Контекст використання |
| ---------------------------- | ------------------------------------------------------ | ------------------------------------------------ | ------------------------------------------ | --------------------- |
| `section.main_title`         | 💰 Crypto Earn Products                                | 💰 Крипто Earn Продукты                          | 💰 Crypto Earn Products                    | main_menu.py          |
| `section.trending_top`       | 🚀 TOP 10 trending products                            | 🚀 ТОП 10 трендовых продуктов                    | 🚀 TOP 10 trending products                | main_menu.py          |
| `section.exchanges_overview` | 🏦 Огляд по біржам                                     | 🏦 Обзор по биржам                               | 🏦 Exchanges Overview                      | main_menu.py          |
| `section.exchanges_list`     | 🏦 Всі біржі                                           | 🏦 Все биржи                                     | 🏦 All Exchanges                           | main_menu.py          |
| `section.recommendations`    | 🎯 Рекомендації по Earn продуктам                      | 🎯 Рекомендации по Earn продуктам                | 🎯 Earn Product Recommendations            | recommendations.py    |
| `section.available_rec`      | 📚 Доступні рекомендації                               | 📚 Доступные рекомендации                        | 📚 Available Recommendations               | recommendations.py    |
| `section.hint`               | 💡 Натисніть на біржу або використовуйте команди нижче | 💡 Нажмите на биржу или используйте команды ниже | 💡 Click on exchange or use commands below | main_menu.py          |

#### 1.8 bot/localization/texts/language.json

**Мета:** Тексти для вибору мови

| Ключ                      | Українська                         | Російська                      | English                      | Контекст використання |
| ------------------------- | ---------------------------------- | ------------------------------ | ---------------------------- | --------------------- |
| `language.title`          | 🌐 Вибір мови інтерфейсу           | 🌐 Выбор языка интерфейса      | 🌐 Language Selection        | language.py           |
| `language.current`        | Поточна мова: {language}           | Текущий язык: {language}       | Current language: {language} | language.py           |
| `language.select_prompt`  | Оберіть мову інтерфейсу:           | Выберите язык интерфейса:      | Select interface language:   | language.py           |
| `language.ua_name`        | 🇺🇦 Українська                      | 🇺🇦 Українська                  | 🇺🇦 Ukrainian                 | language.py           |
| `language.ru_name`        | 🇷🇺 Русский                         | 🇷🇺 Русский                     | 🇷🇺 Russian                   | language.py           |
| `language.en_name`        | 🇬🇧 English                         | 🇬🇧 English                     | 🇬🇧 English                   | language.py           |
| `language.ua_description` | Українська мова (за замовчуванням) | Украинский язык (по умолчанию) | Ukrainian language (default) | language.py           |
| `language.ru_description` | Русский язык                       | Русский язык                   | Russian language             | language.py           |
| `language.en_description` | English language                   | Английский язык                | English language             | language.py           |
| `language.changed`        | ✅ Мову змінено!                   | ✅ Язык изменен!               | ✅ Language changed!         | language.py           |

### 2. Статичні Текстові Файли (TXT)

#### 2.1 Help Тексти

**Шлях:** bot/content/help/{lang}/help.txt

| Мова | Статус               | Розмір | Опис                        |
| ---- | -------------------- | ------ | --------------------------- |
| ua   | ✅ Готово            | ~3KB   | Повний посібник українською |
| ru   | ❌ Потрібно створити | ~3KB   | Повний посібник російською  |
| en   | ❌ Потрібно створити | ~3KB   | Complete guide in English   |

**Зміст для перекладу (основні секції):**

- Заголовок та вступ
- Функції головного меню
- Опис кнопок та команд
- Підтримувані криптовалюти та біржі
- Корисні поради
- Застереження

### 3. Модифіковані Файли Коду

#### 3.1 Core Локалізації

**bot/localization/manager.py** (Новий файл)

```python
class LocalizationManager:
    """Централізований менеджер локалізації"""

    def __init__(self):
        self._cache = {}
        self._load_texts()

    def get_text(self, key: str, lang: str = "ua") -> str:
        """Отримати текст за ключем з fallback"""
        # Логіка отримання тексту

    def get_menu_text(self, key: str, lang: str = "ua") -> str:
        """Отримати текст меню"""
        # Логіка для меню

    def get_error_text(self, key: str, lang: str = "ua") -> str:
        """Отримати текст помилки"""
        # Логіка для помилок
```

**bot/localization/**init**.py** (Новий файл)

```python
from .manager import LocalizationManager

# Глобальний екземпляр
localization = LocalizationManager()

__all__ = ['localization']
```

#### 3.2 Модифіковані Хендлери

**handlers/language.py**

- Додати повну реалізацію замість заглушки
- FSM для вибору мови
- Збереження вибору в БД

**handlers/start.py**

- Отримання мови користувача з БД
- Передача мови до всіх функцій

**handlers/main_menu.py**

- Додати параметр `lang` до всіх функцій
- Замінити hardcoded тексти на локалізовані

**handlers/recommendations.py**

- Локалізація меню рекомендацій
- Підтримка lang параметра

**handlers/help.py**

- Підтримка lang параметра (вже частково є)


#### 3.4 Модифіковані Утиліти

**utils/formatters.py**

- Функції для локалізації таблиць
- Локалізовані заголовки

**utils/logger.py**

- Локалізація повідомлень логування (опціонально)

#### 3.5 Модифіковані Моделі

**db/models.py**

- Додати поле `language` до `TelegramUser`

**db/crud.py**

- Функції для роботи з мовою користувача

### 4. Міграції Бази Даних

#### 4.1 migration_add_user_language.py

```sql
-- Додавання поля мови до таблиці користувачів
ALTER TABLE telegram_users
ADD COLUMN language VARCHAR(2) DEFAULT 'ua' NOT NULL;

-- Індекс для швидкого пошуку
CREATE INDEX idx_telegram_users_language ON telegram_users(language);

-- Коментар до поля
COMMENT ON COLUMN telegram_users.language IS 'Мова інтерфейсу користувача (ua, ru, en)';
```

### 5. Структура Проекту Після Реалізації

```
bot/
├── localization/
│   ├── __init__.py          # Ініціалізація менеджера
│   ├── manager.py           # Основний менеджер локалізації
│   └── texts/
│       ├── ui.json          # Інтерфейсні елементи
│       ├── messages.json    # Системні повідомлення
│       ├── errors.json      # Повідомлення помилок
│       ├── navigation.json  # Навігація
│       ├── tables.json      # Таблиці
│       ├── search.json      # Пошук
│       ├── sections.json    # Секції
│       └── language.json    # Вибір мови
├── content/
│   ├── help/
│   │   ├── ua/help.txt      # ✅ Існує
│   │   ├── ru/help.txt      # ❌ Потрібно створити
│   │   └── en/help.txt      # ❌ Потрібно створити
│   └── recommendations/
│       ├── ua/rec1.txt - rec10.txt  # ✅ Існує
│       ├── ru/rec1.txt - rec10.txt  # ❌ Потрібно створити
│       └── en/rec1.txt - rec10.txt  # ❌ Потрібно створити
├── handlers/
│   ├── language.py          # ✏️ Потрібно модифікувати
│   ├── start.py            # ✏️ Потрібно модифікувати
│   ├── main_menu.py        # ✏️ Потрібно модифікувати
│   └── ...                 # Інші хендлери
├── keyboards/
│   ├── reply.py            # ✏️ Потрібно модифікувати
│   └── inline.py           # ✏️ Потрібно модифікувати
├── utils/
│   └── formatters.py       # ✏️ Потрібно модифікувати
└── db/
    ├── models.py           # ✏️ Потрібно модифікувати
    └── crud.py             # ✏️ Потрібно модифікувати
```

### 6. Детальний Перелік Текстів для Перекладу

#### 6.1 Категорія: Інтерфейс (45 текстів)

| №   | Ключ                      | UA                             | RU                                      | EN                              |
| --- | ------------------------- | ------------------------------ | --------------------------------------- | ------------------------------- |
| 1   | menu.main.welcome         | 👋 Вітаємо в ChainAdvisor Bot! | 👋 Добро пожаловать в ChainAdvisor Bot! | 👋 Welcome to ChainAdvisor Bot! |
| 2   | menu.main.language        | 🌐 Language                        | 🌐 Language                                 | 🌐 Language                     |
| 3   | menu.main.exchanges       | 🏦 Exchanges                       | 🏦 Exchanges                                | 🏦 Exchanges                    |
| 4   | menu.main.recommendations | 🎯 Recommendations                | 🎯 Recommendations                         | 🎯 Recommendations              |
| 5   | menu.main.help            | ❓ Help                     | ❓ Help                              | ❓ Help                         |
| ... | ...                       | ...                            | ...                                     | ...                             |

#### 6.2 Категорія: Повідомлення (35 текстів)

| №   | Ключ              | UA                                           | RU                                      | EN                                   |
| --- | ----------------- | -------------------------------------------- | --------------------------------------- | ------------------------------------ |
| 36  | loading.main_menu | 🔄 Завантаження головного меню, зачекайте... | 🔄 Загрузка главного меню, подождите... | 🔄 Loading main menu, please wait... |
| 37  | loading.products  | 🔄 Завантаження продуктів...                 | 🔄 Загрузка продуктов...                | 🔄 Loading products...               |
| ... | ...               | ...                                          | ...                                     | ...                                  |

#### 6.3 Категорія: Помилки (25 текстів)

| №   | Ключ                  | UA                                     | RU                                     | EN                                            |
| --- | --------------------- | -------------------------------------- | -------------------------------------- | --------------------------------------------- |
| 71  | error.general         | ❌ Сталася помилка. Спробуйте пізніше. | ❌ Произошла ошибка. Попробуйте позже. | ❌ An error occurred. Please try again later. |
| 72  | error.api_unavailable | ⚠️ API тимчасово недоступний           | ⚠️ API временно недоступен             | ⚠️ API temporarily unavailable                |
| ... | ...                   | ...                                    | ...                                    | ...                                           |

#### 6.4 Категорія: Навігація (30 текстів)

| №   | Ключ             | UA                 | RU                | EN              |
| --- | ---------------- | ------------------ | ----------------- | --------------- |
| 96  | nav.back_to_list | ⬅️ Назад до списку | ⬅️ Назад к списку | ⬅️ Back to List |
| 97  | nav.to_main      | 🏠 На головну      | 🏠 На главную     | 🏠 To Main      |
| ... | ...              | ...                | ...               | ...             |

#### 6.5 Категорія: Таблиці (25 текстів)

| №   | Ключ                  | UA      | RU      | EN       |
| --- | --------------------- | ------- | ------- | -------- |
| 126 | table.header.product  | Продукт | Продукт | Product  |
| 127 | table.header.exchange | Біржа   | Биржа   | Exchange |
| ... | ...                   | ...     | ...     | ...      |

#### 6.6 Категорія: Пошук (20 текстів)

| №   | Ключ                 | UA                  | RU                   | EN                 |
| --- | -------------------- | ------------------- | -------------------- | ------------------ |
| 151 | search.title         | 🔍 Розширений пошук | 🔍 Расширенный поиск | 🔍 Advanced Search |
| 152 | search.product.label | 🪙 Продукт          | 🪙 Продукт           | 🪙 Product         |
| ... | ...                  | ...                 | ...                  | ...                |

#### 6.7 Категорія: Секції (10 текстів)

| №   | Ключ                 | UA                          | RU                            | EN                          |
| --- | -------------------- | --------------------------- | ----------------------------- | --------------------------- |
| 171 | section.main_title   | 💰 Crypto Earn Products     | 💰 Крипто Earn Продукты       | 💰 Crypto Earn Products     |
| 172 | section.trending_top | 🚀 TOP 10 trending products | 🚀 ТОП 10 трендовых продуктов | 🚀 TOP 10 trending products |
| ... | ...                  | ...                         | ...                           | ...                         |

#### 6.8 Категорія: Мова (15 текстів)

| №   | Ключ             | UA                       | RU                        | EN                    |
| --- | ---------------- | ------------------------ | ------------------------- | --------------------- |
| 181 | language.title   | 🌐 Вибір мови інтерфейсу | 🌐 Выбор языка интерфейса | 🌐 Language Selection |
| 182 | language.ua_name | 🇺🇦 Українська            | 🇺🇦 Українська             | 🇺🇦 Ukrainian          |
| ... | ...              | ...                      | ...                       | ...                   |

### 7. Перелік 30+ Файлів Локалізації

#### 7.1 JSON Файли (8 файлів)

1. `bot/localization/texts/ui.json` - Інтерфейсні елементи
2. `bot/localization/texts/messages.json` - Системні повідомлення
3. `bot/localization/texts/errors.json` - Повідомлення помилок
4. `bot/localization/texts/navigation.json` - Навігація
5. `bot/localization/texts/tables.json` - Таблиці
6. `bot/localization/texts/search.json` - Пошук
7. `bot/localization/texts/sections.json` - Секції
8. `bot/localization/texts/language.json` - Вибір мови

#### 7.2 TXT Файли Help (3 файли)

9. `bot/content/help/ua/help.txt` - ✅ Існує
10. `bot/content/help/ru/help.txt` - ❌ Потрібно створити
11. `bot/content/help/en/help.txt` - ❌ Потрібно створити

#### 7.3 TXT Файли Recommendations (30 файлів)

12-21. `bot/content/recommendations/ua/rec1.txt` - `rec10.txt` - ✅ Існують
22-31. `bot/content/recommendations/ru/rec1.txt` - `rec10.txt` - ❌ Потрібно створити
32-41. `bot/content/recommendations/en/rec1.txt` - `rec10.txt` - ❌ Потрібно створити

**Загалом: 41 файл** (8 JSON + 3 Help + 30 Recommendations)

### 8. Пріоритет Перекладу

#### 8.1 Критичні Тексти (Priority 1 - 50 текстів)

- Основні елементи інтерфейсу (кнопки меню)
- Системні повідомлення (загрузка, помилки)
- Навігація (назад, далі, головна)

#### 8.2 Важливі Тексти (Priority 2 - 100 текстів)

- Заголовки секцій та таблиць
- Елементи пошуку та фільтрів
- Детальні повідомлення помилок

#### 8.3 Допоміжні Тексти (Priority 3 - 50 текстів)

- Допоміжні підказки
- Розширені описи
- Рідко використовувані повідомлення

### 9. Якість Перекладу

#### 9.1 Вимоги до Перекладів

- **Термінологічна консистентність** - однакові терміни в усіх текстах
- **Граматична правильність** - дотримання правил мови
- **Культурна адаптація** - врахування особливостей цільової аудиторії
- **Технічна точність** - правильне використання крипто-термінів

#### 9.2 Контроль Якості

- **Перевірка носіями мови** - native speakers для кожної мови
- **Тестування в контексті** - перевірка в реальному інтерфейсі
- **Консистентність термінів** - використання глосарію термінів

### 10. Технічні Вимоги

#### 10.1 Формат Файлів

- **JSON файли**: UTF-8, відформатовані з відступами
- **TXT файли**: UTF-8, з емодзі та форматуванням
- **Ключі**: snake_case, ієрархічна структура

#### 10.2 Продуктивність

- **Розмір файлів**: < 50KB на мову
- **Час завантаження**: < 100ms
- **Кешування**: LRU cache для швидкого доступу

#### 10.3 Fallback Стратегія

- **Первинна мова**: українська (ua)
- **Fallback ланцюг**: ua → en → ключ
- **Обробка відсутніх ключів**: логування + повернення ключа

---

## 📊 Підсумкова Статистика

### Тексти для Перекладу

- **200+ унікальних текстів** × **3 мови** = **600+ перекладів**
- **8 категорій** текстів (інтерфейс, повідомлення, помилки, навігація, таблиці, пошук, секції, мова)
- **3 рівні пріоритету** (критичні, важливі, допоміжні)

### Файли Локалізації

- **8 JSON файлів** з структурованими текстами
- **3 TXT файли** довідки
- **30 TXT файлів** рекомендацій
- **Загалом: 41 файл**

### Обсяг Роботи

- **2500+ рядків коду** для імплементації
- **15+ модифікованих файлів** існуючого коду
- **4 тижні** часу розробки
- **3 місяці** підтримки та тестування

---

_Цей план є основою для імплементації повноцінної системи локалізації в Telegram боті EarnAggregator. Для початку роботи рекомендується почати з Priority 1 текстів та core функціональності._
