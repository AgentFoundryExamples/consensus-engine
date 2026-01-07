"""Logging setup for Consensus Engine.

This module configures structured logging with appropriate levels
based on the application environment.
"""

import logging
import sys

from consensus_engine.config.settings import Settings


def setup_logging(settings: Settings) -> None:
    """Configure application logging based on settings.

    Args:
        settings: Application settings containing log level and debug mode
    """
    log_level = getattr(logging, settings.log_level)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("consensus_engine").setLevel(log_level)

    # Suppress overly verbose third-party loggers in production
    if not settings.debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
