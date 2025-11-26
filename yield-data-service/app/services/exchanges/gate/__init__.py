"""
Інтеграція з Gate.io API.

Цей пакет містить всю логіку для роботи з Gate.io Earn продуктами.
"""

from .api import GateAPI
from .service import GateService
from .models import GateUniCurrency, GateFlexibleProduct, GateFixedProduct

__all__ = [
    "GateAPI",
    "GateService",
    "GateUniCurrency",
    "GateFlexibleProduct",
    "GateFixedProduct"
]

