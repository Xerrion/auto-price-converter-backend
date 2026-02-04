"""Logging configuration for the application."""

import logging
import sys
from typing import Any

from app.core.config import get_settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Sets up structured logging with:
    - Configurable log level from settings
    - JSON-like formatting for production
    - Human-readable formatting for development
    - Console output to stdout
    """
    settings = get_settings()

    # Get log level from settings (default to INFO)
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create formatter
    if settings.environment == "production":
        # Structured format for production (easier to parse)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # More detailed format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set log levels for third-party libraries (reduce noise)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level.upper()}, "
        f"environment={settings.environment}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__ of the module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin to add logging capability to classes."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)


def log_execution_time(func):
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time
        def my_function():
            pass
    """
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        logger.debug(f"Starting {func.__name__}")

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"Completed {func.__name__} in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Failed {func.__name__} after {elapsed:.3f}s: {e}")
            raise

    return wrapper
