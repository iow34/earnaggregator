"""
Інтеграція з OKX API для отримання Financial Product (Earn продуктів).

OKX використовує специфічну аутентифікацію з 3 параметрами:
- API Key
- API Secret
- API Passphrase (унікальна особливість OKX)

Формат підпису:
    message = timestamp + method + requestPath + body
    signature = base64(HMAC-SHA256(message, secret_key))

Підтримувані продукти:
- On-chain earn (staking/DeFi) - GET /api/v5/finance/staking-defi/offers
- Simple Earn Flexible - GET /api/v5/finance/simple-earn/products (потребує уточнення в docs)
"""

from typing import List, Dict, Optional, Any
import hmac
import hashlib
import base64
import datetime
from urllib.parse import urlencode

from ..base_exchange import BaseExchange
from app.utils.logger import logger
from app.utils.rate_limiter import rate_limiter


class OKXAPI(BaseExchange):
    """
    Клієнт для роботи з OKX Financial Product API.
    
    Особливості:
    - 3 параметри аутентифікації (key + secret + passphrase)
    - Rate limit: 3 req/s для On-chain earn endpoints
    - ISO 8601 timestamp у форматі: 2025-10-29T14:23:45.123Z
    """

    def __init__(self, api_key: str, api_secret: str, api_passphrase: str = ""):
        """
        Ініціалізує OKX API клієнт.

        Args:
            api_key: OKX API ключ
            api_secret: OKX API секрет
            api_passphrase: OKX API passphrase (встановлюється при створенні ключа)
        """
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://www.okx.com"
        )
        self.api_passphrase = api_passphrase
        
        # Ініціалізуємо rate limiter для OKX (3 req/s)
        if not rate_limiter.get_limiter("okx"):
            rate_limiter.create_limiter("okx", max_requests=3, per_seconds=1.0)
        
        logger.info(f"✅ OKXAPI ініціалізовано з URL: {self.base_url}")

    def _generate_timestamp(self) -> str:
        """
        Генерує ISO 8601 timestamp для OKX API.
        
        Формат: 2025-10-29T14:23:45.123Z (з мілісекундами та суфіксом Z)
        
        Returns:
            str: Timestamp у форматі ISO 8601
        """
        now = datetime.datetime.utcnow()
        # Форматуємо з мілісекундами
        timestamp = now.isoformat(timespec='milliseconds') + 'Z'
        return timestamp

    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = ""
    ) -> str:
        """
        Генерує HMAC SHA256 підпис для OKX API.
        
        Формат повідомлення: timestamp + method + requestPath + body
        
        Args:
            timestamp: ISO 8601 timestamp
            method: HTTP метод (GET, POST, тощо)
            request_path: Шлях запиту (наприклад: /api/v5/finance/staking-defi/offers)
            body: Тіло запиту (для POST/PUT)
        
        Returns:
            str: Base64-encoded підпис
        """
        # Формуємо повідомлення для підпису
        message = timestamp + method.upper() + request_path + body
        
        # Генеруємо HMAC SHA256
        mac = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        
        # Кодуємо в base64
        signature = base64.b64encode(mac.digest()).decode('utf-8')
        
        return signature

    def get_headers(
        self,
        method: str = "GET",
        request_path: str = "/",
        body: str = ""
    ) -> Dict[str, str]:
        """
        Генерує заголовки для OKX API запитів з аутентифікацією.
        
        Args:
            method: HTTP метод
            request_path: Шлях запиту
            body: Тіло запиту
        
        Returns:
            Dict[str, str]: Заголовки HTTP запиту
        """
        timestamp = self._generate_timestamp()
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            "Content-Type": "application/json",
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.api_passphrase
        }
        
        # Безпечне логування (не логуємо passphrase та повний підпис)
        logger.debug(
            f"[OKXAPI] Headers generated: "
            f"key={self.api_key[:8]}***, "
            f"timestamp={timestamp}"
        )
        
        return headers

    async def _make_okx_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Виконує запит до OKX API з rate limiting та обробкою помилок.
        
        Args:
            method: HTTP метод
            path: Шлях endpoint
            params: Query параметри
        
        Returns:
            Dict[str, Any]: Розпарсена JSON відповідь
        """
        # Rate limiting
        await rate_limiter.acquire("okx", tokens=1, timeout=10.0)
        
        # Формуємо повний шлях для підпису
        query_string = ""
        if params:
            query_string = "?" + urlencode(params)
        request_path = path + query_string
        
        # Генеруємо заголовки
        headers = self.get_headers(method=method, request_path=request_path)
        
        # Виконуємо запит
        response = await self._make_request(
            method=method,
            path=path,
            params=params,
            headers=headers
        )
        
        return response

    async def get_onchain_earn_products(
        self,
        product_id: Optional[str] = None,
        protocol_type: Optional[str] = None,
        ccy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Отримує On-chain earn продукти (staking/DeFi).
        
        Endpoint: GET /api/v5/finance/staking-defi/offers
        
        Args:
            product_id: Фільтр по конкретному продукту
            protocol_type: Фільтр по типу протоколу (staking, defi_lending)
            ccy: Фільтр по валюті (BTC, ETH, тощо)
        
        Returns:
            List[Dict]: Список нормалізованих продуктів
        """
        try:
            path = "/api/v5/finance/staking-defi/offers"
            params = {}
            
            if product_id:
                params["productId"] = product_id
            if protocol_type:
                params["protocolType"] = protocol_type
            if ccy:
                params["ccy"] = ccy
            
            logger.info(f"[OKXAPI] Запит On-chain earn продуктів: params={params}")
            
            response = await self._make_okx_request("GET", path, params)
            
            # Перевіряємо успішність відповіді
            code = response.get("code", "-1")
            if code != "0":
                error_msg = response.get("msg", "Unknown error")
                logger.error(f"[OKXAPI] Помилка API: code={code}, msg={error_msg}")
                return []
            
            # Отримуємо дані
            data = response.get("data", [])
            if not data:
                logger.info("[OKXAPI] On-chain earn: немає доступних продуктів")
                return []
            
            # Нормалізуємо продукти
            products = []
            for item in data:
                try:
                    product = self._normalize_onchain_product(item)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації On-chain продукту: {e}")
                    continue
            
            logger.info(f"[OKXAPI] ✅ Отримано {len(products)} On-chain earn продуктів")
            return products
            
        except Exception as e:
            logger.warning(f"[OKXAPI] ⚠️ On-chain продукти недоступні (потрібна аутентифікація): {e}")
            logger.info("[OKXAPI] ✅ Повертаємо порожній список On-chain продуктів")
            return []

    def _normalize_onchain_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормалізує On-chain продукт до формату EarnAggregator.
        
        Args:
            item: Сирі дані з OKX API
        
        Returns:
            Dict: Нормалізований продукт
        """
        # Парсимо APY (формат: "0.0395" -> 3.95%)
        apy_raw = item.get("apy", "0")
        try:
            apy = float(apy_raw) * 100  # Конвертуємо в відсотки
        except:
            apy = 0.0
        
        # Парсимо термін блокування
        term = item.get("term", "")
        lock_days = 0
        if term and term.isdigit():
            lock_days = int(term)
        
        # Отримуємо мін/макс суми з investData
        min_amount = 0.0
        max_amount = None
        invest_data = item.get("investData", [])
        if invest_data and len(invest_data) > 0:
            first_invest = invest_data[0]
            try:
                min_amount = float(first_invest.get("minAmt", "0"))
            except:
                min_amount = 0.0
            
            max_amt_str = first_invest.get("maxAmt", "")
            if max_amt_str:
                try:
                    max_amount = float(max_amt_str)
                except:
                    max_amount = None
        
        # Визначаємо активність
        state = item.get("state", "")
        is_active = state.lower() == "purchasable"
        
        # Формуємо ID
        product_id = item.get("productId", "")
        ccy = item.get("ccy", "")

        # Якщо ccy порожнє, витягуємо символ з назви продукту
        if not ccy:
            # Назва продукту має формат "ADA/Cardano Staking" або подібний
            # Витягуємо перше слово до пробілу або слеша
            product_name = item.get("termName", item.get("name", ""))
            if "/" in product_name:
                ccy = product_name.split("/")[0].strip()
            elif " " in product_name:
                ccy = product_name.split(" ")[0].strip()
            else:
                ccy = product_name.strip()

        unified_id = f"okx_onchain_{product_id}"

        # Формуємо назву
        protocol = item.get("protocol", "")
        name = f"{ccy} On-chain Earn ({protocol})" if protocol else f"{ccy} On-chain Earn"
        
        product = {
            "id": unified_id,
            "symbol": ccy,
            "name": name,
            "provider": "OKX",
            "apy": apy,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "lock_period_days": lock_days,
            "product_type": "OnChain",
            "is_active": is_active,
            "risk_level": "Medium",  # On-chain має середній ризик
            "can_early_redeem": item.get("earlyRedeem", False),
            "protocol": protocol,
            "description": f"On-chain staking for {ccy} via {protocol}",
            "website_url": "https://www.okx.com/earn/onchain",
            "raw_data": item
        }
        
        return product

    async def get_simple_earn_flexible_products(
        self,
        ccy: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Отримує Simple Earn Flexible продукти.
        
        Endpoint: GET /api/v5/finance/savings/lending-rate-summary (потрібно уточнити в docs)
        
        Args:
            ccy: Фільтр по валюті
        
        Returns:
            List[Dict]: Список нормалізованих продуктів
        """
        try:
            # ВАЖЛИВО: Точний endpoint потрібно уточнити в офіційній документації OKX
            # Використовуємо lending-rate-summary як найближчий аналог Simple Earn
            path = "/api/v5/finance/savings/lending-rate-summary"
            params = {}
            
            if ccy:
                params["ccy"] = ccy
            
            logger.info(f"[OKXAPI] Запит Simple Earn Flexible продуктів: params={params}")
            
            response = await self._make_okx_request("GET", path, params)
            
            # Перевіряємо успішність
            code = response.get("code", "-1")
            if code != "0":
                error_msg = response.get("msg", "Unknown error")
                logger.warning(f"[OKXAPI] Simple Earn недоступний: code={code}, msg={error_msg}")
                return []
            
            # Отримуємо дані
            data = response.get("data", [])
            if not data:
                logger.info("[OKXAPI] Simple Earn: немає доступних продуктів")
                return []
            
            # Нормалізуємо продукти
            products = []
            for item in data:
                try:
                    product = self._normalize_simple_earn_product(item)
                    products.append(product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації Simple Earn продукту: {e}")
                    continue
            
            logger.info(f"[OKXAPI] ✅ Отримано {len(products)} Simple Earn продуктів")
            return products
            
        except Exception as e:
            logger.error(f"[OKXAPI] ❌ Помилка отримання Simple Earn продуктів: {e}", exc_info=True)
            return []

    def _normalize_simple_earn_product(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормалізує Simple Earn продукт до формату EarnAggregator.
        
        Args:
            item: Сирі дані з OKX API
        
        Returns:
            Dict: Нормалізований продукт
        """
        # Парсимо APY (OKX повертає десяткові значення, наприклад "0.01" = 1%)
        # Пріоритет: estRate -> avgRate -> preRate -> rate
        rate_raw = (item.get("estRate") or
                   item.get("avgRate") or
                   item.get("preRate") or
                   item.get("rate") or "0")
        try:
            apy = float(rate_raw) * 100  # Конвертуємо в відсотки
        except:
            apy = 0.0
        
        # Парсимо мін/макс суми
        try:
            min_amt_str = item.get("minAmt", "0")
            min_amount = float(min_amt_str) if min_amt_str else 0.0
        except:
            min_amount = 0.0
        
        max_amt_str = item.get("maxAmt", "")
        max_amount = None
        if max_amt_str:
            try:
                max_amount = float(max_amt_str)
            except:
                max_amount = None
        
        # Визначаємо активність
        # OKX Simple Earn продукти вважаємо активними, якщо вони приходять з API
        is_active = True
        
        # Формуємо ID та назву
        ccy = item.get("ccy", "")
        unified_id = f"okx_simple_flex_{ccy}"
        name = f"{ccy} Simple Earn Flexible"
        
        product = {
            "id": unified_id,
            "symbol": ccy,
            "name": name,
            "provider": "OKX",
            "apy": apy,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "lock_period_days": 0,  # Flexible завжди 0
            "product_type": "SimpleFlexible",
            "is_active": is_active,
            "risk_level": "Low",  # Simple Earn має низький ризик
            "can_early_redeem": True,  # Flexible завжди можна вивести
            "description": f"Simple Earn flexible savings for {ccy}",
            "website_url": "https://www.okx.com/earn/savings",
            "raw_data": item
        }
        
        return product

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Агрегує всі Earn продукти з OKX (On-chain + Simple Earn).
        
        Returns:
            List[Dict]: Список всіх нормалізованих продуктів
        """
        all_products = []
        
        try:
            logger.info("[OKXAPI] Початок агрегації всіх Earn продуктів")
            
            # Отримуємо On-chain продукти
            onchain_products = await self.get_onchain_earn_products()
            all_products.extend(onchain_products)
            logger.info(f"[OKXAPI] ✅ On-chain: {len(onchain_products)} продуктів")
            
            # Отримуємо Simple Earn продукти
            simple_earn_products = await self.get_simple_earn_flexible_products()
            all_products.extend(simple_earn_products)
            logger.info(f"[OKXAPI] ✅ Simple Earn: {len(simple_earn_products)} продуктів")
            
            # Нормалізація через базовий метод
            normalized = []
            for product in all_products:
                try:
                    norm_product = self.normalize_earn_product(product)
                    normalized.append(norm_product)
                except Exception as e:
                    logger.warning(f"[OKXAPI] Помилка нормалізації: {e}")
                    normalized.append(product)
            
            logger.info(f"[OKXAPI] ✅ Агреговано {len(normalized)} продуктів")
            return normalized
            
        except Exception as e:
            logger.error(f"[OKXAPI] ❌ Помилка агрегації Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Отримує Earn продукти для конкретного активу.
        
        Args:
            asset: Символ активу (BTC, ETH, USDT, тощо)
        
        Returns:
            List[Dict]: Список продуктів для активу
        """
        try:
            all_products = []
            
            # Отримуємо On-chain продукти для активу
            onchain = await self.get_onchain_earn_products(ccy=asset)
            all_products.extend(onchain)
            
            # Отримуємо Simple Earn продукти для активу
            simple = await self.get_simple_earn_flexible_products(ccy=asset)
            all_products.extend(simple)
            
            logger.info(f"[OKXAPI] Знайдено {len(all_products)} продуктів для {asset}")
            return all_products
            
        except Exception as e:
            logger.error(f"[OKXAPI] Помилка отримання продуктів для {asset}: {e}")
            return []

    # Реалізація абстрактних методів з BaseExchange
    async def get_flexible_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """Аліас для Simple Earn Flexible."""
        return await self.get_simple_earn_flexible_products(ccy=asset)

    async def get_locked_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        """Аліас для On-chain earn (які можуть мати lock period)."""
        return await self.get_onchain_earn_products(ccy=asset)

