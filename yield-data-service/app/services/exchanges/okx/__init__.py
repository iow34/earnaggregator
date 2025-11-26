"""
Модуль інтеграції з OKX Financial Product API.

OKX надає наступні типи Earn продуктів:
- On-chain earn (staking/DeFi) - GET /api/v5/finance/staking-defi/offers
- Simple Earn Flexible - GET /api/v5/finance/simple-earn/products
"""

from .api import OKXAPI
from .service import OKXService
from .models import OKXOnChainProduct, OKXSimpleEarnProduct, OKXUnifiedProduct

__all__ = [
    "OKXAPI",
    "OKXService",
    "OKXOnChainProduct",
    "OKXSimpleEarnProduct",
    "OKXUnifiedProduct"
]

