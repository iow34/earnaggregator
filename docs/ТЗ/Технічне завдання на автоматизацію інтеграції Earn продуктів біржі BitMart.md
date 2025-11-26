# 🔧 Технічне завдання на автоматизацію інтеграції Earn продуктів біржі BitMart в EarnAggregator

## 🏗️ Загальна інформація про інтеграцію

### Мета інтеграції:
- Автоматизувати отримання даних про Earn продукти (Savings) з біржі BitMart через виявлений публічний API ендпоінт.
- Замінити ручний імпорт JSON файлів на автоматичний запит до API з нормалізацією та збереженням в PostgreSQL.
- Забезпечити агрегацію Flexible та Fixed продуктів з нормалізацією до єдиного формату, з акцентом на мінімальний APR для кожного продукту та типу.
- Підтримати монетизацію через реферальні посилання BitMart.
- Інтеграція повинна відповідати загальній архітектурі проекту: модульність, кешування в Redis, зберігання в PostgreSQL, REST API на FastAPI, Telegram бот на Aiogram 3.x.

### Джерела даних:
- Виявлений публічний API ендпоінт: https://www.bitmart.com/gw-api/newearn/summary/earn/product/list.
- Це GET-запит без аутентифікації, який повертає JSON з продуктами.
- Параметри запиту не потрібні для повного списку, але можна додати для фільтрації якщо знадобиться (наприклад, coinName для конкретного символу).

