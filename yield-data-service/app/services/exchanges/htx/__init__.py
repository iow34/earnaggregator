"""
Модуль для інтеграції з HTX Exchange API.

HTX (колишній Huobi) надає Savings продукти:
- Flexible Savings (гнучкі заощадження)
- Fixed Savings (фіксовані заощадження)
"""

from .api import HTXAPI
from .service import HTXService
from .models import HTXFlexibleProduct, HTXFixedProduct

__all__ = [
    "HTXAPI",
    "HTXService",
    "HTXFlexibleProduct",
    "HTXFixedProduct"
]

