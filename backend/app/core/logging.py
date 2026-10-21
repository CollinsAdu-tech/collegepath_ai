"""
Basic logging setup for CollegePath AI.

Per Section 43: log startup, knowledge-base loading counts, and errors.
Never log full user queries or any sensitive data here.
"""

import logging
import sys


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("collegepath")
    if logger.handlers:
        # Avoid duplicate handlers if configure_logging() is called more than once
        # (e.g. under a reloader).
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = configure_logging()
