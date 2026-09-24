import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Module logger. Level comes from $LOG_LEVEL (default INFO); pytest captures it into reports."""
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    return logger
