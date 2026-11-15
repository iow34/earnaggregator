from typing import List, Dict, Optional, Any, Union
from urllib.parse import urljoin

from ..base_exchange import BaseExchange
from app.config import settings
from app.utils.logger import logger
from .models import MEXCEarnAPIResponse, CurrencyResult, FinancialProduct


class MEXCAPI(BaseExchange):
    def __init__(self, api_key: str = "", api_secret: str = ""):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url=getattr(settings, "mexc_api_url", "https://www.mexc.com"),
        )
        logger.info(f"[MEXCAPI] Ініціалізовано з URL: {self.base_url}")

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = "GET"
    ) -> Dict[str, Any]:
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
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

                data = response.json()
                logger.debug(f"[MEXCAPI] Отримана відповідь від {url}")
                return data

        except Exception as e:
            logger.error(f"[MEXCAPI] Помилка запиту до {url}: {e}")
            raise

    async def get_earn_products(
        self, page: int = 1, page_size: int = 100, match_member_assets: bool = False
    ) -> MEXCEarnAPIResponse:
        endpoint = "/api/financialactivity/financial/products/list"
        params = {
            "matchMemberAssets": str(match_member_assets).lower(),
            "page": page,
            "pageSize": page_size,
        }

        logger.info(f"[MEXCAPI] Запит earn продуктів: page={page}, pageSize={page_size}")
        response_data = await self._make_request(endpoint, params)

        api_response = MEXCEarnAPIResponse(**response_data)

        if not api_response.is_success:
            raise Exception(f"MEXC API помилка: {api_response.msg}")

        logger.info(
            f"[MEXCAPI] Отримано {len(api_response.result)} валют з {api_response.total} загалом"
        )
        return api_response

    async def get_all_earn_products(self) -> List[CurrencyResult]:
        all_results = []
        page = 1
        page_size = 100

        while True:
            try:
                response = await self.get_earn_products(
                    page=page, page_size=page_size, match_member_assets=False
                )

                all_results.extend(response.result)

                if page >= response.total_pages:
                    break

                page += 1

            except Exception as e:
                logger.error(f"[MEXCAPI] Помилка отримання сторінки {page}: {e}")
                break

        logger.info(f"[MEXCAPI] Загалом отримано {len(all_results)} валют")
        return all_results

    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            currencies = await self.get_all_earn_products()
            products = []

            for currency in currencies:
                if asset and currency.currency != asset.upper():
                    continue

                for product in currency.financialProductList:
                    if (
                        product.financialType == "FLEXIBLE"
                        and product.financialState == 2
                        and not product.soldOut
                    ):
                        products.append(
                            {
                                "id": f"mexc_flexible_{product.financialId}",
                                "symbol": currency.currency,
                                "name": f"{currency.currency} Flexible Savings",
                                "provider": "MEXC",
                                "apy": self._parse_apr(product),
                                "min_amount": 0.001,  # Default minimum
                                "max_amount": None,
                                "lock_period_days": 0,
                                "product_type": "Flexible",
                                "is_active": True,
                                "risk_level": "Low"
                                if currency.currency in ["USDT", "USDC"]
                                else "Medium",
                                "description": f"Flexible savings for {currency.currency}",
                                "website_url": "https://www.mexc.com/staking",
                                "raw_data": product.model_dump(),
                            }
                        )

            logger.info(f"[MEXCAPI] Знайдено {len(products)} Flexible продуктів")
            return products

        except Exception as e:
            logger.error(f"[MEXCAPI] Помилка отримання Flexible продуктів: {e}")
            return []

    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            currencies = await self.get_all_earn_products()
            products = []

            for currency in currencies:
                if asset and currency.currency != asset.upper():
                    continue

                for product in currency.financialProductList:
                    if (
                        product.financialType == "FIXED"
                        and product.financialState == 2
                        and not product.soldOut
                        and product.fixedInvestPeriodCount
                    ):
                        products.append(
                            {
                                "id": f"mexc_fixed_{product.financialId}",
                                "symbol": currency.currency,
                                "name": f"{currency.currency} {product.fixedInvestPeriodCount} Days Fixed Savings",
                                "provider": "MEXC",
                                "apy": self._parse_apr(product),
                                "min_amount": 0.001,  # Default minimum
                                "max_amount": None,
                                "lock_period_days": product.fixedInvestPeriodCount,
                                "product_type": "Locked",
                                "is_active": True,
                                "risk_level": "Low"
                                if currency.currency in ["USDT", "USDC"]
                                else "Medium",
                                "description": f"Fixed savings for {currency.currency} ({product.fixedInvestPeriodCount} days)",
                                "website_url": "https://www.mexc.com/staking",
                                "raw_data": product.model_dump(),
                            }
                        )

            logger.info(f"[MEXCAPI] Знайдено {len(products)} Locked продуктів")
            return products

        except Exception as e:
            logger.error(f"[MEXCAPI] Помилка отримання Locked продуктів: {e}")
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        try:
            flexible = await self.get_flexible_savings_products(asset=asset)
            locked = await self.get_locked_savings_products(asset=asset)

            all_products = flexible + locked
            logger.info(f"[MEXCAPI] Для {asset} знайдено {len(all_products)} продуктів")
            return all_products

        except Exception as e:
            logger.error(f"[MEXCAPI] Помилка отримання продуктів для {asset}: {e}")
            return []

    def _parse_apr(self, product: FinancialProduct) -> float:
        try:
            return float(product.showApr)

        except (ValueError, TypeError, AttributeError):
            logger.warning(f"[MEXCAPI] Помилка парсингу APR для продукту {product.financialId}")
            return 0.0
