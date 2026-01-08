"""Structured logging configuration for DSPy Jira Feedback."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to console.
        log_format: Log message format string

    Returns:
        Configured root logger for the application
    """
    # Get the root logger for our application
    logger = logging.getLogger("jira_feedback")

    # Clear any existing handlers
    logger.handlers.clear()

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Console handler - always add
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler - optional
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"jira_feedback.{name}")


# Module-level loggers for each component
class Loggers:
    """Container for application loggers."""

    app: logging.Logger
    config: logging.Logger
    jira: logging.Logger
    cache: logging.Logger
    pipeline: logging.Logger
    rubric: logging.Logger
    feedback: logging.Logger

    @classmethod
    def init(cls) -> None:
        """Initialize all module loggers."""
        cls.app = get_logger("app")
        cls.config = get_logger("config")
        cls.jira = get_logger("jira")
        cls.cache = get_logger("cache")
        cls.pipeline = get_logger("pipeline")
        cls.rubric = get_logger("rubric")
        cls.feedback = get_logger("feedback")


def configure_from_env(
    log_level_env: str = "LOG_LEVEL",
    log_file_env: str = "LOG_FILE",
    default_level: str = "INFO",
) -> logging.Logger:
    """
    Configure logging from environment variables.

    Args:
        log_level_env: Environment variable name for log level
        log_file_env: Environment variable name for log file path
        default_level: Default log level if env var not set

    Returns:
        Configured logger
    """
    import os

    level = os.getenv(log_level_env, default_level)
    log_file_str = os.getenv(log_file_env)
    log_file = Path(log_file_str) if log_file_str else None

    logger = setup_logging(level=level, log_file=log_file)
    Loggers.init()

    return logger
