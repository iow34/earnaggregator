"""
KuCoin exchange module.

Provides API client and service integration for KuCoin Earn (Savings) products.
"""

from .api import KuCoinAPI
from .service import KuCoinService

__all__ = [
    "KuCoinAPI",
    "KuCoinService",
]
