from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl, field_validator, FieldValidationInfo
from typing import Dict, Optional, List


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = Field(..., alias="BOT_TOKEN")
    DATA_SERVICE_URL: AnyUrl = Field("https://go-to-the-exchange.up.railway.app")
    DEPLOY_ENV: str = Field("prod", alias="DEPLOY_ENV")
    # Railway автоматично генерований URL для data service
    RAILWAY_SERVICE_EARNAGGREGATOR_URL: Optional[str] = Field(None, alias="RAILWAY_SERVICE_EARNAGGREGATOR_URL")
    # Актуальний public URL для data service (з RAILWAY_PUBLIC_DOMAIN earnaggregator)
    DATA_SERVICE_PUBLIC_URL: Optional[str] = Field(None, alias="DATA_SERVICE_PUBLIC_URL")
    # Публічна адреса для трекінгових посилань (для HTML посилань в Telegram)
    TRACKING_REDIRECT_URL: AnyUrl = Field("https://go-to-the-exchange.up.railway.app", alias="TRACKING_REDIRECT_URL")
    REDIS_URL: str = Field("redis://redis:6379/1")
    DATABASE_URL: str = Field(...)

    REQUEST_TIMEOUT: float = 30.0
    LOG_LEVEL: str = "INFO"

    BROADCAST_QUEUE_NAME: str = Field("broadcasts")
    BROADCAST_RATE_DELAY: float = Field(0.2)
    BROADCAST_RETRY_BASE_DELAY: float = Field(1.0)
    BROADCAST_RETRY_MAX_DELAY: float = Field(60.0)
    BROADCAST_ADMIN_BASE_URL: str = Field("http://broadcast-admin:8081")
    BROADCAST_ADMIN_API_KEY: str = Field("", alias="BROADCAST_ADMIN_API_KEY")
    BROADCAST_ADMIN_ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    BROADCAST_APPROVAL_THRESHOLD: int = Field(1000)
    BROADCAST_SCHEDULER_INTERVAL: float = Field(5.0)
    BROADCAST_SCHEDULER_BATCH_SIZE: int = Field(100)

    # Конфігурації кешування
    MAIN_MENU_TTL: int = 60  # 1 хвилина для головної сторінки (частіше оновлення APY)
    TOP10_TTL: int = 300      # 5 хвилин для топ-10 продуктів
    EXCHANGES_TTL: int = 600  # 10 хвилин для огляду бірж
    TRENDING_TTL: int = 900   # 15 хвилин для trending даних

    # Конфігурація трекінгу
    TRACKING_ENABLED: bool = Field(True)
    TRACKING_LOG_RETENTION_DAYS: int = Field(100)
    TRACKING_BATCH_SIZE: int = Field(100)
    TRACKING_BATCH_INTERVAL: int = Field(5)

    # Реферальні посилання бірж
    REFERRAL_BINANCE: str = Field("https://accounts.binance.com/register?ref=YOUR_REF")
    REFERRAL_BYBIT: str = Field("https://www.bybit.com/invite?ref=YOUR_REF")
    REFERRAL_OKX: str = Field("https://www.okx.com/join/YOUR_REF")
    REFERRAL_MEXC: str = Field("https://www.mexc.com/register?inviteCode=YOUR_REF")
    REFERRAL_BITMART: str = Field("https://www.bitmart.com/register?referralCode=YOUR_REF")
    REFERRAL_GATE: str = Field("https://www.gate.io/signup?referralCode=YOUR_REF")
    REFERRAL_BITGET: str = Field("https://www.bitget.com/referral/register?from=referral&clacCode=YOUR_REF")
    REFERRAL_KRAKEN: str = Field("https://www.kraken.com/ref/YOUR_REF")
    REFERRAL_KUCOIN: str = Field("https://www.kucoin.com/ref/YOUR_REF")
    REFERRAL_HTX: str = Field("https://www.htx.com/ref/YOUR_REF")
    REFERRAL_NEXO: str = Field("https://nexo.io/ref/YOUR_REF")
    
    # Трекінгові посилання (fallback якщо динамічна генерація не працює)
    TRACK_BINANCE_PAGE1: str = Field("", alias="TRACK_BINANCE_PAGE1")
    TRACK_BINANCE_PAGE2: str = Field("", alias="TRACK_BINANCE_PAGE2")
    TRACK_BINANCE_PAGE3: str = Field("", alias="TRACK_BINANCE_PAGE3")
    TRACK_BYBIT_PAGE1: str = Field("", alias="TRACK_BYBIT_PAGE1")
    TRACK_BYBIT_PAGE2: str = Field("", alias="TRACK_BYBIT_PAGE2")
    TRACK_BYBIT_PAGE3: str = Field("", alias="TRACK_BYBIT_PAGE3")
    TRACK_OKX_PAGE1: str = Field("", alias="TRACK_OKX_PAGE1")
    TRACK_OKX_PAGE2: str = Field("", alias="TRACK_OKX_PAGE2")
    TRACK_OKX_PAGE3: str = Field("", alias="TRACK_OKX_PAGE3")
    TRACK_MEXC_PAGE1: str = Field("", alias="TRACK_MEXC_PAGE1")
    TRACK_MEXC_PAGE2: str = Field("", alias="TRACK_MEXC_PAGE2")
    TRACK_MEXC_PAGE3: str = Field("", alias="TRACK_MEXC_PAGE3")
    TRACK_BITMART_PAGE1: str = Field("", alias="TRACK_BITMART_PAGE1")
    TRACK_BITMART_PAGE2: str = Field("", alias="TRACK_BITMART_PAGE2")
    TRACK_BITMART_PAGE3: str = Field("", alias="TRACK_BITMART_PAGE3")
    TRACK_GATE_PAGE1: str = Field("", alias="TRACK_GATE_PAGE1")
    TRACK_GATE_PAGE2: str = Field("", alias="TRACK_GATE_PAGE2")
    TRACK_GATE_PAGE3: str = Field("", alias="TRACK_GATE_PAGE3")
    TRACK_BITGET_PAGE1: str = Field("", alias="TRACK_BITGET_PAGE1")
    TRACK_BITGET_PAGE2: str = Field("", alias="TRACK_BITGET_PAGE2")
    TRACK_BITGET_PAGE3: str = Field("", alias="TRACK_BITGET_PAGE3")
    TRACK_KRAKEN_PAGE1: str = Field("", alias="TRACK_KRAKEN_PAGE1")
    TRACK_KRAKEN_PAGE2: str = Field("", alias="TRACK_KRAKEN_PAGE2")
    TRACK_KRAKEN_PAGE3: str = Field("", alias="TRACK_KRAKEN_PAGE3")
    TRACK_KUCOIN_PAGE1: str = Field("", alias="TRACK_KUCOIN_PAGE1")
    TRACK_KUCOIN_PAGE2: str = Field("", alias="TRACK_KUCOIN_PAGE2")
    TRACK_KUCOIN_PAGE3: str = Field("", alias="TRACK_KUCOIN_PAGE3")
    TRACK_HTX_PAGE1: str = Field("", alias="TRACK_HTX_PAGE1")
    TRACK_HTX_PAGE2: str = Field("", alias="TRACK_HTX_PAGE2")
    TRACK_HTX_PAGE3: str = Field("", alias="TRACK_HTX_PAGE3")
    TRACK_NEXO_PAGE1: str = Field("", alias="TRACK_NEXO_PAGE1")
    TRACK_NEXO_PAGE2: str = Field("", alias="TRACK_NEXO_PAGE2")
    TRACK_NEXO_PAGE3: str = Field("", alias="TRACK_NEXO_PAGE3")

    @field_validator("TRACKING_REDIRECT_URL", "DATA_SERVICE_URL", mode="before")
    @classmethod
    def _ensure_public_urls(cls, value: str | AnyUrl | None, info: FieldValidationInfo):
        """
        Prevent internal/localhost URLs in production to avoid broken links during ads review.
        """
        if value is None:
            return value

        env = (info.data.get("DEPLOY_ENV") or "prod").lower() if hasattr(info, "data") else "prod"
        url_str = str(value)

        if env == "prod":
            forbidden_hosts = ("localhost", "127.0.0.1", "yield-api")
            if any(host in url_str for host in forbidden_hosts):
                raise ValueError("Public URL required: tracking/data endpoints must be reachable outside the cluster")
        return value

    @field_validator("BROADCAST_ADMIN_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if value in (None, "", []):
            return ["*"]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def data_service_url(self) -> str:
        """
        Повертає правильний URL для data service.

        Пріоритет:
        1. DATA_SERVICE_PUBLIC_URL (з RAILWAY_PUBLIC_DOMAIN earnaggregator сервісу)
        2. RAILWAY_SERVICE_EARNAGGREGATOR_URL (Railway auto-generated)
        3. DATA_SERVICE_URL (fallback)
        """
        # Найвищий пріоритет - URL з RAILWAY_PUBLIC_DOMAIN earnaggregator
        if self.DATA_SERVICE_PUBLIC_URL:
            return self.DATA_SERVICE_PUBLIC_URL

        # Другий пріоритет - Railway auto-generated URL
        if self.RAILWAY_SERVICE_EARNAGGREGATOR_URL:
            # Railway автоматично генерує URL без https://
            if self.RAILWAY_SERVICE_EARNAGGREGATOR_URL.startswith('http'):
                return self.RAILWAY_SERVICE_EARNAGGREGATOR_URL
            else:
                return f"https://{self.RAILWAY_SERVICE_EARNAGGREGATOR_URL}"

        # Fallback
        return str(self.DATA_SERVICE_URL)

    @property
    def referral_urls(self) -> Dict[str, str]:
        """Повертає словник реферальних посилань."""
        return {
            "binance": self.REFERRAL_BINANCE,
            "bybit": self.REFERRAL_BYBIT,
            "okx": self.REFERRAL_OKX,
            "mexc": self.REFERRAL_MEXC,
            "bitmart": self.REFERRAL_BITMART,
            "gate": self.REFERRAL_GATE,
            "bitget": self.REFERRAL_BITGET,
            "kraken": self.REFERRAL_KRAKEN,
            "kucoin": self.REFERRAL_KUCOIN,
            "htx": self.REFERRAL_HTX,
            "nexo": self.REFERRAL_NEXO
        }
    
    def get_tracking_link(self, exchange: str, page: str) -> Optional[str]:
        """
        Отримати статичне трекінгове посилання з .env (fallback).
        
        Args:
            exchange: Назва біржі (lowercase)
            page: Номер сторінки (1, 2, 3)
            
        Returns:
            Трекінгове посилання або None
        """
        exchange_upper = exchange.upper()
        page_key = f"PAGE{page}"
        attr_name = f"TRACK_{exchange_upper}_{page_key}"
        
        try:
            link = getattr(self, attr_name, None)
            if link and link.strip():
                return link.strip()
        except AttributeError:
            pass
        
        return None

    class Config:
        # Prefer environment variables; fallback to project .env if present
        # В Docker контейнері .env монтується як volume в /app/.env
        # Pydantic автоматично читає з environment variables, а також з .env файлу
        from pathlib import Path
        import os
        
        # Визначаємо шлях до .env файлу
        # В Docker: /app/.env, локально: відносний шлях
        env_file_paths = [
            "/app/.env",  # Docker контейнер
            Path(__file__).parent.parent.parent.parent / ".env",  # Локально (project root)
            ".env"  # Поточна директорія
        ]
        
        env_file = None
        for path in env_file_paths:
            check_path = Path(path) if isinstance(path, str) else path
            if check_path.exists():
                env_file = str(check_path)
                break
        
        # Якщо не знайдено - використовуємо стандартний шлях
        if env_file is None:
            env_file = ".env"
        
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


