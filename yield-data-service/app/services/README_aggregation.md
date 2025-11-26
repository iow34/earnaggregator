# Сервіс агрегації - РОЗДІЛ 3.2

## Огляд

Сервіс агрегації (`DataAggregationService`) об'єднує всі компоненти системи в єдину систему для отримання, валідації та обробки даних про yield продукти.

## Основні функції

### 1. Сервіс агрегації - об'єднання даних з бірж

**Стратегії агрегації:**

- `FAST_CACHE_FIRST` - швидкий доступ з пріоритетом кешу
- `COMPREHENSIVE` - повна агрегація з усіх джерел
- `FALLBACK_CHAIN` - ланцюжок fallback при помилках

**Джерела даних:**

- `CACHE` - Redis кеш
- `DATABASE` - PostgreSQL база даних
- `API_BINANCE` - Binance API
- `API_BYBIT` - Bybit API
- `COMBINED` - комбіновані джерела

### 2. Логіка кешування - коли використовувати кеш, коли API

**Пріоритети доступу:**

1. **Кеш** - найшвидший доступ для популярних запитів
2. **БД** - fallback при відсутності в кеші
3. **Live API** - оновлення даних та додавання нових

**Стратегії кешування:**

- Cache-first для швидких відповідей
- Comprehensive для повних даних
- Fallback chain для надійності

### 3. Обробка помилок - graceful degradation

**Рівні обробки помилок:**

- **Рівень 1**: Помилки валідації - пропуск невалідних даних
- **Рівень 2**: Помилки API - fallback до наступного джерела
- **Рівень 3**: Системні помилки - повернення порожніх результатів з логуванням

### 4. Валідація даних - перевірка якості даних

**Критерії валідації:**

- Обов'язкові поля: `symbol`, `provider`, `apy`
- Валідний APY: 0-10000%
- Валідний символ: alphanumeric, 2+ символів
- Фільтрація по провайдеру та мінімальному APY

### 5. Логування операцій - для моніторингу

**Метрики:**

- Кількість продуктів знайдено
- Джерела використані
- Cache hit/miss rate
- Час відповіді
- Оцінка якості даних
- Кількість помилок

## API Endpoints

### Методи сервісу

```python
# Основна агрегація
aggregation_result = await aggregation_service.aggregate_yield_data(
    symbol="BTC",
    limit=50,
    min_apy=5.0,
    provider="binance",
    strategy=AggregationStrategy.FAST_CACHE_FIRST
)

# Статистика для моніторингу
stats = await aggregation_service.get_aggregation_stats()
```

### API Endpoints

**GET `/api/v1/aggregation/stats`**

- Статистика сервісу агрегації
- Метрики cache, джерел, якості даних

**GET `/api/v1/aggregation/test`**

- Тестування роботи агрегації
- Параметри: `symbol`, `strategy`, `limit`

## Використання в існуючих endpoints

### Оновлені endpoints з агрегацією:

**GET `/api/v1/yield/{symbol}`**

- Використовує `FAST_CACHE_FIRST` стратегію
- Інтегрована валідація та обробка помилок

**GET `/api/v1/exchanges?exchange=binance`**

- Використовує `COMPREHENSIVE` стратегію
- Фільтрація по конкретній біржі

## Структура даних

### AggregationResult

```python
@dataclass
class AggregationResult:
    data: List[YieldProduct]              # Результати агрегації
    sources_used: List[DataSource]        # Використані джерела
    cache_hits: int                      # Попадання в кеш
    cache_misses: int                    # Промахи кешу
    api_calls_made: int                  # API виклики
    errors_encountered: List[str]        # Помилки
    total_response_time_ms: float        # Час відповіді
    data_quality_score: float            # Оцінка якості (0-1)
```

## Приклади використання

### Швидке отримання даних

```python
# Запит з кешу першим
result = await aggregation_service.aggregate_yield_data(
    symbol="BTC",
    strategy=AggregationStrategy.FAST_CACHE_FIRST
)
```

### Повна агрегація

```python
# Всі джерела + валідація
result = await aggregation_service.aggregate_yield_data(
    symbol="ETH",
    limit=100,
    strategy=AggregationStrategy.COMPREHENSIVE
)
```

### Fallback ланцюжок

```python
# Надійність при помилках
result = await aggregation_service.aggregate_yield_data(
    symbol="USDT",
    strategy=AggregationStrategy.FALLBACK_CHAIN
)
```

## Моніторинг та логування

### Метрики якості

- **Data Quality Score**: 0.0-1.0 на основі:
  - Кількості знайдених продуктів
  - Cache hit rate
  - Кількості джерел
  - Відсутності помилок

### Логування

- Всі операції логуються з деталями
- Помилки з контекстом та стек-трейсом
- Метрики продуктивності для моніторингу

## Інтеграція з системою

Сервіс агрегації інтегрований в:

- **API routes** - для обробки запитів користувачів
- **Cache system** - для ефективного кешування
- **Database** - для fallback та збереження
- **Exchange APIs** - для live даних

Це забезпечує єдину точку доступу до всіх даних з автоматичною обробкою помилок та оптимальною продуктивністю.
