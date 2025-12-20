import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from bot.config import settings


def setup_logger(name: str = "yield_telegram_bot", level: Optional[str] = None) -> logging.Logger:
    log_level = (level or settings.LOG_LEVEL).upper()

    # В продакшені зберігаємо заданий рівень для діагностики проблем
    # (раніше підвищувався до WARNING, але це заважало бачити INFO логи middleware)
    # if hasattr(settings, 'ENVIRONMENT') and settings.ENVIRONMENT and settings.ENVIRONMENT.lower() == "production":
    #     # В продакшені тільки WARNING та вище
    #     if log_level in ["DEBUG", "INFO"]:
    #         log_level = "WARNING"

    numeric_level = getattr(logging, log_level, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    if logger.handlers:
        return logger

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = TimedRotatingFileHandler(
        filename=str(logs_dir / "bot.log"), when="midnight", interval=1, backupCount=14, encoding="utf-8", utc=True
    )
    fh.setLevel(numeric_level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    eh = TimedRotatingFileHandler(
        filename=str(logs_dir / "errors.log"), when="midnight", interval=1, backupCount=14, encoding="utf-8", utc=True
    )
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    logger.addHandler(eh)

    return logger


logger = setup_logger()


