# 🚀 EarnAggregator API Documentation

## 📋 Зміст

1. [Огляд API](#огляд-api)
2. [Базові Endpoints](#базові-endpoints)
3. [Yield Products API](#yield-products-api)
4. [Приклади використання](#приклади-використання)
5. [Коди помилок](#коди-помилок)
6. [Rate Limiting](#rate-limiting)

---

## 🔍 Огляд API

**EarnAggregator Data Service** - це REST API для отримання даних про Earn продукти з різних криптобірж.

- **Base URL:** `http://localhost:8000`
- **API Version:** v1
- **Формат:** JSON
- **Аутентифікація:** Поки не потрібна (буде додана пізніше)

---

## 🏠 Базові Endpoints

### **GET /** - Інформація про сервіс

**Опис:** Повертає базову інформацію про EarnAggregator Data Service.

**Приклад запиту:**

```bash
curl http://localhost:8000/
```

**Приклад відповіді:**

```json
{
  "message": "EarnAggregator Data Service",
  "status": "running",
  "version": "1.0.0"
}
```

### **GET /health** - Health Check

**Опис:** Перевіряє стан сервісу.

**Приклад запиту:**

```bash
curl http://localhost:8000/health
```

**Приклад відповіді:**

```json
{
  "status": "healthy",
  "service": "yield-data-service"
}
```

### **GET /api/v1/status** - API Статус

**Опис:** Повертає інформацію про доступні API endpoints.

**Приклад запиту:**

```bash
curl http://localhost:8000/api/v1/status
```

**Приклад відповіді:**

```json
{
  "api_version": "v1",
  "status": "active",
  "endpoints": [
    "/api/v1/yield/{symbol}",
    "/api/v1/top",
    "/api/v1/recommendations/{user_id}"
  ]
}
```

---

## 💰 Yield Products API

### **GET /api/v1/yield/{symbol}** - Earn продукти по символу

**Опис:** Отримує всі доступні Earn продукти для конкретної криптовалюти.

**Параметри:**

- `symbol` (string, required) - Символ криптовалюти (BTC, ETH, USDT, тощо)

**Приклад запиту:**

```bash
curl http://localhost:8000/api/v1/yield/BTC
```

**Приклад відповіді:**

```json
{
  "success": true,
  "data": [
    {
      "product_id": "binance_flexible_BTC_001",
      "exchange": "binance",
      "symbol": "BTC",
      "name": "Bitcoin Flexible Savings",
      "apy": 3.5,
      "min_amount": 0.001,
      "max_amount": 1000.0,
      "lock_period_days": 0,
      "product_type": "Flexible",
      "category": "FlexibleSaving",
      "is_active": true,
      "is_cefi": true,
      "created_at": "2024-10-16T17:00:00Z",
      "updated_at": "2024-10-16T19:00:00Z"
    }
  ],
  "count": 1,
  "cached": true,
  "timestamp": "2024-10-16T19:00:00Z"
}
```

### **GET /api/v1/top** - Топ Earn продукти

**Опис:** Повертає найкращі Earn продукти за APY.

**Параметри:**

- `limit` (integer, optional) - Кількість результатів (за замовчуванням: 20, максимум: 100)

**Приклад запиту:**

```bash
curl http://localhost:8000/api/v1/top?limit=10
```

**Приклад відповіді:**

```json
{
  "success": true,
  "data": [
    {
      "product_id": "bybit_fixed_ETH_001",
      "exchange": "bybit",
      "symbol": "ETH",
      "name": "Ethereum Fixed Savings (30 days)",
      "apy": 8.5,
      "min_amount": 0.1,
      "max_amount": 500.0,
      "lock_period_days": 30,
      "product_type": "Fixed",
      "category": "FlexibleSaving",
      "is_active": true,
      "is_cefi": true
    }
  ],
  "count": 10,
  "cached": true,
  "timestamp": "2024-10-16T19:00:00Z"
}
```

### **GET /api/v1/recommendations/{user_id}** - Персоналізовані рекомендації

**Опис:** Повертає персоналізовані рекомендації на основі історії запитів користувача.

**Параметри:**

- `user_id` (integer, required) - ID користувача Telegram

**Приклад запиту:**

```bash
curl http://localhost:8000/api/v1/recommendations/123456789
```

**Приклад відповіді:**

```json
{
  "success": true,
  "data": [
    {
      "product_id": "binance_flexible_BTC_001",
      "exchange": "binance",
      "symbol": "BTC",
      "name": "Bitcoin Flexible Savings",
      "apy": 3.5,
      "recommendation_score": 0.95,
      "reason": "Based on your frequent BTC queries"
    }
  ],
  "count": 5,
  "cached": false,
  "timestamp": "2024-10-16T19:00:00Z"
}
```

---

## 📖 Приклади використання

### **JavaScript (Fetch API)**

```javascript
// Отримати Earn продукти для Bitcoin
async function getBitcoinYields() {
  try {
    const response = await fetch("http://localhost:8000/api/v1/yield/BTC");
    const data = await response.json();
    console.log("Bitcoin Earn продукти:", data);
  } catch (error) {
    console.error("Помилка:", error);
  }
}

// Отримати топ-10 найкращих пропозицій
async function getTopYields() {
  try {
    const response = await fetch("http://localhost:8000/api/v1/top?limit=10");
    const data = await response.json();
    console.log("Топ Earn продукти:", data);
  } catch (error) {
    console.error("Помилка:", error);
  }
}
```

### **Python (requests)**

```python
import requests

# Отримати Earn продукти для Ethereum
def get_ethereum_yields():
    response = requests.get('http://localhost:8000/api/v1/yield/ETH')
    if response.status_code == 200:
        data = response.json()
        print(f"Знайдено {data['count']} Ethereum Earn продуктів")
        for product in data['data']:
            print(f"- {product['name']}: {product['apy']}% APY")
    else:
        print(f"Помилка: {response.status_code}")

# Отримати рекомендації для користувача
def get_user_recommendations(user_id):
    response = requests.get(f'http://localhost:8000/api/v1/recommendations/{user_id}')
    if response.status_code == 200:
        data = response.json()
        print(f"Рекомендації для користувача {user_id}:")
        for product in data['data']:
            print(f"- {product['name']}: {product['apy']}% APY (Score: {product['recommendation_score']})")
```

### **cURL приклади**

```bash
# Перевірити стан сервісу
curl -X GET http://localhost:8000/health

# Отримати всі Earn продукти для USDT
curl -X GET http://localhost:8000/api/v1/yield/USDT

# Отримати топ-5 найкращих пропозицій
curl -X GET "http://localhost:8000/api/v1/top?limit=5"

# Отримати рекомендації для користувача
curl -X GET http://localhost:8000/api/v1/recommendations/123456789
```

---

## ❌ Коди помилок

| Код     | Опис                  | Приклад                                                               |
| ------- | --------------------- | --------------------------------------------------------------------- |
| **200** | Успішний запит        | `{"success": true, "data": [...]}`                                    |
| **400** | Неправильні параметри | `{"success": false, "error": "Invalid symbol format"}`                |
| **404** | Дані не знайдено      | `{"success": false, "error": "No products found for BTC"}`            |
| **503** | Сервіс недоступний    | `{"success": false, "error": "Exchange API temporarily unavailable"}` |

**Приклад помилки:**

```json
{
  "success": false,
  "error": "Invalid symbol format",
  "details": "Symbol must be 2-10 characters long and contain only letters",
  "timestamp": "2024-10-16T19:00:00Z"
}
```

---

## ⚡ Rate Limiting

**Поточні обмеження:**

- **100 запитів/хвилину** на IP адресу
- **1000 запитів/день** на користувача (коли буде додана аутентифікація)

**Заголовки відповіді:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

**При перевищенні ліміту:**

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "details": "Too many requests. Try again in 60 seconds.",
  "retry_after": 60
}
```

---

## 🔗 Корисні посилання

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

---

**Створено:** 16.10.2024  
**Версія:** 1.0  
**Статус:** ✅ Активна документація
