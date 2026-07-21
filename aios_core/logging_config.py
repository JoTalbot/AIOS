"""AIOS Logging Configuration"""

import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(level: str = "INFO", log_file: str = "aios.log"):
    """Configure structured logging for AIOS."""
    logger = logging.getLogger("aios")
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    logger.addHandler(console_handler)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )
    logger.addHandler(file_handler)

    return logger


# Default setup
logger = setup_logging()