"""
Інтеграція з HTX API для отримання Earn продуктів.

HTX (колишній Huobi) надає наступні типи Earn продуктів.

Документація API: https://www.htx.com/en-us/opend/newApiPages
Основний endpoint для Earn: GET /v1/earn/project/queryEarnProjectList
"""

import hmac
import hashlib
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
from urllib.parse import urlencode, quote

from ..base_exchange import BaseExchange
from app.utils.logger import logger


class HTXAPI(BaseExchange):
    """
    Клієнт для роботи з HTX API.
    
    HTX використовує специфічну аутентифікацію HmacSHA256:
    - Формат підпису: method\nhost\npath\nsorted_params
    - Обов'язкові параметри: AccessKeyId, SignatureMethod, SignatureVersion, Timestamp
    - Rate limits: 100 запитів на 10 секунд
    """

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(
            api_key=api_key,
            api_secret=api_secret,
            base_url="https://api.htx.com"
        )
        self.host = "api.htx.com"
        self.max_retry_attempts = 4
        self.retry_delays = [2, 5, 10, 30]  # Більші затримки для уникнення rate limit
        self.request_delay = 1.0  # Затримка між запитами в секундах

    def get_headers(self) -> Dict[str, str]:
        """Заголовки для API запитів HTX."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _generate_signature(self, method: str, path: str, params: Dict[str, Any]) -> str:
        """
        Генерує HMAC SHA256 підпис для HTX API.
        
        Формат підпису:
        method\nhost\npath\nsorted_params
        
        Args:
            method: HTTP метод (GET, POST)
            path: Шлях endpoint
            params: Параметри запиту (вже з AccessKeyId, Timestamp, etc.)
            
        Returns:
            str: Base64 encoded підпис
        """
        # Сортуємо параметри за ключами
        sorted_params = sorted(params.items())
        
        # URL-encode параметрів
        query_string = urlencode(sorted_params)
        
        # Формуємо рядок для підпису
        signature_string = f"{method}\n{self.host}\n{path}\n{query_string}"
        
        # Генеруємо HMAC SHA256
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Кодуємо в base64
        import base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return signature_b64

    def _prepare_signed_params(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Підготовка параметрів з підписом для HTX API.
        
        Args:
            method: HTTP метод
            path: Шлях endpoint
            params: Додаткові параметри
            
        Returns:
            Dict з усіма необхідними параметрами включно з підписом
        """
        if params is None:
            params = {}
        
        # Додаємо обов'язкові параметри HTX
        signed_params = {
            "AccessKeyId": self.api_key,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": "2",
            "Timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        # Додаємо користувацькі параметри
        signed_params.update(params)
        
        # Генеруємо підпис
        signature = self._generate_signature(method, path, signed_params)
        signed_params["Signature"] = signature
        
        return signed_params

    def _normalize_project_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        currency = item.get("currency", "")
        term = int(item.get("term") or 0)
        view_rate = float(item.get("viewYearRate") or 0.0)
        start_amount = float(item.get("startAmount") or 0.0)

        lock_days = term if term and term > 0 else 0
        product_type = "Fixed" if lock_days > 0 else "Flexible"

        name = f"{currency} {'Fixed Savings (' + str(lock_days) + ' days)' if lock_days > 0 else 'Flexible Savings'}"
        product_id = item.get("productId", "")

        normalized = {
            "id": f"htx_{'fixed' if lock_days > 0 else 'flex'}_{product_id}{'_' + str(lock_days) if lock_days > 0 else ''}",
            "symbol": currency,
            "name": name,
            "provider": "HTX",
            "apy": view_rate * 100.0,
            "is_cefi": True,  # HTX - це централізована біржа (CeFi)
            "min_amount": start_amount,
            "max_amount": None,
            "lock_period_days": lock_days,
            "max_apy": view_rate * 100.0,  # Для HTX max_apy = apy
            "product_type": product_type,
            "is_active": True,
            "risk_level": "Low" if currency in ["USDT", "USDC", "DAI", "USD1"] else "Medium",
            "website_url": "https://www.htx.com/en-us/financial/earn/",
            "raw_data": item,
        }
        return normalized

    async def _fetch_earn_projects_page(
        self,
        page_num: int = 1,
        page_size: int = 100,
        currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = "/v1/earn/project/queryEarnProjectList"
        params: Dict[str, Any] = {"pageNum": page_num, "pageSize": page_size}
        if currency:
            params["currency"] = currency

        response = await self._make_signed_request("GET", path, params)
        return response

    async def _make_signed_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Виконує підписаний запит до HTX API з retry logic.
        
        Args:
            method: HTTP метод
            path: Шлях endpoint
            params: Параметри запиту
            
        Returns:
            Dict з відповіддю API
        """
        for attempt in range(self.max_retry_attempts):
            try:
                # Затримка між запитами для зменшення навантаження
                if attempt > 0:
                    await asyncio.sleep(self.request_delay)

                # Підготовка підписаних параметрів
                signed_params = self._prepare_signed_params(method, path, params)

                # Виконуємо запит
                response = await self._make_request(
                    method=method,
                    path=path,
                    params=signed_params,
                    auth_required=False  # Аутентифікація вже в параметрах
                )
                
                # Перевірка статусу відповіді
                if isinstance(response, dict):
                    status = response.get("status")

                    if status == "ok":
                        return response

                    elif status == "error":
                        err_code = response.get("err-code", "unknown")
                        err_msg = response.get("err-msg", "Unknown error")

                        # Обробка специфічних помилок
                        if "invalid signature" in err_code.lower() or "invalid signature" in err_msg.lower():
                            logger.error(f"[HTXAPI] Invalid signature error. Attempt {attempt + 1}/{self.max_retry_attempts}")
                            # Логування для діагностики
                            self._log_failed_signature(method, path, params, response)

                            if attempt == self.max_retry_attempts - 1:
                                raise ValueError(f"Invalid signature after {self.max_retry_attempts} attempts")

                            await asyncio.sleep(self.retry_delays[attempt])
                            continue

                        elif "invalid timestamp" in err_code.lower() or "invalid timestamp" in err_msg.lower():
                            logger.warning(f"[HTXAPI] Invalid timestamp, retrying with updated time")
                            await asyncio.sleep(1)
                            continue

                        elif "429" in err_code or "rate limit" in err_msg.lower():
                            logger.warning(f"[HTXAPI] Rate limit exceeded, waiting 10 seconds")
                            await asyncio.sleep(10)
                            continue

                        else:
                            logger.error(f"[HTXAPI] API error: {err_code} - {err_msg}")
                            raise ValueError(f"HTX API error: {err_code} - {err_msg}")

                # Якщо відповідь не dict, це може бути помилка (наприклад HTML від Cloudflare)
                elif isinstance(response, str) and ("Just a moment" in response or "cloudflare" in response.lower()):
                    logger.warning(f"[HTXAPI] Cloudflare protection detected in response. Attempt {attempt + 1}/{self.max_retry_attempts}")
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(30)  # Довша затримка для Cloudflare
                        continue
                    else:
                        raise ValueError("Cloudflare protection blocked request after all retries")

                return response
                
            except Exception as e:
                error_msg = str(e)

                # Спеціальна обробка для Cloudflare 403 помилки
                if "403" in error_msg and ("Just a moment" in error_msg or "cloudflare" in error_msg.lower()):
                    logger.warning(f"[HTXAPI] Cloudflare 403 protection detected. Attempt {attempt + 1}/{self.max_retry_attempts}")
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(30)  # Довша затримка для Cloudflare
                        continue

                if attempt == self.max_retry_attempts - 1:
                    logger.error(f"[HTXAPI] Request failed after {self.max_retry_attempts} attempts: {e}")
                    raise

                logger.warning(f"[HTXAPI] Request failed (attempt {attempt + 1}/{self.max_retry_attempts}): {e}")
                await asyncio.sleep(self.retry_delays[attempt])
        
        raise ValueError(f"Failed to complete request after {self.max_retry_attempts} attempts")

    def _log_failed_signature(self, method: str, path: str, params: Optional[Dict], response: Dict):
        """Логування невдалих підписів для діагностики."""
        try:
            log_file = "/app/logs/htx_failed_signature.log"
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.now(UTC).isoformat()}\n")
                f.write(f"Method: {method}\n")
                f.write(f"Path: {path}\n")
                f.write(f"Params: {params}\n")
                f.write(f"Response: {response}\n")
        except Exception as e:
            logger.error(f"[HTXAPI] Failed to log signature error: {e}")

    async def get_flexible_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"[HTXAPI] Запит Flexible продуктів{f' для {asset}' if asset else ''}")
            page_num = current if current and current > 0 else 1
            page_size = size if size and size > 0 else 100
            resp = await self._fetch_earn_projects_page(page_num=page_num, page_size=page_size, currency=asset)
            data = (resp.get("data") or {})
            total = int(data.get("total") or 0)
            items = list(data.get("items") or [])

            products: List[Dict[str, Any]] = []
            for it in items:
                norm = self._normalize_project_item(it)
                if norm.get("lock_period_days", 0) == 0:
                    products.append(norm)

            logger.info(f"[HTXAPI] Отримано {len(products)} Flexible продуктів (page {page_num}/{(total + page_size - 1)//page_size if page_size else 1})")
            return products
        except Exception as e:
            logger.error(f"[HTXAPI] Помилка отримання Flexible продуктів: {e}", exc_info=True)
            return []

    async def get_locked_savings_products(
        self,
        asset: Optional[str] = None,
        current: int = 1,
        size: int = 100
    ) -> List[Dict[str, Any]]:
        try:
            logger.info(f"[HTXAPI] Запит Fixed продуктів{f' для {asset}' if asset else ''}")
            page_num = current if current and current > 0 else 1
            page_size = size if size and size > 0 else 100
            resp = await self._fetch_earn_projects_page(page_num=page_num, page_size=page_size, currency=asset)
            data = (resp.get("data") or {})
            total = int(data.get("total") or 0)
            items = list(data.get("items") or [])

            products: List[Dict[str, Any]] = []
            for it in items:
                norm = self._normalize_project_item(it)
                if norm.get("lock_period_days", 0) > 0:
                    products.append(norm)

            logger.info(f"[HTXAPI] Отримано {len(products)} Fixed продуктів (page {page_num}/{(total + page_size - 1)//page_size if page_size else 1})")
            return products
        except Exception as e:
            logger.error(f"[HTXAPI] Помилка отримання Fixed продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products(self) -> List[Dict[str, Any]]:
        """
        Отримання всіх Earn продуктів з агрегацією Flexible та Fixed.
        
        Returns:
            List всіх нормалізованих продуктів
        """
        try:
            logger.info("[HTXAPI] Початок отримання всіх Earn продуктів (пагінація)")
            page_num = 1
            page_size = 100
            products: List[Dict[str, Any]] = []

            while True:
                resp = await self._fetch_earn_projects_page(page_num=page_num, page_size=page_size)
                data = (resp.get("data") or {})
                total = int(data.get("total") or 0)
                items = list(data.get("items") or [])

                for it in items:
                    products.append(self._normalize_project_item(it))

                if page_num * page_size >= total or not items:
                    break
                page_num += 1

            logger.info(f"[HTXAPI] ✅ Агреговано {len(products)} Earn продуктів")
            return products
        except Exception as e:
            logger.error(f"[HTXAPI] ❌ Помилка отримання всіх Earn продуктів: {e}", exc_info=True)
            return []

    async def get_earn_products_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """
        Отримання Earn продуктів для конкретного активу.
        
        Args:
            asset: Символ криптовалюти (наприклад "BTC")
            
        Returns:
            List продуктів для конкретного активу
        """
        try:
            logger.info(f"[HTXAPI] Отримання продуктів для {asset}")
            page_num = 1
            page_size = 100
            products: List[Dict[str, Any]] = []

            while True:
                resp = await self._fetch_earn_projects_page(page_num=page_num, page_size=page_size, currency=asset)
                data = (resp.get("data") or {})
                total = int(data.get("total") or 0)
                items = list(data.get("items") or [])

                for it in items:
                    products.append(self._normalize_project_item(it))

                if page_num * page_size >= total or not items:
                    break
                page_num += 1

            logger.info(f"[HTXAPI] Знайдено {len(products)} продуктів для {asset}")
            return products
        except Exception as e:
            logger.error(f"[HTXAPI] Помилка фільтрації продуктів для {asset}: {e}")
            return []

