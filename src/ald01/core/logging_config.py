"""
ALD-01 Logging Configuration
Structured logging with rotation, colored output, and file persistence.
"""

import os
import sys
import logging
import logging.handlers
from typing import Optional

from ald01 import LOGS_DIR


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_file_mb: int = 10,
    backup_count: int = 5,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the entire ALD-01 application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging with rotation
        log_to_console: Enable console logging with colors
        max_file_mb: Max log file size in MB before rotation
        backup_count: Number of rotated log files to keep
        log_file: Custom log file path
    """
    root_logger = logging.getLogger("ald01")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Format
    file_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_format = ColoredFormatter(
        fmt="%(levelname_colored)s %(name_short)s %(message)s",
    )

    # File handler with rotation
    if log_to_file:
        log_path = log_file or os.path.join(LOGS_DIR, "ald01.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_file_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_format)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # Console handler with colors
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(console_format)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    for noisy in ["httpx", "httpcore", "uvicorn.access", "uvicorn.error", "watchfiles"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root_logger.debug("Logging configured: level=%s, file=%s", level, log_to_file)


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"
    DIM = "\033[2m"

    LEVEL_ICONS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️ ",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def format(self, record):
        # Add colored level
        color = self.COLORS.get(record.levelname, "")
        icon = self.LEVEL_ICONS.get(record.levelname, "")
        record.levelname_colored = f"{color}{icon} {record.levelname:8s}{self.RESET}"

        # Shorten logger name
        name = record.name
        if name.startswith("ald01."):
            name = name[6:]
        if len(name) > 15:
            name = name[:12] + "..."
        record.name_short = f"{self.DIM}[{name:>15s}]{self.RESET}"

        return super().format(record)


def get_log_files() -> list:
    """List all log files."""
    if not os.path.exists(LOGS_DIR):
        return []
    files = []
    for f in sorted(os.listdir(LOGS_DIR)):
        path = os.path.join(LOGS_DIR, f)
        if os.path.isfile(path):
            files.append({
                "name": f,
                "path": path,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "modified": os.path.getmtime(path),
            })
    return files


def get_recent_logs(lines: int = 100) -> str:
    """Get the last N lines from the current log file."""
    log_path = os.path.join(LOGS_DIR, "ald01.log")
    if not os.path.exists(log_path):
        return "No log file found"
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading logs: {e}"


def clear_logs() -> int:
    """Clear all log files. Returns number of files deleted."""
    if not os.path.exists(LOGS_DIR):
        return 0
    count = 0
    for f in os.listdir(LOGS_DIR):
        path = os.path.join(LOGS_DIR, f)
        if os.path.isfile(path):
            try:
                os.remove(path)
                count += 1
            except Exception:
                pass
    return count
