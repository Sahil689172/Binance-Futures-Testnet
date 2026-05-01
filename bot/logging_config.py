"""
logging_config.py
-----------------
Configures structured logging for the trading bot.
Logs are written to both the console and a rotating file in the logs/ directory.
"""

import logging
import logging.handlers
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up root logger with:
      - Console handler  (INFO and above, human-readable)
      - Rotating file handler (DEBUG and above, structured for auditing)

    Returns the root logger.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_file = os.path.join(LOG_DIR, "trading_bot.log")

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # ── Root logger ──────────────────────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # Avoid adding duplicate handlers when called multiple times
    if root_logger.handlers:
        return logging.getLogger("trading_bot")

    # ── Formatters ───────────────────────────────────────────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── File handler (rotating, max 5 MB × 3 backups) ────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)

    # ── Console handler ───────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(console_fmt)

    root_logger.addHandler(fh)
    root_logger.addHandler(ch)

    logger = logging.getLogger("trading_bot")
    logger.info("Logging initialised — file: %s", log_file)
    return logger
