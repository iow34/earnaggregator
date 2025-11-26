"""
API клієнт для BitMart Earn продуктів.

BitMart надає публічний API для отримання Savings/Earn продуктів через
ендпоінт /gw-api/newearn/summary/earn/product/list.

Цей клас успадковує BaseExchange та реалізує методи для отримання даних.
"""

from typing import List, Dict, Optional, Any, Union
from urllib.parse import urljoin

from ..base_exchange import BaseExchange
from app.config import settings
from app.utils.logger import logger
from .models import BitMartEarnAPIResponse, EarnProduct, AddInfo


class BitMartAPI(BaseExchange):
    """
    API клієнт для BitMart Earn продуктів.

    BitMart надає публічний API без аутентифікації для отримання списку
    Savings/Earn продуктів. Цей клас реалізує запити до API та
    повертає структуровані дані.
    """

    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        Ініціалізація BitMart API клієнта.

        Args:
            api_key: API ключ (не використовується для цього публічного API)
            api_secret: API секрет (не використовується для цього публічного API)
        """
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url=getattr(settings, 'bitmart_api_url', 'https://www.bitmart.com')
        )
        logger.info(f"[BitMartAPI] Ініціалізовано з URL: {self.base_url}")

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Виконує HTTP запит до BitMart API.

        Args:
            endpoint: API ендпоінт
            params: Query параметри
            method: HTTP метод

        Returns:
            JSON відповідь

        Raises:
            Exception: При помилці запиту
        """
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))

        try:
            async with self as api_client:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params or {},
                    headers={
                        "User-Agent": "EarnAggregator/1.0",
                        "Accept": "application/json",
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

                data = response.json()
                logger.debug(f"[BitMartAPI] Отримана відповідь від {url}")
                return data

        except Exception as e:
            logger.error(f"[BitMartAPI] Помилка запиту до {url}: {e}")
            raise

    async def get_earn_products_direct(
        self,
        coin_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Прямий запит до BitMart API для отримання продуктів.

        Args:
            coin_name: Опціональний фільтр по конкретній валюті

        Returns:
            Dict[str, Any]: JSON відповідь API

        Raises:
            Exception: При помилці запиту
        """
        try:
            logger.info(f"[BitMartAPI] Прямий запит Earn продуктів{' для ' + coin_name if coin_name else ''}")

            # Формуємо параметри запиту
            params = {}
            if coin_name:
                params["coinName"] = coin_name.upper()

            # Виконуємо запит до API
            endpoint = "/gw-api/newearn/summary/earn/product/list"
            response_data = await self._make_request(endpoint, params)

            # Перевіряємо успішність відповіді
            if isinstance(response_data, dict) and response_data.get('code') == 0:
                products_count = len(response_data.get('data', []))
                logger.info(f"[BitMartAPI] Отримано {products_count} продуктів з API")
                return response_data
            else:
                raise Exception(f"BitMart API error: {response_data.get('msg', 'Unknown error')}")

        except Exception as e:
            logger.error(f"[BitMartAPI] Помилка отримання продуктів: {e}")
            raise

    async def get_earn_products(
        self,
        coin_name: Optional[str] = None
    ) -> BitMartEarnAPIResponse:
        """
        Отримує всі Earn продукти з BitMart API.

        Args:
            coin_name: Опціональний фільтр по конкретній валюті

        Returns:
            BitMartEarnAPIResponse: Структурована відповідь API

        Raises:
            Exception: При помилці запиту або парсингу
        """
        try:
            logger.info(f"[BitMartAPI] Запит Earn продуктів{' для ' + coin_name if coin_name else ''}")

            # Формуємо параметри запиту
            params = {}
            if coin_name:
                params["coinName"] = coin_name.upper()

            # Виконуємо запит до API
            endpoint = "/gw-api/newearn/summary/earn/product/list"
            response_data = await self._make_request(endpoint, params)

            # Парсимо відповідь через Pydantic модель
            api_response = BitMartEarnAPIResponse(**response_data)

            if not api_response.is_success:
                raise Exception(f"BitMart API error: {api_response.msg}")

            logger.info(f"[BitMartAPI] Отримано {len(api_response.result)} продуктів з API")
            return api_response

        except Exception as e:
            logger.error(f"[BitMartAPI] Помилка отримання продуктів: {e}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """
        Тестує підключення до BitMart API.

        Returns:
            Dict з результатами тесту
        """
        try:
            logger.info("[BitMartAPI] Тестування підключення до BitMart API")

            # Спробуємо отримати невелику кількість продуктів напряму
            endpoint = "/gw-api/newearn/summary/earn/product/list"
            response_data = await self._make_request(endpoint, {})

            # Перевіряємо структуру відповіді
            if isinstance(response_data, dict) and 'code' in response_data:
                if response_data.get('code') == 0:
                    products_count = len(response_data.get('data', []))
                    return {
                        "status": "success",
                        "message": f"✅ Підключення успішне. Отримано {products_count} продуктів",
                        "products_count": products_count,
                        "timestamp": "BitMartAPI"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"❌ API помилка: {response_data.get('msg', 'Unknown error')}",
                        "products_count": 0
                    }
            else:
                return {
                    "status": "error",
                    "message": "❌ Неправильна структура відповіді API",
                    "products_count": 0
                }

        except Exception as e:
            logger.error(f"[BitMartAPI] Помилка тестування підключення: {e}")
            return {
                "status": "error",
                "message": f"❌ Помилка підключення: {str(e)}",
                "products_count": 0
            }

    def extract_products_from_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Витягує всі продукти з JSON відповіді API для подальшої обробки.

        Args:
            response_data: JSON відповідь API

        Returns:
            List[Dict[str, Any]]: Список продуктів
        """
        products = []

        data = response_data.get('data', [])
        for earn_product in data:
            summary_products = earn_product.get('summaryProductList', [])
            for summary_product in summary_products:
                # Пропускаємо wealth продукти (stable), обробляємо тільки saving
                if summary_product.get('earnType') == "wealth":
                    continue

                # Додаємо всі продукти з addInfo
                add_info_list = summary_product.get('addInfo', [])
                for add_info in add_info_list:
                    if add_info.get('saleState') == 1:  # Тільки активні продукти
                        products.append(add_info)

        logger.debug(f"[BitMartAPI] Витягнуто {len(products)} активних продуктів з відповіді")
        return products

    def get_product_apr(self, product: Dict[str, Any]) -> float:
        """
        Отримує APR продукту, враховуючи tiered ставки.

        Для tiered продуктів (rateType=1) обирає мінімальний pec з tierRules.
        Для фіксованих продуктів використовує annualProfitPec напряму.

        Args:
            product: AddInfo продукт як словник

        Returns:
            float: APR як десяткове число
        """
        try:
            if product.get('rateType') == 1 and product.get('tierRules'):
                # Tiered APR - обираємо мінімальний pec
                tier_rules = product.get('tierRules', [])
                min_pec = min(float(tier.get('pec', '0')) for tier in tier_rules)
                return min_pec
            else:
                # Фіксований APR
                annual_profit_pec = product.get('annualProfitPec', '0%')
                return float(annual_profit_pec.replace('%', ''))

        except (ValueError, AttributeError) as e:
            logger.warning(f"[BitMartAPI] Помилка парсингу APR для продукту {product.get('id')}: {e}")
            return 0.0

    def get_product_min_amount(self, product: Dict[str, Any]) -> float:
        """
        Отримує мінімальну суму для продукту.

        Args:
            product: AddInfo продукт як словник

        Returns:
            float: Мінімальна сума
        """
        try:
            return float(product.get('minSubcription', 0))
        except (ValueError, TypeError):
            return 0.0

    async def get_flexible_savings_products(self, asset: Optional[str] = None, current: int = 1, size: int = 100) -> List[Dict[str, Any]]:
        """
        Отримує Flexible Savings продукти.

        Args:
            asset: Символ активу для фільтрації
            current: Номер сторінки (не використовується для BitMart)
            size: Розмір сторінки (не використовується для BitMart)

        Returns:
            List[Dict]: Список flexible продуктів
        """
        products = await self.get_products_from_api(asset)
        return [p for p in products if p.get("product_type") == "Flexible"]

    async def get_locked_savings_products(self, asset: Optional[str] = None, current: int = 1, size: int = 100) -> List[Dict[str, Any]]:
        """
        Отримує Locked Savings продукти.

        Args:
            asset: Символ активу для фільтрації
            current: Номер сторінки (не використовується для BitMart)
            size: Розмір сторінки (не використовується для BitMart)

        Returns:
            List[Dict]: Список locked продуктів
        """
        products = await self.get_products_from_api(asset)
        return [p for p in products if p.get("product_type") == "Locked"]

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Отримує всі Earn продукти з біржі.

        Returns:
            List[Dict]: Всі Earn продукти
        """
        return await self.get_products_from_api()

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Отримує Earn продукти для конкретного активу.

        Args:
            asset: Символ активу

        Returns:
            List[Dict]: Earn продукти для активу
        """
        return await self.get_products_from_api(asset)

    async def get_products_from_api(self, asset: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує продукти з API та нормалізує їх.

        Args:
            asset: Опціональний символ для фільтрації

        Returns:
            List[Dict]: Нормалізовані продукти
        """
        try:
            # Отримуємо дані з API напряму
            api_response = await self.get_earn_products_direct(coin_name=asset)

            # Витягуємо продукти з відповіді
            raw_products = self.extract_products_from_response(api_response)

            # Нормалізуємо продукти (проста версія для BaseExchange)
            normalized_products = []
            for product in raw_products:
                if product.saleState != 1:  # Тільки активні продукти
                    continue

                apr = self.get_product_apr(product)
                if apr <= 0:
                    continue

                # Визначаємо тип продукту
                if product.productType == "flexible" and product.lockDay == 0:
                    prod_type = "Flexible"
                    lock_days = 0
                    name = f"{product.coinName} Flexible Savings"
                elif product.productType == "fixed" and product.lockDay > 0:
                    prod_type = "Locked"
                    lock_days = product.lockDay
                    name = f"{product.coinName} {lock_days} Days Fixed Savings"
                else:
                    continue

                # Створюємо нормалізований продукт
                normalized_product = {
                    "id": f"bitmart_{product.productType}_{product.id}",
                    "symbol": product.coinName,
                    "name": name,
                    "provider": "BitMart",
                    "apy": apr,
                    "min_amount": self.get_product_min_amount(product),
                    "max_amount": None,
                    "lock_period_days": lock_days,
                    "product_type": prod_type,
                    "is_cefi": True,
                    "is_active": True,
                    "risk_level": "Low" if product.coinName in ["USDT", "USDC"] else "Medium",
                    "description": f"{'Flexible' if prod_type == 'Flexible' else 'Fixed'} savings for {product.coinName}",
                    "website_url": "https://www.bitmart.com/earn",
                    "raw_data": product.model_dump() if hasattr(product, 'model_dump') else product.__dict__,
                }
                normalized_products.append(normalized_product)

            return normalized_products

        except Exception as e:
            logger.error(f"[BitMartAPI] Помилка отримання продуктів з API: {e}")
            return []
