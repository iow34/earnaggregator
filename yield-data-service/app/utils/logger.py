"""
Налаштування логування для Data Service.

Цей модуль налаштовує логування для всього проекту:
- Форматування повідомлень
- Рівні логування
- Вивід в консоль та файл
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from app.config import settings
from logging.handlers import TimedRotatingFileHandler


def setup_logger(
    name: str = "yield_data_service",
    level: Optional[str] = None
) -> logging.Logger:
    """
    Налаштовує логер для проекту.
    
    Args:
        name: Назва логера
        level: Рівень логування (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        logging.Logger: Налаштований логер
    """
    
    # Визначаємо рівень логування
    log_level = level or settings.log_level

    # В продакшені підвищуємо рівень до WARNING для зменшення кількості логів
    if settings.environment and settings.environment.lower() == "production":
        # В продакшені тільки WARNING та вище
        if log_level.upper() in ["DEBUG", "INFO"]:
            log_level = "WARNING"

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Створюємо логер
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Перевіряємо чи логер вже налаштований
    if logger.handlers:
        return logger
    
    # Створюємо директорію для логів
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Формат повідомлень
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Консольний handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловий handler (добова ротація)
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
    
    # Логер для помилок (окремий файл з ротацією)
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


# Створюємо глобальний логер
logger = setup_logger()


def log_api_request(method: str, url: str, status_code: Optional[int] = None):
    """
    Логує API запити.
    
    Args:
        method: HTTP метод (GET, POST, etc.)
        url: URL запиту
        status_code: HTTP статус код відповіді
    """
    if status_code:
        logger.info(f"API {method} {url} -> {status_code}")
    else:
        logger.info(f"API {method} {url}")


def log_cache_operation(operation: str, key: str, hit: bool = None):
    """
    Логує операції з кешем.
    
    Args:
        operation: Тип операції (GET, SET, DELETE)
        key: Ключ кешу
        hit: True якщо cache hit, False якщо cache miss, None для інших операцій
    """
    if hit is True:
        logger.debug(f"Cache HIT: {operation} {key}")
    elif hit is False:
        logger.debug(f"Cache MISS: {operation} {key}")
    else:
        logger.debug(f"Cache {operation}: {key}")


def log_error(error: Exception, context: str = ""):
    """
    Логує помилки з контекстом.
    
    Args:
        error: Об'єкт помилки
        context: Додатковий контекст
    """
    context_str = f" ({context})" if context else ""
    logger.error(f"Error{context_str}: {type(error).__name__}: {error}")
