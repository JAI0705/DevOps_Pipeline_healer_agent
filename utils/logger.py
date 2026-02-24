# utils/logger.py

"""Structured logging for the Pipeline Healer Agent."""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        for key in ("step", "repo_name", "run_id", "correlation_id", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class PrettyFormatter(logging.Formatter):
    """Human-readable colorized log format for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")

        step = getattr(record, "step", "")
        step_str = f" [{step}]" if step else ""

        duration = getattr(record, "duration_ms", None)
        duration_str = f" ({duration:.0f}ms)" if duration is not None else ""

        return (
            f"{color}{timestamp} {record.levelname:<8}{self.RESET}"
            f"{step_str} {record.getMessage()}{duration_str}"
        )


def get_logger(
    name: str = "pipeline-healer",
    level: str = "INFO",
    json_output: bool = False,
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output structured JSON; otherwise, pretty format

    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        StructuredFormatter() if json_output else PrettyFormatter()
    )
    logger.addHandler(handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return str(uuid.uuid4())[:8]


@contextmanager
def log_step(logger: logging.Logger, step_name: str, **extra: Any):
    """
    Context manager that logs the start and end of a workflow step,
    including execution time.

    Usage:
        with log_step(logger, "fetch_logs", repo_name="owner/repo"):
            # ... do work ...
    """
    start = time.perf_counter()
    logger.info(f"Starting: {step_name}", extra={"step": step_name, **extra})

    try:
        yield
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            f"Failed: {step_name} — {e}",
            extra={"step": step_name, "duration_ms": duration_ms, **extra},
            exc_info=True,
        )
        raise
    else:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Completed: {step_name}",
            extra={"step": step_name, "duration_ms": duration_ms, **extra},
        )
