from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    service_api_key: str = ""
    allowed_origins: list[str] = ["http://localhost:5173"]

    redis_host: str = Field(default="localhost", description="Redis host", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, description="Redis port", alias="REDIS_PORT")
    redis_password: Optional[str] = Field(
        default=None, description="Redis password", alias="REDIS_PASSWORD"
    )
    redis_db: int = Field(default=0, description="Redis db", alias="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, description="Redis URL", alias="REDIS_URL")

    database_url: str = Field(..., description="PostgreSQL connection string", alias="DATABASE_URL")

    environment: str = Field(default="development", description="Environment", alias="ENVIRONMENT")

    cache_expiration: int = Field(default=3600, description="Cache expiration")
    update_interval: int = Field(default=3600, description="Update interval")

    binance_api_key: str = Field(default="your_binance_api_key_here", description="Binance api key")
    binance_api_secret: str = Field(
        default="your_binance_api_secret_here", description="Binance api secret"
    )
    bybit_api_key: str = Field(default="your_bybit_api_key_here", description="Bybit api key")
    bybit_api_secret: str = Field(
        default="your_bybit_api_secret_here", description="Bybit api secret"
    )

    okx_api_key: str = Field(default="your_okx_api_key_here", description="Okx api key")
    okx_api_secret: str = Field(default="your_okx_api_secret_here", description="Okx api secret")
    okx_api_passphrase: str = Field(
        default="your_okx_api_passphrase_here", description="Okx api passphrase"
    )
    okx_base_url: str = Field(default="https://www.okx.com", description="Okx base url")

    mexc_api_key: str = Field(default="", description="MEXC API Key (not used in manual mode)")
    mexc_api_secret: str = Field(
        default="", description="MEXC API Secret (not used in manual mode)"
    )
    mexc_manual_mode: bool = Field(
        default=False, description="MEXC works in manual data import mode (deprecated)"
    )
    mexc_api_url: str = Field(default="https://www.mexc.com", description="Mexc api url")

    bitmart_api_key: str = Field(
        default="", description="BitMart API Key (not used in public API mode)"
    )
    bitmart_api_secret: str = Field(
        default="", description="BitMart API Secret (not used in public API mode)"
    )
    bitmart_api_url: str = Field(default="https://www.bitmart.com", description="Bitmart api url")

    gate_api_key: Optional[str] = Field(default=None, description="Gate.io API Key")
    gate_api_secret: Optional[str] = Field(default=None, description="Gate.io API Secret")

    bitget_api_key: Optional[str] = Field(default=None, description="Bitget API Key")
    bitget_api_secret: Optional[str] = Field(default=None, description="Bitget API Secret")
    bitget_api_passphrase: Optional[str] = Field(default=None, description="Bitget api passphrase")

    kucoin_api_key: Optional[str] = Field(default=None, description="KuCoin API Key")
    kucoin_api_secret: Optional[str] = Field(default=None, description="KuCoin API Secret")
    kucoin_api_passphrase: Optional[str] = Field(
        default=None, description="KuCoin API Passphrase (v2)"
    )

    kraken_api_key: Optional[str] = Field(default=None, description="Kraken API Key")
    kraken_api_secret: Optional[str] = Field(default=None, description="Kraken API Secret")

    htx_api_key: Optional[str] = Field(default=None, description="HTX API Key")
    htx_api_secret: Optional[str] = Field(default=None, description="HTX API Secret")

    log_level: str = Field(default="INFO", description="Log level")

    referral_binance: str = Field(
        default="https://accounts.binance.com/register?ref=YOUR_REF", alias="REFERRAL_BINANCE"
    )
    referral_bybit: str = Field(
        default="https://www.bybit.com/invite?ref=YOUR_REF", alias="REFERRAL_BYBIT"
    )
    referral_okx: str = Field(default="https://okx.com/join/YOUR_REF", alias="REFERRAL_OKX")
    referral_mexc: str = Field(default="https://promote.mexc.com/r/YOUR_REF", alias="REFERRAL_MEXC")
    referral_bitmart: str = Field(
        default="https://www.bitmart.com/register?referralCode=YOUR_REF", alias="REFERRAL_BITMART"
    )
    referral_gate: str = Field(
        default="https://www.gate.io/signup?referralCode=YOUR_REF", alias="REFERRAL_GATE"
    )
    referral_bitget: str = Field(
        default="https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF",
        alias="REFERRAL_BITGET",
    )
    referral_kraken: str = Field(
        default="https://www.kraken.com/ref/YOUR_REF", alias="REFERRAL_KRAKEN"
    )
    referral_kucoin: str = Field(
        default="https://www.kucoin.com/ref/YOUR_REF", alias="REFERRAL_KUCOIN"
    )
    referral_htx: str = Field(default="https://www.htx.com/ref/YOUR_REF", alias="REFERRAL_HTX")
    referral_nexo: str = Field(default="https://nexo.com/ref/YOUR_REF", alias="REFERRAL_NEXO")

    model_config = ConfigDict(
        env_file=(
            Path(__file__).parent.parent.parent / ".env"
            if (Path(__file__).parent.parent.parent / ".env").exists()
            else None
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()


def get_redis_url() -> str:

    if settings.redis_url:
        return settings.redis_url

    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    else:
        return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