### Вимоги до інтеграції:
- Використовувати тільки виявлений ендпоінт API BitMart.
- Обробляти можливі помилки (наприклад, зміна структури відповіді) з graceful degradation: при помилках використовувати кеш або БД.
- Нормалізувати дані до стандарту EarnAggregator (обов'язкові поля: id, symbol, name, provider, apy, min_amount, max_amount, lock_period_days, product_type, is_active, risk_level).
- Оновлювати дані періодично (наприклад, щогодини) через scheduler.
- Перейти з manual mode на автоматизований, зберігаючи сумісність з існуючим кодом (видалити ручний імпорт після тестування).

---

## 📊 Аналіз API біржі BitMart

### Основні ендпоінти для Earn продуктів:
- **GET /gw-api/newearn/summary/earn/product/list**: Отримання списку Earn продуктів.
  - Базовий URL: https://www.bitmart.com.
  - Параметри запиту: Не обов'язкові, але можна додати для фільтрації (наприклад, coinName для конкретного символу).
  - Відповідь: JSON з data - масив об'єктів за coin (USDT, USDC тощо), з полями coinName, summaryProductList (масив типів з productType (flexible/fixed/stable), addInfo (масив варіантів з productId, annualProfitPec (string), minSubcription (string), lockDay (int), rateType (0/1 для fixed/tiered), tierRules (масив tiers якщо tiered), saleState (1 для активного)).
  - Flexible продукти: productType = "flexible", lockDay = 0.
  - Fixed продукти: productType = "fixed", lockDay > 0.
  - APY: annualProfitPec як string (наприклад, "15.00" для 15%), може бути tiered (залежить від суми) з tierRules.

### Аутентифікація:
- Не потрібна, це публічний ендпоінт (без API key/secret).

### Rate limits та обмеження:
- Не задокументовано, але як публічний — можливі обмеження на IP (рекомендовано 1 запит на хвилину).
- Пагінація: Не потрібна, ендпоінт повертає повний список.

### Формат відповіді та помилки:
- Успішна відповідь: code = 0, msg = "Success", data з масивом продуктів.
- Помилки: code ≠ 0, msg з описом (наприклад, "system error").

---

## ⚠️ Нюанси інтеграції з BitMart API

На основі аналізу документації та обговорень на спеціалізованих форумах (Stack Overflow, GitHub issues для CCXT, Reddit r/BitMart, r/cryptocurrency):

- **Публічний характер ендпоінту**: Це неофіційний internal API, тому ризики змін URL або структури. На GitHub CCXT issues згадується, що BitMart API для торгівлі стабільне, але для Earn рекомендують моніторити відповіді на помилки.
- **Tiered APY**: Якщо rateType=1, APY залежить від суми (tiers в tierRules); форуми радять брати мінімальний pec з tiers для нормалізації.
- **Rate limits**: Не задокументовано, але на Reddit r/BitMart користувачі скаржаться на блокування IP при частих запитах; рекомендують delays (затримки) між запитами.
- **Фільтри та параметри**: Без параметрів для повного списку; saleState=1 для активних. На Stack Overflow відзначають, що addInfo може містити дублікати, ігнорувати.
- **Обробка помилок**: Exponential backoff для помилок 5xx; на GitHub радять fallback до cached даних.
- **Тестування**: Використовувати Postman для симуляції; BitMart не має sandbox для Earn.
- **Інші поради**: На Reddit згадують безпеку: уникати частого scraping, використовувати headers як в браузері (User-Agent).
- **Додатково**: якщо буде помилка з отриманням даних по api використовувати дані отримані в останньому успішному отриманні даних по api.

---

## 📊 Правила нормалізації даних

- **Типи продуктів**:
  - Flexible: Якщо productType = "flexible" та lockDay = 0.
  - Fixed: Якщо productType = "fixed" та lockDay > 0 (lock_period_days = int(lockDay)).
  - Ігнорувати "stable" або інші типи, якщо не FIXED/FLEXIBLE.

- **APY**:
  - Брати мінімальний annualProfitPec як float (парсити string, видалити "%"), з 2-4 знаками.
  - Якщо rateType=1 (tiered), обрати мінімальний pec з tierRules (перший tier або min з масиву).
  - Перетворювати до річного формату.

- **Суми**:
  - min_amount: Парсити minSubcription (string) до float.
  - max_amount: Не вказане, встановити null.

- **Статус**:
  - is_active = True тільки якщо saleState = 1.
  - Ігнорувати неактивні.

- **Ризик**:
  - Low для stablecoins (USDT/USDC), Medium для volatile assets.

- **Інші поля**:
  - id: "bitmart_" + productType + "_" + productId.
  - symbol: coinName.
  - name: coinName + " " + productType.capitalize() + " Savings" (додати lockDay для fixed).
  - provider: "BitMart".
  - description: З labelNameList та earnType.
  - website_url: "https://www.bitmart.com/earn".
  - raw_data: Зберегти повний об'єкт для діагностики.

- **Валідація**: Перевіряти обов'язкові поля; видаляти невалідні продукти; для одного symbol і типу брати тільки один варіант з мінімальним APY (ігнорувати дублікати з вищим APY).

---

## 📁 Структура модулів для BitMart

- Шлях: yield-data-service/app/services/exchanges/bitmart/
  - __init__.py: Імпорти модулів.
  - api.py: API клієнт з методами для earn продуктів.
  - service.py: Бізнес-логіка, кешування, синхронізація з БД.
  - models.py (опціонально): Pydantic моделі для відповідей.

---

## 🚀 Покрокова інструкція інтеграції

### Крок 1: Підготовка
- Ознайомитися з виявленим ендпоінтом та структурою JSON.
- Видалити ручний імпорт після тестування.
- Додати конфігурацію для API URL в config.py.

### Крок 2: Реалізація API клієнта (api.py)
- Успадкувати від BaseExchange (без аутентифікації).
- Методи: get_earn_products (GET без параметрів), get_earn_products_by_asset (додати coinName якщо потрібно).
- Обробити масив data для ітерації по coins.

### Крок 3: Реалізація сервісу (service.py)
- Успадкувати від BaseExchangeService.
- Ініціалізувати API клієнт.
- Методи: get_products_from_api, get_products_with_cache, sync_products_to_db, test_connection, get_health_status.
- Додати retry з exponential backoff.

### Крок 4: Реалізація моделей (models.py) - опціонально
- Моделі для продуктів з полями з JSON.

### Крок 5: Налаштування імпортів (__init__.py)
- Експортувати класи API, Service, моделі.

### Крок 6: Реєстрація біржі в системі
- Оновити aggregation_service.py: DataSource.API_BITMART.
- Оновити registry.py: AVAILABLE_EXCHANGES з "bitmart".
- Оновити routes.py: Валідація для bitmart, provider_mapping = {'bitmart': 'BitMart'}.

### Крок 7: Оновлення конфігурації
- Додати до config.py: bitmart_api_url.
- Оновити docker-compose.yml для environment якщо потрібно.

### Крок 8: Синхронізація з БД (в sync_products_to_db)
1. Отримати дані з API.
2. Фільтрувати активні продукти (saleState=1).
3. Нормалізувати: Для кожного coinName і типу обрати один з мінімальним annualProfitPec.
4. Підготувати UPSERT для БД.
5. Виконати транзакцію з вставкою/оновленням.
6. Обробити помилки з логуванням.
7. Оновити кеш.

---

## 📱 Інтеграція з Telegram ботом

- Оновити provider_mapping: {'bitmart': 'BitMart'}.
- Оновити списки бірж в handlers.
- Додати реферальне посилання до REFERRAL_URLS.
- Бот підтримає /all_bitmart_products, фільтри, сортування.

---

## ✅ Валідація та тестування

- Unit тести: Отримання продуктів, нормалізація (мінімальний APY).
- Інтеграційні: Curl для /api/v1/bitmart/products, /api/v1/bitmart/test.
- Функціональні: Команди в боту.
- БД: SQL на count по provider='BitMart'.

---

## 📊 Моніторинг та підтримка

- Додати метрики для "bitmart".
- Логування: Кількість продуктів, помилки.
- Обробка помилок: Graceful degradation.
- Регулярні завдання: Синхронізація щогодини, моніторинг змін API.

## Приклад json відповіді
 Тобі потрібно вивчити приклад по якому отримуються продукти і записувати в базу даних продукти з мінмальним APY для кожного продукту і кожного типу Flexible або Fixed.

 {
  "code": 0,
  "msg": "Success",
  "data": [
    {
      "coinId": 17,
      "coinName": "USDT",
      "coinFullName": "Tether USD",
      "coinUrl": "/static-file/public/coin/USDT-20200604062641.png",
      "labelNameList": null,
      "availableBalance": "0",
      "summaryProductList": [
        {
          "productId": "635577818569605120",
          "productType": "flexible",
          "earnType": "saving",
          "labelNameList": [
            "HOT",
            "Boost"
          ],
          "addInfo": [
            {
              "id": "635577818569605120",
              "productType": "flexible",
              "earnType": "saving",
              "productName": "USDT Flexible Savings",
              "productCnName": "USDT 活期余币宝",
              "coinId": 17,
              "coinName": "USDT",
              "lockDay": 0,
              "minSubcription": "0",
              "annualProfitPec": "15.00%",
              "interestRate": null,
              "sortWeight": 9975,
              "launchTime": null,
              "saleState": 1,
              "productTags": "[\"HOT\",\"Boost\"]",
              "rateType": 1,
              "tierRules": [
                {
                  "sequence": 0,
                  "start": "0",
                  "end": "200",
                  "pec": "0.15"
                },
                {
                  "sequence": 1,
                  "start": "200",
                  "end": null,
                  "pec": "0.0425"
                }
              ],
              "additionalAnnualProfitPec": "4.25%",
              "additionalDetailLink": "https://www.bitmart.com/en-US/activity/savingxfutures",
              "additionalDescriptionList": [
                {
                  "language": "en-US",
                  "description": "In addition to the interests of the product, you will also be rewarded with Futures Rebate Cards or Futures Trial Funds equal in value to the interests you earned."
                },
                {
                  "language": "zh-CN",
                  "description": "在获得理财产品利息的同时，您还将获得同等价值的合约交易手续费抵扣券或合约体验金！"
                }
              ],
              "priorityDisplay": false,
              "couponsProfitPec": null,
              "orderPrecision": null,
              "profitBigDecimal": "0.1500",
              "coinPriority": 0,
              "tagPriority": 0,
              "earnProductWealth": null,
              "groupId": 0
            }
          ],
          "wealthProduct": null,
          "duration": [
            "flexible"
          ],
          "annualProfitPecMin": "15.00%",
          "annualProfitPecMax": "15.00%"
        },
        {
          "productId": "301841484009091570",
          "productType": "fixed",
          "earnType": "saving",
          "labelNameList": [
            "HOT"
          ],
          "addInfo": [
            {
              "id": "301841484009091570",
              "productType": "fixed",
              "earnType": "saving",
              "productName": "USDT 30D Fixed Savings",
              "productCnName": "USDT 30天 定期余币宝",
              "coinId": 17,
              "coinName": "USDT",
              "lockDay": 30,
              "minSubcription": "10",
              "annualProfitPec": "4.75%",
              "interestRate": null,
              "sortWeight": 9975,
              "launchTime": null,
              "saleState": 1,
              "productTags": "[\"HOT\"]",
              "rateType": 0,
              "tierRules": [],
              "additionalAnnualProfitPec": "",
              "additionalDetailLink": "",
              "additionalDescriptionList": [],
              "priorityDisplay": false,
              "couponsProfitPec": null,
              "orderPrecision": null,
              "profitBigDecimal": "0.0475",
              "coinPriority": 0,
              "tagPriority": 0,
              "earnProductWealth": null,
              "groupId": 0
            },
            {
              "id": "725103614486781952",
              "productType": "fixed",
              "earnType": "saving",
              "productName": "USDT 180D Fixed Savings",
              "productCnName": "USDT 180天 定期余币宝",
              "coinId": 17,
              "coinName": "USDT",
              "lockDay": 180,
              "minSubcription": "10",
              "annualProfitPec": "5.25%",
              "interestRate": null,
              "sortWeight": 9975,
              "launchTime": null,
              "saleState": 1,
              "productTags": "[\"HOT\"]",
              "rateType": 0,
              "tierRules": [],
              "additionalAnnualProfitPec": "",
              "additionalDetailLink": "",
              "additionalDescriptionList": [],
              "priorityDisplay": false,
              "couponsProfitPec": null,
              "orderPrecision": null,
              "profitBigDecimal": "0.0525",
              "coinPriority": 0,
              "tagPriority": 0,
              "earnProductWealth": null,
              "groupId": 0
            }
          ],
          "wealthProduct": null,
          "duration": [
            "fixed"
          ],
          "annualProfitPecMin": "4.75%",
          "annualProfitPecMax": "5.25%"
        },
        {
          "productId": null,
          "productType": "stable",
          "earnType": "wealth",
          "labelNameList": null,
          "addInfo": null,
          "wealthProduct": {
            "id": "434323113216450651",
            "productName": "USDT Fixed Income",
            "productCnName": "USDT 固定收益",
            "coinId": 17,
            "coinName": "USDT",
            "coinFullName": null,
            "coinIcon": null,
            "lockDay": 14,
            "minSubcription": "3000",
            "productType": "stable",
            "annualProfitPec": "5.75%",
            "orderPrecision": null,
            "launchTime": 1761811200000,
            "saleState": 1,
            "startBuyTime": 1761811200000,
            "saleStopTime": 1763020800000,
            "interestStartTime": 1763020800000,
            "interestEndTime": 1764230400000,
            "redeemTime": 1764230400000,
            "reinvestTime": null,
            "availableBalance": null,
            "profitList": [],
            "remainingSubscribeAmount": null,
            "sortWeight": 9999,
            "couponsProfitPec": null,
            "existCouponsInterest": null,
            "couponsInterestList": null
          },
          "duration": null,
          "annualProfitPecMin": null,
          "annualProfitPecMax": null
        }
      ],
      "earnTypeList": [
        "wealth",
        "saving"
      ],
      "duration": [
        "flexible",
        "fixed"
      ],
      "annualProfitPecMin": "4.75%",
      "annualProfitPecMax": "15.00%",
      "plusInterestCoupon": false
    },
    {
      "coinId": 2008,
      "coinName": "USDC",
      "coinFullName": "USDC",
      "coinUrl": "/static-file/public/coin/USDC-20211115040218.png",
      "labelNameList": null,
      "availableBalance": "0",
      "summaryProductList": [
        {
          "productId": "656604651012325376",
          "productType": "flexible",
          "earnType": "saving",
          "labelNameList": [
            "HOT",
            "Boost"
          ],
          "addInfo": [
            {
              "id": "656604651012325376",
              "productType": "flexible",
              "earnType": "saving",
              "productName": "USDC Flexible Savings",
              "productCnName": "USDC 活期余币宝",
              "coinId": 2008,
              "coinName": "USDC",
              "lockDay": 0,
              "minSubcription": "0",
              "annualProfitPec": "15.00%",
              "interestRate": null,
              "sortWeight": 9974,
              "launchTime": null,
              "saleState": 1,
              "productTags": "[\"HOT\",\"Boost\"]",
              "rateType": 1,
              "tierRules": [
                {
                  "sequence": 0,
                  "start": "0",
                  "end": "200",
                  "pec": "0.15"
                },
                {
                  "sequence": 1,
                  "start": "200",
                  "end": null,
                  "pec": "0.0575"
                }
              ],
              "additionalAnnualProfitPec": "",
              "additionalDetailLink": "",
              "additionalDescriptionList": [],
              "priorityDisplay": false,
              "couponsProfitPec": null,
              "orderPrecision": null,
              "profitBigDecimal": "0.1500",
              "coinPriority": 1,
              "tagPriority": 0,
              "earnProductWealth": null,
              "groupId": 0
            }
          ],
          "wealthProduct": null,
          "duration": [
            "flexible"
          ],
          "annualProfitPecMin": "15.00%",
          "annualProfitPecMax": "15.00%"
        }
      ],
      "earnTypeList": [
        "saving"
      ],
      "duration": [
        "flexible"
      ],
      "annualProfitPecMin": "15.00%",
      "annualProfitPecMax": "15.00%",
      "plusInterestCoupon": false
    },
    {
      "coinId": 2,
      "coinName": "BTC",
      "coinFullName": "Bitcoin",
      "coinUrl": "/static-file/public/coin/BTC-20200604060942.png",
      "labelNameList": null,
      "availableBalance": "0",
      "summaryProductList": [
        {
          "productId": "635593620437958656",
          "productType": "flexible",
          "earnType": "saving",
          "labelNameList": [
            "HOT"
          ],
          "addInfo": [
            {
              "id": "635593620437958656",
              "productType": "flexible",
              "earnType": "saving",
              "productName": "BTC Flexible Savings",
              "productCnName": "BTC 活期余币宝",
              "coinId": 2,
              "coinName": "BTC",
              "lockDay": 0,
              "minSubcription": "0",
              "annualProfitPec": "15.00%",
              "interestRate": null,
              "sortWeight": 9973,
              "launchTime": null,
              "saleState": 1,
              "productTags": "[\"HOT\"]",
              "rateType": 1,
              "tierRules": [
                {
                  "sequence": 0,
                  "start": "0",
                  "end": "0.002",
                  "pec": "0.15"
                },
                {
                  "sequence": 1,
                  "start": "0.002",
                  "end": null,
                  "pec": "0.0075"
                }
              ],
              "additionalAnnualProfitPec": "",
              "additionalDetailLink": "",
              "additionalDescriptionList": [],
              "priorityDisplay": false,
              "couponsProfitPec": null,
              "orderPrecision": null,
              "profitBigDecimal": "0.1500",
              "coinPriority": 2,
              "tagPriority": 0,
              "earnProductWealth": null,
              "groupId": 0
            }
          ],
          "wealthProduct": null,
          "duration": [
            "flexible"
          ],
          "annualProfitPecMin": "15.00%",
          "annualProfitPecMax": "15.00%"
        },
        {
          "productId": null,
          "productType": "stable",
          "earnType": "wealth",
          "labelNameList": null,
          "addInfo": null,
          "wealthProduct": {
            "id": "434323877720633635",
            "productName": "BTC Fixed Income",
            "productCnName": "BTC 固定收益",
            "coinId": 2,
            "coinName": "BTC",
            "coinFullName": null,
            "coinIcon": null,
            "lockDay": 14,
            "minSubcription": "0.03",
            "productType": "stable",
            "annualProfitPec": "1.50%",
            "orderPrecision": null,
            "launchTime": 1761811200000,
            "saleState": 1,
            "startBuyTime": 1761811200000,
            "saleStopTime": 1763020800000,
            "interestStartTime": 1763020800000,
            "interestEndTime": 1764230400000,
            "redeemTime": 1764230400000,
            "reinvestTime": null,
            "availableBalance": null,
            "profitList": [],
            "remainingSubscribeAmount": null,
            "sortWeight": 9979,
            "couponsProfitPec": null,
            "existCouponsInterest": null,
            "couponsInterestList": null
          },
          "duration": null,
          "annualProfitPecMin": null,
          "annualProfitPecMax": null
        }
      ],
      "earnTypeList": [
        "wealth",
        "saving"
      ],
      "duration": [
        "flexible",
        "fixed"
      ],
      "annualProfitPecMin": "1.50%",
      "annualProfitPecMax": "15.00%",
      "plusInterestCoupon": false
    }
  ]
}