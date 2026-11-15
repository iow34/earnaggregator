from typing import List, Dict, Optional, Any
from datetime import datetime, UTC
import json
from pathlib import Path

from ..base_service import BaseExchangeService
from .api import GateAPI
from app.utils.logger import logger


class GateService(BaseExchangeService):
    def __init__(self):
        super().__init__("gate", GateAPI)

    async def test_connection(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "status": "error",
                "message": "API ключі Gate.io не налаштовані",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        try:
            logger.info("🧪 Тестування підключення до Gate.io API...")
            start_time = datetime.now(UTC)

            currencies = await self.api_client.get_uni_currencies(page=1, limit=1)

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            return {
                "status": "success",
                "message": "Підключення до Gate.io API успішне",
                "response_time_ms": round(response_time * 1000, 2),
                "api_status": "active",
                "currencies_found": len(currencies) if currencies else 0,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Помилка підключення до Gate.io API: {e}")
            return {
                "status": "error",
                "message": f"Помилка підключення: {str(e)}",
                "api_status": "inactive",
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def get_products_with_cache(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"exchange:gate:{symbol or 'all'}"

        cached_data = await self.cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Gate.io продукти отримано з кешу для {symbol or 'всі'}")
            return cached_data.get("products", [])

        logger.info(f"💾 Запит до Gate.io API для {symbol or 'всіх'} продуктів")
        try:
            if symbol:
                flexible_products = await self.api_client.get_earn_products_by_asset(symbol)
            else:
                flexible_products = await self.api_client.get_earn_products()

            fixed_products = await self._get_fixed_products_from_db(symbol)

            all_products = flexible_products + fixed_products

            normalized_products = await self._normalize_products(all_products)

            cache_data = {
                "products": normalized_products,
                "timestamp": datetime.now(UTC).isoformat(),
                "source": "gate_api",
            }
            await self.cache_manager.set_cached_data(cache_key, cache_data, expiration=3600)

            logger.info(f"✅ Gate.io: отримано та кешовано {len(normalized_products)} продуктів")
            return normalized_products

        except Exception as e:
            logger.error(f"❌ Помилка отримання Gate.io продуктів: {e}")
            return []

    async def _normalize_products(self, raw_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []

        for product in raw_products:
            try:
                normalized_product = {
                    "id": product.get("id"),
                    "symbol": product.get("symbol"),
                    "name": product.get("name"),
                    "provider": "gate",
                    "apy": float(product.get("apy", 0)),
                    "min_amount": product.get("min_amount"),
                    "max_amount": product.get("max_amount"),
                    "lock_period_days": int(product.get("lock_period_days", 0)),
                    "product_type": product.get("product_type", "Flexible"),
                    "is_active": product.get("is_active", True),
                    "risk_level": product.get("risk_level", "Low"),
                    "description": product.get("description", ""),
                    "website_url": product.get("website_url", "https://www.gate.com/simple-earn"),
                    "raw_data": product.get("raw_data", {}),
                    "is_cefi": True,
                    "max_apy": float(product.get("apy", 0)),
                }

                normalized.append(normalized_product)

            except Exception as e:
                logger.warning(
                    f"[GateService] Помилка нормалізації продукту {product.get('id', 'unknown')}: {e}"
                )
                continue

        logger.info(f"[GateService] Нормалізовано {len(normalized)} продуктів")
        return normalized

    async def _get_fixed_products_from_db(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        logger.info("[GateService] Fixed продукти з БД поки не реалізовано")
        return []

    async def load_fixed_products_from_json(self, filepath: str) -> Dict[str, Any]:
        try:
            logger.info(f"📂 Завантаження Fixed продуктів з {filepath}")

            file_path = Path(filepath)
            if not file_path.exists():
                return {
                    "status": "error",
                    "message": f"Файл не знайдено: {filepath}",
                    "products_loaded": 0,
                }

            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, list):
                return {
                    "status": "error",
                    "message": "JSON має містити список продуктів",
                    "products_loaded": 0,
                }

            products = []
            for item in raw_data:
                try:
                    symbol = item.get("symbol", "")
                    lock_days = item.get("lock_period_days", 0)
                    product_id = f"gate_fixed_{symbol}_{lock_days}"

                    product = {
                        "id": product_id,
                        "symbol": symbol,
                        "name": f"{symbol} Fixed {lock_days} days",
                        "provider": "gate",
                        "apy": float(item.get("apy", 0)),
                        "min_amount": item.get("min_amount"),
                        "max_amount": item.get("max_amount"),
                        "lock_period_days": lock_days,
                        "product_type": "Fixed",
                        "is_active": item.get("status", "active") == "active",
                        "risk_level": "Low",
                        "description": f"Gate.io Fixed Savings for {symbol} ({lock_days} days)",
                        "website_url": "https://www.gate.com/simple-earn",
                        "raw_data": item,
                        "is_cefi": True,
                        "max_apy": float(item.get("apy", 0)),
                    }

                    products.append(product)

                except Exception as parse_error:
                    logger.warning(f"[GateService] Помилка парсингу продукту: {parse_error}")
                    continue

            if products:
                sync_stats = await self._save_products_to_db(products)

                return {
                    "status": "success",
                    "message": f"Завантажено {len(products)} Fixed продуктів",
                    "products_loaded": len(products),
                    "sync_stats": sync_stats,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            else:
                return {
                    "status": "warning",
                    "message": "Не знайдено валідних продуктів у файлі",
                    "products_loaded": 0,
                }

        except json.JSONDecodeError as e:
            logger.error(f"❌ Помилка парсингу JSON: {e}")
            return {
                "status": "error",
                "message": f"Невалідний JSON: {str(e)}",
                "products_loaded": 0,
            }
        except Exception as e:
            logger.error(f"❌ Помилка завантаження Fixed продуктів: {e}")
            return {
                "status": "error",
                "message": f"Помилка завантаження: {str(e)}",
                "products_loaded": 0,
            }
