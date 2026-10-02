import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIRECTORY = Path("/var/log/classsync")


def get_logger(name, level=logging.INFO):
    """
    Create and return a logger for a ClassSync job.

    Example:
        logger = get_logger("new_meetings")

    Log file:
        /var/log/classsync/new_meetings.log
    """

    # Prevent invalid or unsafe characters from being used in the filename.
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    environment = (
        "staging"
        if os.environ.get("STAGING") == "true"
        else "live"
    )

    console_only = os.environ.get("CONSOLE_ONLY") == "true"

    level = logging.DEBUG if console_only else level
    
    logger = logging.getLogger(f"classsync.{safe_name}")
    logger.setLevel(level)
    logger.propagate = False

    # Avoid adding the same handlers more than once.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | "
        f"{environment.upper()} | "
        "%(filename)s:%(lineno)d | %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if not console_only:
        log_file = LOG_DIRECTORY / f"{safe_name}-{environment}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger