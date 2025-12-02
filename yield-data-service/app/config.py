"""
Конфігурація проекту Data Service.

Цей файл читає налаштування з .env файлу та надає їх у вигляді
зручного об'єкта для використання в усьому проекті.

Налаштування включають:
- Redis для кешування
- PostgreSQL для бази даних
- Параметри кешування та логування
"""

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """
    Налаштування проекту.
    
    Всі змінні читаються з .env файлу або змінних середовища.
    """
    
    
    # Redis налаштування
    redis_host: str = Field(default="localhost", description="Redis хост", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, description="Redis порт", alias="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, description="Redis пароль", alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, description="Redis база даних", alias="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, description="Redis URL", alias="REDIS_URL")
    
    # PostgreSQL налаштування
    database_url: str = Field(..., description="PostgreSQL connection string", alias="DATABASE_URL")
    
    # Середовище виконання
    environment: str = Field(
        default="development",
        description="Середовище виконання (development/production)",
        alias="ENVIRONMENT"
    )

    # Кешування
    cache_expiration: int = Field(
        default=3600,
        description="Час життя кешу в секундах (1 година)"
    )
    update_interval: int = Field(
        default=3600,
        description="Інтервал оновлення кешу в секундах (1 година)"
    )
    
    # API бірж
    binance_api_key: str = Field(
        default="your_binance_api_key_here",
        description="Binance API ключ"
    )
    binance_api_secret: str = Field(
        default="your_binance_api_secret_here", 
        description="Binance API секрет"
    )
    bybit_api_key: str = Field(
        default="your_bybit_api_key_here",
        description="Bybit API ключ"
    )
    bybit_api_secret: str = Field(
        default="your_bybit_api_secret_here",
        description="Bybit API секрет"
    )
    
    # OKX API (специфічна аутентифікація з 3 параметрами)
    okx_api_key: str = Field(
        default="your_okx_api_key_here",
        description="OKX API ключ"
    )
    okx_api_secret: str = Field(
        default="your_okx_api_secret_here",
        description="OKX API секрет"
    )
    okx_api_passphrase: str = Field(
        default="your_okx_api_passphrase_here",
        description="OKX API passphrase (встановлюється при створенні ключа)"
    )
    okx_base_url: str = Field(
        default="https://www.okx.com",
        description="OKX базовий URL"
    )
    
    # MEXC налаштування (manual mode)
    mexc_api_key: str = Field(
        default="",
        description="MEXC API Key (not used in manual mode)"
    )
    mexc_api_secret: str = Field(
        default="",
        description="MEXC API Secret (not used in manual mode)"
    )
    mexc_manual_mode: bool = Field(
        default=False,
        description="MEXC works in manual data import mode (deprecated)"
    )
    mexc_api_url: str = Field(
        default="https://www.mexc.com",
        description="MEXC API базовий URL для отримання Earn продуктів"
    )

    # BitMart налаштування
    bitmart_api_key: str = Field(
        default="",
        description="BitMart API Key (not used in public API mode)"
    )
    bitmart_api_secret: str = Field(
        default="",
        description="BitMart API Secret (not used in public API mode)"
    )
    bitmart_api_url: str = Field(
        default="https://www.bitmart.com",
        description="BitMart API базовий URL для отримання Earn продуктів"
    )

    # Gate.io налаштування
    gate_api_key: Optional[str] = Field(
        default=None,
        description="Gate.io API Key"
    )
    gate_api_secret: Optional[str] = Field(
        default=None,
        description="Gate.io API Secret"
    )
    
    # Bitget налаштування (з passphrase як в OKX)
    bitget_api_key: Optional[str] = Field(
        default=None,
        description="Bitget API Key"
    )
    bitget_api_secret: Optional[str] = Field(
        default=None,
        description="Bitget API Secret"
    )
    bitget_api_passphrase: Optional[str] = Field(
        default=None,
        description="Bitget API Passphrase (обов'язковий)"
    )
    
    # KuCoin налаштування (з passphrase v2)
    kucoin_api_key: Optional[str] = Field(
        default=None,
        description="KuCoin API Key"
    )
    kucoin_api_secret: Optional[str] = Field(
        default=None,
        description="KuCoin API Secret"
    )
    kucoin_api_passphrase: Optional[str] = Field(
        default=None,
        description="KuCoin API Passphrase (v2)"
    )
    
    # Kraken налаштування
    kraken_api_key: Optional[str] = Field(
        default=None,
        description="Kraken API Key"
    )
    kraken_api_secret: Optional[str] = Field(
        default=None,
        description="Kraken API Secret"
    )
    
    # HTX налаштування
    htx_api_key: Optional[str] = Field(
        default=None,
        description="HTX API Key"
    )
    htx_api_secret: Optional[str] = Field(
        default=None,
        description="HTX API Secret"
    )
    
    # Логування
    log_level: str = Field(default="INFO", description="Рівень логування")
    
    # Реферальні посилання для бірж (з .env)
    referral_binance: str = Field(default="https://accounts.binance.com/register?ref=YOUR_REF", alias="REFERRAL_BINANCE")
    referral_bybit: str = Field(default="https://www.bybit.com/invite?ref=YOUR_REF", alias="REFERRAL_BYBIT")
    referral_okx: str = Field(default="https://okx.com/join/YOUR_REF", alias="REFERRAL_OKX")
    referral_mexc: str = Field(default="https://promote.mexc.com/r/YOUR_REF", alias="REFERRAL_MEXC")
    referral_bitmart: str = Field(default="https://www.bitmart.com/register?referralCode=YOUR_REF", alias="REFERRAL_BITMART")
    referral_gate: str = Field(default="https://www.gate.io/signup?referralCode=YOUR_REF", alias="REFERRAL_GATE")
    referral_bitget: str = Field(default="https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF", alias="REFERRAL_BITGET")
    referral_kraken: str = Field(default="https://www.kraken.com/ref/YOUR_REF", alias="REFERRAL_KRAKEN")
    referral_kucoin: str = Field(default="https://www.kucoin.com/ref/YOUR_REF", alias="REFERRAL_KUCOIN")
    referral_htx: str = Field(default="https://www.htx.com/ref/YOUR_REF", alias="REFERRAL_HTX")
    referral_nexo: str = Field(default="https://nexo.com/ref/YOUR_REF", alias="REFERRAL_NEXO")
    
    model_config = ConfigDict(
        # Перевіряємо чи існує .env файл перед тим як встановлювати env_file
        # На Railway .env файлу немає, тому використовуємо тільки змінні середовища
        env_file=(
            Path(__file__).parent.parent.parent / ".env"
            if (Path(__file__).parent.parent.parent / ".env").exists()
            else None
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ігнорувати додаткові поля з .env
        populate_by_name=True,  # Дозволити використання alias
        # Важливо: Pydantic завжди читає змінні середовища, навіть якщо env_file встановлено
        # Змінні середовища мають пріоритет над env_file
    )


# Створюємо глобальний об'єкт налаштувань
settings = Settings()


def get_redis_url() -> str:
    """
    Формує URL для підключення до Redis.
    
    Returns:
        str: Redis URL для підключення
    """
    # Якщо встановлений REDIS_URL, використовуємо його
    if settings.redis_url:
        return settings.redis_url
    
    # Інакше формуємо URL з окремих параметрів
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    else:
        return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"

