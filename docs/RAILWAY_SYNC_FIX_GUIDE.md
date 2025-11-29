# 🔧 Інструкція з виправлення проблем синхронізації на Railway

**Дата:** 2025-11-29  
**Статус:** Виправлення застосовано

---

## ✅ Результати перевірки

### Variables на Railway встановлені правильно:

- ✅ `BINANCE_API_KEY`: встановлено та співпадає з .env
- ✅ `BINANCE_API_SECRET`: встановлено та співпадає з .env
- ✅ `BYBIT_API_KEY`: встановлено та співпадає з .env
- ✅ `BYBIT_API_SECRET`: встановлено та співпадає з .env

**Висновок:** Проблема НЕ в налаштуванні Variables на Railway.

---

## 🔴 Виявлені проблеми та виправлення

### Проблема 1: Логіка перевірки конфігурації

**Файл:** `yield-data-service/app/services/exchanges/base_service.py`

**Було:**
```python
def _check_configuration(self) -> bool:
    return bool(self.api_key and self.api_secret)
```

**Стало:**
```python
def _check_configuration(self) -> bool:
    # Для Bybit дозволяємо роботу без ключів (публічний API)
    if self.exchange_name == "bybit":
        return True
    
    # Перевіряємо чи ключі не порожні та не є default значеннями
    default_values = ["your_binance_api_key_here", ...]
    api_key_valid = self.api_key and self.api_key not in default_values
    api_secret_valid = self.api_secret and self.api_secret not in default_values
    return api_key_valid and api_secret_valid
```

**Результат:** Bybit тепер працює без ключів, Binance перевіряє на default значення.

---

### Проблема 2: Обробка помилок Foreign Key

**Файл:** `yield-data-service/app/services/exchanges/base_service.py` (метод `_save_products_to_db`)

**Було:**
```python
try:
    await ExchangeDataCRUD.create_exchange_data(...)
except Exception as exchange_data_error:
    if "unique_product_exchange" in str(exchange_data_error):
        logger.debug(...)
    else:
        logger.warning(...)
```

**Стало:**
```python
# Використовуємо UPSERT для exchange_data
existing_exchange_data = await db.execute(
    select(ExchangeDataDB).where(...)
)
exchange_data_record = existing_exchange_data.scalar_one_or_none()

if exchange_data_record:
    # Оновлюємо існуючий запис
    exchange_data_record.raw_data = ...
    await db.commit()
else:
    # Створюємо новий запис
    await ExchangeDataCRUD.create_exchange_data(...)
```

**Результат:** Тепер використовується UPSERT замість CREATE, що запобігає помилкам duplicate key.

---

### Проблема 3: Відсутність перевірки таблиць

**Додано:** Перевірка існування таблиць перед синхронізацією

```python
# Перевіряємо чи існує таблиця yield_products
result = await db.execute(text("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'yield_products'
    );
"""))
```

**Результат:** Синхронізація не запускається, якщо таблиці не існують.

---

### Проблема 4: Відсутність діагностичного логування

**Додано:** Логування API ключів при ініціалізації

```python
logger.info(f"🔑 {exchange_name} API Key: {self.api_key[:10]}... (довжина: {len(self.api_key)})")
logger.info(f"🔑 {exchange_name} API Secret: {'*' * 10}... (довжина: {len(self.api_secret)})")
```

**Результат:** Можна перевірити чи ключі правильно читаються з Railway.

---

## 📋 Покрокова інструкція виправлення

### Крок 1: Виконати міграції бази даних

```bash
# Через API endpoint
curl -X POST https://earnaggregator-production.up.railway.app/api/v1/migrations/run

# Або через Railway Shell
railway shell
curl -X POST http://localhost:8000/api/v1/migrations/run
```

**Очікуваний результат:**
```json
{
  "status": "completed",
  "total": 4,
  "successful": 4,
  "failed": 0
}
```

