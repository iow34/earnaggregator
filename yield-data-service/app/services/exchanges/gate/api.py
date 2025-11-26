"""
Інтеграція з Gate.io API для отримання Earn продуктів.

Gate.io надає наступні типи Earn продуктів:
- Uni Lend (Flexible Savings) -> GET /api/v4/earn/uni/currencies
- Fixed Savings (через manual JSON import, API не має публічного endpoint)

Особливості Gate.io API:
- HMAC SHA512 підпис (не SHA256 як Binance)
- Unix timestamp в секундах (не мілісекундах)
- Заголовки: KEY, Timestamp, SIGN (без префіксу X-)
"""

from typing import List, Dict, Optional, Any
import hmac
import hashlib
import time
from urllib.parse import urlencode, urljoin

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class GateAPI(BaseExchange):
    """
    Клієнт для роботи з Gate.io API.
    
    Використовує Gate.io API v4 з HMAC SHA512 аутентифікацією.
    """

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://api.gateio.ws/api/v4"
        )

    def get_headers(self) -> Dict[str, str]:
        """
        Заголовки для запитів до Gate.io.
        
        Returns:
            Dict з базовими заголовками
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _generate_signature(
        self,
        method: str,
        path: str,
        query_string: str = "",
        body: str = "",
        timestamp: Optional[int] = None
    ) -> tuple[Dict[str, str], int]:
        """
        Генерує HMAC SHA512 підпис для Gate.io API.
        
        Формула підпису:
        message = method + "\\n" + path + "\\n" + query_string + "\\n" + hex(SHA512(body)) + "\\n" + timestamp
        signature = hex(HMAC_SHA512(message, secret_key))
        
        Args:
            method: HTTP метод у UPPERCASE (GET, POST, DELETE, PATCH)
            path: Шлях запиту без хоста (наприклад: /api/v4/earn/uni/currencies)
            query_string: Параметри без URL-encode (наприклад: page=1&limit=100)
            body: Тіло запиту (для POST/PATCH, порожня строка для GET)
            timestamp: Unix timestamp в секундах (якщо None - генерується автоматично)
            
        Returns:
            Tuple з заголовками аутентифікації та timestamp
        """
        # Генеруємо timestamp якщо не передано
        if timestamp is None:
            timestamp = int(time.time())
        
        # Hash тіла запиту (для GET запитів без body - hash порожньої строки)
        body_hash = hashlib.sha512(body.encode('utf-8')).hexdigest()
        
        # Формуємо message для підпису
        message = f"{method}\n{path}\n{query_string}\n{body_hash}\n{timestamp}"
        
        # Генеруємо підпис HMAC SHA512
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Формуємо заголовки аутентифікації
        auth_headers = {
            "KEY": self.api_key,
            "Timestamp": str(timestamp),
            "SIGN": signature
        }
        
        return auth_headers, timestamp

    async def get_uni_currencies(
        self,
        page: int = 1,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Отримує список валют доступних для Uni Lend (Flexible Savings).

        Endpoint: GET /api/v4/earn/uni/currencies
        Цей endpoint НЕ потребує аутентифікації!

        Args:
            page: Номер сторінки (починається з 1)
            limit: Кількість записів на сторінку (макс 1000)

        Returns:
            List з Uni Lend currencies
        """
        try:
            path = "earn/uni/currencies"
            method = "GET"

            # Формуємо query параметри
            params = {}
            if page > 1:
                params["page"] = page
            if limit != 100:
                params["limit"] = limit

            logger.info(f"[GateAPI] Запит Uni Lend currencies (page={page}, limit={limit})")

            # Цей endpoint НЕ потребує аутентифікації!
            # Виконуємо прямий запит без аутентифікаційних заголовків
            await self._ensure_client()

            url = urljoin(self.base_url + '/', path.lstrip('/'))

            # Використовуємо мінімальні заголовки без аутентифікації
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            logger.debug(f"[GateAPI] {method} {url} params={params}")

            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers
            )

            response.raise_for_status()
            data = response.json()

            # Gate.io API повертає список напряму
            if isinstance(data, list):
                logger.info(f"[GateAPI] Отримано {len(data)} Uni Lend currencies")
                return data

            logger.warning(f"[GateAPI] Неочікувана структура відповіді: {type(data)}")
            return []

        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання Uni Lend currencies: {e}")
            return []

    async def get_uni_rates(self) -> List[Dict[str, Any]]:
        """
        Отримує estimated rates для всіх валют доступних для Uni Lend (Flexible Savings).

        Endpoint: GET /api/v4/earn/uni/rate
        Цей endpoint НЕ потребує аутентифікації!

        Returns:
            List з estimated rates для всіх валют
        """
        try:
            path = "earn/uni/rate"
            method = "GET"

            logger.info(f"[GateAPI] Запит Uni Lend estimated rates")

            # Цей endpoint НЕ потребує аутентифікації!
            # Виконуємо прямий запит без аутентифікаційних заголовків
            await self._ensure_client()

            url = urljoin(self.base_url + '/', path.lstrip('/'))

            # Використовуємо мінімальні заголовки без аутентифікації
            request_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            logger.debug(f"[GateAPI] {method} {url}")

            response = await self.client.request(
                method=method,
                url=url,
                headers=request_headers
            )

            response.raise_for_status()
            data = response.json()

            # Gate.io API повертає список напряму
            if isinstance(data, list):
                logger.info(f"[GateAPI] Отримано {len(data)} Uni Lend estimated rates")
                return data

            logger.warning(f"[GateAPI] Неочікувана структура відповіді: {type(data)}")
            return []

        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання Uni Lend estimated rates: {e}")
            return []

    async def get_uni_currency(self, currency: str) -> Optional[Dict[str, Any]]:
        """
        Отримує детальну інформацію про конкретну Uni Lend currency.
        
        Endpoint: GET /api/v4/earn/uni/currencies/{currency}
        
        Args:
            currency: Назва валюти (BTC, ETH, USDT, etc.)
            
        Returns:
            Dict з деталями currency або None при помилці
        """
        try:
            path = f"/api/v4/earn/uni/currencies/{currency}"
            method = "GET"
            
            # Генеруємо підпис
            auth_headers, timestamp = self._generate_signature(
                method=method,
                path=path,
                query_string="",
                body=""
            )
            
            # Об'єднуємо заголовки
            headers = self.get_headers()
            headers.update(auth_headers)
            
            logger.info(f"[GateAPI] Запит деталей Uni Lend currency: {currency}")
            
            # Виконуємо запит
            data = await self._make_request(
                method=method,
                path=path,
                headers=headers
            )
            
            return data
            
        except Exception as e:
            logger.error(f"[GateAPI] Помилка отримання деталей {currency}: {e}")
            return None

    async def get_flexible_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Отримує Flexible Savings продукти (Uni Lend).

        Метод успадкований від BaseExchange.
        Gate.io називає Flexible Savings як Uni Lend.

        Використовує комбінацію даних:
        - est_rate з /api/v4/earn/uni/rate (для точних APY)
        - min/max amounts з /api/v4/earn/uni/currencies (для лімітів)

        Args:
            asset: Символ активу для фільтрації (опціонально)
            current: Номер сторінки
            size: Розмір сторінки

        Returns:
            List нормалізованих Flexible продуктів
        """
        try:
            logger.info(f"[GateAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''}")

            # Отримуємо estimated rates (правильні APY)
            rates_data = await self.get_uni_rates()

            # Отримуємо currencies дані (мінімальні/максимальні суми)
            currencies_data = await self.get_uni_currencies(page=current, limit=size)

            if not rates_data:
                logger.warning("[GateAPI] Не отримано estimated rates для Flexible продуктів")
                return []

            # Створюємо словник для швидкого пошуку currencies по currency
            currencies_dict = {c.get("currency", ""): c for c in currencies_data}

            # Фільтруємо rates за asset якщо вказано
            if asset:
                rates_data = [r for r in rates_data if r.get("currency", "").upper() == asset.upper()]

            # Нормалізуємо продукти
            products = []
            for item in rates_data:
                try:
                    # Парсинг APY - використовуємо est_rate як основну ставку
                    # Gate.io повертає est_rate у десятковому форматі: 0.0138 = 1.38%
                    est_rate_str = item.get("est_rate", "0")
                    apy = float(est_rate_str) * 100 if est_rate_str else 0.0

                    # Символ валюти
                    currency = item.get("currency", "")

                    # Отримуємо додаткові дані з currencies (якщо доступні)
                    currency_info = currencies_dict.get(currency, {})

                    # Парсинг мінімальної/максимальної суми
                    min_amount_str = currency_info.get("min_lend_amount", "0")
                    min_amount = float(min_amount_str) if min_amount_str else 0.0

                    max_amount_str = currency_info.get("max_lend_amount", "")
                    # Якщо max_lend_amount дуже великий (> 1M), вважаємо необмеженим
                    if max_amount_str and max_amount_str.isdigit():
                        max_amount_val = float(max_amount_str)
                        max_amount = max_amount_val if max_amount_val < 1000000 else None
                    else:
                        max_amount = None

                    # У Gate.io всі валюти в списку вважаються активними,
                    # якщо вони присутні в API відповіді
                    is_active = True

                    # Формуємо нормалізований продукт
                    product = {
                        "id": f"gate_flexible_{currency}",
                        "symbol": currency,
                        "name": f"{currency} Flexible Savings",
                        "provider": "gate",
                        "apy": apy,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                        "lock_period_days": 0,  # Flexible завжди 0
                        "product_type": "Flexible",
                        "is_active": is_active,
                        "risk_level": "Low",
                        "description": f"Gate.io Uni Lend Flexible Savings for {currency}",
                        "website_url": "https://www.gate.com/simple-earn",
                        "raw_data": item
                    }
                    
                    products.append(product)
                    
                except Exception as parse_error:
                    logger.warning(f"[GateAPI] Помилка парсингу продукту {item.get('currency')}: {parse_error}")
                    continue
            
            logger.info(f"[GateAPI] ✅ Нормалізовано {len(products)} Flexible продуктів")
            return products
            
        except Exception as e:
            logger.error(f"[GateAPI] ❌ Помилка отримання Flexible продуктів: {e}")
            return []

    async def get_locked_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Stub метод для Locked Savings продуктів.
        
        Gate.io не має публічного API для Fixed Savings.
        Дані завантажуються вручну через POST /api/v1/gate/import endpoint.
        
        Returns:
            Порожній список (Fixed продукти доступні через manual import)
        """
        logger.info("[GateAPI] Fixed Savings доступні тільки через manual JSON import")
        return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Отримує всі Earn продукти з Gate.io (тільки Flexible через API).
        
        Returns:
            List нормалізованих Earn продуктів
        """
        try:
            logger.info("[GateAPI] Початок отримання всіх Earn продуктів")
            
            # Отримуємо Flexible продукти
            flexible_products = await self.get_flexible_savings_products()
            logger.info(f"[GateAPI] ✅ Отримано {len(flexible_products)} Flexible продуктів")
            
            # Fixed продукти не доступні через API
            # Вони завантажуються через manual import у GateService
            
            # Нормалізуємо продукти
            normalized_products = []
            for product in flexible_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception as norm_error:
                    logger.warning(f"[GateAPI] Помилка нормалізації продукту: {norm_error}")
                    normalized_products.append(product)
            
            logger.info(f"[GateAPI] ✅ Агреговано {len(normalized_products)} Earn продуктів")
            return normalized_products
            
        except Exception as e:
            logger.error(f"[GateAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Отримує Earn продукти для конкретного активу.
        
        Args:
            asset: Символ активу (BTC, ETH, USDT, etc.)
            
        Returns:
            List нормалізованих продуктів для активу
        """
        try:
            logger.info(f"[GateAPI] Запит Earn продуктів для {asset}")
            
            # Отримуємо Flexible продукти з фільтрацією
            flexible_products = await self.get_flexible_savings_products(asset=asset)
            
            # Fixed продукти не доступні через API
            # Фільтрація Fixed продуктів буде в GateService
            
            # Нормалізуємо
            normalized_products = []
            for product in flexible_products:
                try:
                    normalized = self.normalize_earn_product(product)
                    normalized_products.append(normalized)
                except Exception:
                    normalized_products.append(product)
            
            logger.info(f"[GateAPI] Знайдено {len(normalized_products)} продуктів для {asset}")
            return normalized_products
            
        except Exception as e:
            logger.error(f"[GateAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []

