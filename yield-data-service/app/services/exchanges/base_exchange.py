import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import httpx

from app.utils.logger import logger


class BaseExchange(ABC):
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.client: Optional[httpx.AsyncClient] = None

        logger.info(f"Ініціалізовано {self.__class__.__name__} з URL: {base_url}")

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_client()

    async def _ensure_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)

    async def _close_client(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_required: bool = False,
    ) -> Dict[str, Any]:
        await self._ensure_client()

        url = urljoin(self.base_url + "/", path.lstrip("/"))

        request_headers = self.get_headers()
        if headers:
            request_headers.update(headers)

        request_params = params or {}

        logger.debug(f"[{self.__class__.__name__}] {method} {url} params={request_params}")

        try:
            response = await self.client.request(
                method=method, url=url, params=request_params, json=data, headers=request_headers
            )

            response.raise_for_status()

            result = response.json()

            logger.debug(
                f"[{self.__class__.__name__}] Отримана відповідь: {len(str(result))} символів"
            )
            return result

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 403:
                content = e.response.text
                if "Just a moment" in content or "cloudflare" in content.lower():
                    logger.warning(
                        f"[{self.__class__.__name__}] Cloudflare protection detected (403). Waiting 30 seconds before retry..."
                    )
                    await asyncio.sleep(30)
                    raise Exception(
                        f"Cloudflare protection (403): Request blocked, retry after delay"
                    )

            logger.error(
                f"[{self.__class__.__name__}] HTTP помилка {status_code}: {e.response.text}"
            )
            raise Exception(f"API помилка {status_code}: {e.response.text}")

        except httpx.RequestError as e:
            logger.error(f"[{self.__class__.__name__}] Помилка запиту: {e}")
            raise Exception(f"Помилка з'єднання з API: {e}")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Неочікувана помилка: {e}")
            raise

    def normalize_earn_product(self, product: Dict[str, Any]) -> Dict[str, Any]:

        normalized = product.copy()

        normalized.setdefault("is_active", True)
        normalized.setdefault("lock_period_days", 0)
        normalized.setdefault("min_amount", 0.0)
        normalized.setdefault("max_amount", None)
        normalized.setdefault("description", "")
        normalized.setdefault("website_url", "")
        normalized.setdefault("raw_data", product)

        return normalized

    @abstractmethod
    async def get_flexible_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_locked_savings_products(
        self, asset: Optional[str] = None, current: int = 1, size: int = 100
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_earn_products(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        pass