### Крок 2: Перевірити що таблиці створені

```bash
railway connect postgres
```

Потім в psql:
```sql
\dt  -- Показати всі таблиці
SELECT COUNT(*) FROM yield_products;
SELECT COUNT(*) FROM exchange_data;
```

### Крок 3: Перезапустити сервіс на Railway

```bash
railway restart --service earnaggregator
```

Або через Railway UI: Deployments → Redeploy

### Крок 4: Перевірити логи при старті

```bash
railway logs --service earnaggregator | grep -i "binance\|bybit\|configured\|API Key"
```

**Очікуваний вивід:**
```
🔑 binance API Key: g5CYWzibxO... (довжина: 64)
🔑 binance API Secret: **********... (довжина: 64)
✅ binance сервіс ініціалізовано з API ключами
🔑 bybit API Key: KT2uv9qtTh... (довжина: 16)
🔑 bybit API Secret: **********... (довжина: 32)
✅ bybit сервіс ініціалізовано з API ключами
```

### Крок 5: Протестувати синхронізацію

```bash
# Binance
curl -X POST https://earnaggregator-production.up.railway.app/api/v1/binance/sync

# Bybit
curl -X POST https://earnaggregator-production.up.railway.app/api/v1/bybit/sync
```

**Очікуваний результат:**
```json
{
  "success": true,
  "status": "success",
  "message": "Синхронізація Binance завершена: 50 створено, 489 оновлено",
  "data": {
    "status": "success",
    "products_count": 539,
    "sync_stats": {
      "created": 50,
      "updated": 489,
      "errors": 0
    }
  }
}
```

---

## 🔍 Діагностика проблем

### Якщо синхронізація все ще не працює:

1. **Перевірити логи:**
   ```bash
   railway logs --service earnaggregator | grep -i "error\|foreign key\|exchange_data"
   ```

2. **Перевірити чи таблиці існують:**
   ```bash
   railway connect postgres
   \dt
   ```

3. **Перевірити чи API ключі читаються:**
   ```bash
   railway logs --service earnaggregator | grep "API Key"
   ```

4. **Перевірити тест підключення:**
   ```bash
   curl https://earnaggregator-production.up.railway.app/api/v1/binance/test
   ```

---

## 📊 Правильне налаштування Variables на Railway

### Для Binance (обов'язково):

| Змінна | Значення | Де встановити |
|--------|----------|---------------|
| `BINANCE_API_KEY` | Ваш Binance API Key | Railway UI → Service → Variables |
| `BINANCE_API_SECRET` | Ваш Binance API Secret | Railway UI → Service → Variables |

**Як отримати:**
1. https://www.binance.com/ → Account → API Management
2. Create API → System generated
3. Увімкнути тільки "Enable Reading"
4. Скопіювати API Key та Secret Key

### Для Bybit (опціонально):

| Змінна | Значення | Де встановити |
|--------|----------|---------------|
| `BYBIT_API_KEY` | Ваш Bybit API Key (або порожній) | Railway UI → Service → Variables |
| `BYBIT_API_SECRET` | Ваш Bybit API Secret (або порожній) | Railway UI → Service → Variables |

**Примітка:** Bybit Earn API публічний, але для сумісності краще встановити ключі.

---

## 🎯 Основні зміни в коді

1. ✅ Покращено перевірку конфігурації (додано перевірку default значень)
2. ✅ Додано підтримку Bybit без API ключів (публічний API)
3. ✅ Покращено обробку помилок Foreign Key (UPSERT замість CREATE)
4. ✅ Додано перевірку існування таблиць перед синхронізацією
5. ✅ Додано діагностичне логування API ключів

---

## 📚 Посилання

- [Railway Environment Variables](https://docs.railway.com/develop/variables)
- [Railway PostgreSQL](https://docs.railway.com/databases/postgresql)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

**Останнє оновлення:** 2025-11-29

