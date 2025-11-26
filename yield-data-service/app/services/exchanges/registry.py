"""
Реєстр бірж для динамічного завантаження та управління.

Цей модуль забезпечує:
- Автоматичне виявлення доступних бірж
- Динамічне завантаження сервісів бірж
- Уніфікований інтерфейс для всіх бірж
- Конфігурацію та валідацію бірж
"""

import importlib
import inspect
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

from app.utils.logger import logger


class ExchangeRegistry:
    """
    Реєстр для управління біржами в системі.

    Забезпечує динамічне завантаження та управління сервісами бірж.
    """

    def __init__(self):
        self._exchanges: Dict[str, Dict[str, Any]] = {}
        self._exchange_path = Path(__file__).parent

    async def initialize(self) -> None:
        """Ініціалізує реєстр та завантажує всі доступні біржі."""
        await self._discover_exchanges()
        logger.info(f"✅ Реєстр бірж ініціалізовано: {list(self._exchanges.keys())}")

    async def _discover_exchanges(self) -> None:
        """Автоматично виявляє та завантажує всі біржі."""
        # Список директорій які потрібно пропустити (шаблони, приклади)
        excluded_dirs = {'example_exchange'}
        
        for exchange_dir in self._exchange_path.iterdir():
            if exchange_dir.is_dir() and not exchange_dir.name.startswith('__'):
                exchange_name = exchange_dir.name
                
                # Пропускаємо виключені директорії
                if exchange_name in excluded_dirs:
                    logger.debug(f"⏭️ Пропущено директорію '{exchange_name}' (виключено з реєстру)")
                    continue
                
                try:
                    await self._load_exchange(exchange_name)
                    logger.info(f"✅ Біржа '{exchange_name}' завантажена")
                except Exception as e:
                    logger.warning(f"⚠️ Не вдалося завантажити біржу '{exchange_name}': {e}")

    async def _load_exchange(self, exchange_name: str) -> None:
        """Завантажує конкретну біржу."""
        try:
            # Імпортуємо модуль біржі
            module_path = f"app.services.exchanges.{exchange_name}"
            exchange_module = importlib.import_module(module_path)

            # Знаходимо сервіс клас
            service_class = None
            api_class = None

            for name, obj in inspect.getmembers(exchange_module):
                if (inspect.isclass(obj) and
                    name.endswith('Service') and
                    hasattr(obj, 'get_products_with_cache')):
                    service_class = obj
                elif (inspect.isclass(obj) and
                      name.endswith('API') and
                      hasattr(obj, 'get_earn_products')):
                    api_class = obj

            if not service_class:
                raise ValueError(f"Не знайдено сервіс клас для біржі {exchange_name}")

            # Створюємо екземпляр сервісу
            service_instance = service_class()

            self._exchanges[exchange_name] = {
                'name': exchange_name,
                'service_class': service_class,
                'service_instance': service_instance,
                'api_class': api_class,
                'module': exchange_module
            }

        except Exception as e:
            logger.error(f"❌ Помилка завантаження біржі {exchange_name}: {e}")
            raise

    def get_exchange_service(self, exchange_name: str) -> Any:
        """Повертає сервіс екземпляр для конкретної біржі."""
        if exchange_name not in self._exchanges:
            raise ValueError(f"Біржа '{exchange_name}' не знайдена")

        return self._exchanges[exchange_name]['service_instance']

    def get_exchange_api_class(self, exchange_name: str) -> Optional[Type]:
        """Повертає API клас для конкретної біржі."""
        if exchange_name not in self._exchanges:
            raise ValueError(f"Біржа '{exchange_name}' не знайдена")

        return self._exchanges[exchange_name]['api_class']

    def get_available_exchanges(self) -> List[str]:
        """Повертає список доступних бірж."""
        return list(self._exchanges.keys())

    def get_exchange_info(self, exchange_name: str) -> Dict[str, Any]:
        """Повертає інформацію про конкретну біржу."""
        if exchange_name not in self._exchanges:
            raise ValueError(f"Біржа '{exchange_name}' не знайдена")

        exchange_data = self._exchanges[exchange_name]
        return {
            'name': exchange_data['name'],
            'service_class': exchange_data['service_class'].__name__,
            'has_api_class': exchange_data['api_class'] is not None,
            'api_class': exchange_data['api_class'].__name__ if exchange_data['api_class'] else None
        }

    async def health_check_all(self) -> Dict[str, Any]:
        """Перевіряє здоров'я всіх бірж."""
        results = {}
        for exchange_name, exchange_data in self._exchanges.items():
            try:
                service = exchange_data['service_instance']
                if hasattr(service, 'get_health_status'):
                    health = await service.get_health_status()
                    results[exchange_name] = health
                else:
                    results[exchange_name] = {'status': 'unknown', 'error': 'No health check method'}
            except Exception as e:
                results[exchange_name] = {'status': 'error', 'error': str(e)}

        return results

    async def reload_exchange(self, exchange_name: str) -> None:
        """Перезавантажує конкретну біржу."""
        if exchange_name in self._exchanges:
            # Очищуємо кеш імпортів
            module_path = f"app.services.exchanges.{exchange_name}"
            if module_path in importlib.sys.modules:
                del importlib.sys.modules[module_path]

        await self._load_exchange(exchange_name)
        logger.info(f"🔄 Біржа '{exchange_name}' перезавантажена")


# Глобальний екземпляр реєстру
exchange_registry = ExchangeRegistry()
