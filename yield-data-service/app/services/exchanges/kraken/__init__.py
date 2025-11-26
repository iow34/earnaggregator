"""
Інтеграція з Kraken API для отримання Earn продуктів.

Kraken надає наступні типи Earn продуктів:
- Flexible staking (lock_type="flexible") - гнучке стейкінг без блокування
- Bonded staking (lock_type="bonded") - стейкінг з фіксованим терміном блокування

API документація: https://docs.kraken.com/api/docs/guides/spot-rest-earn
"""

from .api import KrakenAPI
from .service import KrakenService

__all__ = [
    "KrakenAPI",
    "KrakenService"
]

