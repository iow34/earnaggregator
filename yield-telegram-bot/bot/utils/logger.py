import logging
import re
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from bot.config import settings


class SecretRedactingFormatter(logging.Formatter):
    """Redact credentials from messages and formatted exception tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for name, value in settings.model_dump().items():
            if (
                any(
                    part in name.lower()
                    for part in ("password", "secret", "token", "api_key", "passphrase")
                )
                and isinstance(value, str)
                and len(value) >= 8
            ):
                rendered = rendered.replace(value, "[REDACTED]")
        rendered = re.sub(r"(://[^\s:/]+:)[^\s@]+@", r"\1[REDACTED]@", rendered)
        return rendered


def setup_logger(name: str = "yield_telegram_bot", level: Optional[str] = None) -> logging.Logger:
    log_level = (level or settings.LOG_LEVEL).upper()

    if (
        hasattr(settings, "DEPLOY_ENV")
        and settings.DEPLOY_ENV
        and settings.DEPLOY_ENV.lower() == "prod"
    ):
        if log_level in ["DEBUG", "INFO"]:
            log_level = "WARNING"

    numeric_level = getattr(logging, log_level, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    if logger.handlers:
        return logger

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    fmt = SecretRedactingFormatter(
        fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()

    if (
        hasattr(settings, "DEPLOY_ENV")
        and settings.DEPLOY_ENV
        and settings.DEPLOY_ENV.lower() == "prod"
    ):
        ch.setLevel(logging.WARNING)
    else:
        ch.setLevel(numeric_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = TimedRotatingFileHandler(
        filename=str(logs_dir / "bot.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    fh.setLevel(numeric_level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    eh = TimedRotatingFileHandler(
        filename=str(logs_dir / "errors.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    logger.addHandler(eh)

    return logger


logger = setup_logger()
