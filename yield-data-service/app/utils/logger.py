import logging
import sys
from pathlib import Path
from typing import Optional

from app.config import settings
from logging.handlers import TimedRotatingFileHandler


def setup_logger(name: str = "yield_data_service", level: Optional[str] = None) -> logging.Logger:

    log_level = level or settings.log_level

    try:
        if (
            hasattr(settings, "environment")
            and settings.environment
            and settings.environment.lower() == "production"
        ):
            if log_level.upper() in ["DEBUG", "INFO"]:
                log_level = "WARNING"
    except AttributeError:
        pass

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    if logger.handlers:
        return logger

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = TimedRotatingFileHandler(
        filename=str(logs_dir / "app.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    error_handler = TimedRotatingFileHandler(
        filename=str(logs_dir / "errors.log"),
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger


logger = setup_logger()


def log_api_request(method: str, url: str, status_code: Optional[int] = None):
    if status_code:
        logger.info(f"API {method} {url} -> {status_code}")
    else:
        logger.info(f"API {method} {url}")


def log_cache_operation(operation: str, key: str, hit: bool = None):
    if hit is True:
        logger.debug(f"Cache HIT: {operation} {key}")
    elif hit is False:
        logger.debug(f"Cache MISS: {operation} {key}")
    else:
        logger.debug(f"Cache {operation}: {key}")


def log_error(error: Exception, context: str = ""):
    context_str = f" ({context})" if context else ""
    logger.error(f"Error{context_str}: {type(error).__name__}: {error}")
