"""
Event Logger
=============
Structured logging for upload, search, access, and decrypt events.

Logs go to:
    • stdout  (always)
    • backend/logs/app.log  (file, rotating)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# ── Create log directory ─────────────────────────────────────────────────

_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")

# ── Configure root logger ───────────────────────────────────────────────

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Console handler
_console = logging.StreamHandler()
_console.setFormatter(_formatter)

# File handler (5 MB per file, keep 3 backups)
_file_handler = RotatingFileHandler(
    _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_formatter)

# Application logger
logger = logging.getLogger("e_healthshield")
logger.setLevel(logging.INFO)
logger.addHandler(_console)
logger.addHandler(_file_handler)


# ── Convenience helpers ──────────────────────────────────────────────────

def log_register(wallet: str, role: str) -> None:
    """Log a successful user registration."""
    logger.info("REGISTER | wallet=%s | role=%s", wallet, role)


def log_upload(
    wallet: str, file_id: str, filename: str, file_hash: str, tags_count: int
) -> None:
    """Log a successful file upload."""
    logger.info(
        "UPLOAD | wallet=%s | file_id=%s | filename=%s | hash=%s | tags=%d",
        wallet, file_id, filename, file_hash, tags_count,
    )


def log_search(wallet: str, keyword: str, results_count: int) -> None:
    """Log a keyword search."""
    logger.info(
        "SEARCH | wallet=%s | keyword=%s | results=%d",
        wallet, keyword, results_count,
    )


def log_access(wallet: str, file_id: str, action: str) -> None:
    """Log an access-control event (grant / revoke / check)."""
    logger.info(
        "ACCESS | wallet=%s | file_id=%s | action=%s",
        wallet, file_id, action,
    )


def log_decrypt(wallet: str, file_id: str, filename: str) -> None:
    """Log a successful file decryption."""
    logger.info(
        "DECRYPT | wallet=%s | file_id=%s | filename=%s",
        wallet, file_id, filename,
    )


def log_error(context: str, error: Exception) -> None:
    """Log an error with traceback."""
    logger.error("ERROR | context=%s | %s: %s", context, type(error).__name__, error)
