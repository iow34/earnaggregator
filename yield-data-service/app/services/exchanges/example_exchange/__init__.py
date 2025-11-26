"""
Example Exchange Integration.

Цей приклад показує як додати нову біржу в систему.
Скопіюйте цю структуру та замініть логіку для реальної біржі.
"""

from .api import ExampleAPI
from .service import ExampleService

__all__ = ["ExampleAPI", "ExampleService"]
