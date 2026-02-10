"""Log formatters for different output formats."""

import logging
import json
from datetime import datetime
from typing import Any, Dict
import socket
import os

from src.logging_config.context import get_request_context


class BaseFormatter(logging.Formatter):
    """Base formatter with common functionality."""

    def __init__(self):
        """Initialize base formatter."""
        super().__init__()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def get_base_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Extract common fields from log record.

        Args:
            record: Log record to extract from

        Returns:
            Dictionary with common log fields
        """
        fields = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info for errors
        if record.levelno >= logging.ERROR:
            fields.update(
                {
                    "file": record.pathname,
                    "line": record.lineno,
                    "function": record.funcName,
                }
            )

        # Add exception info
        if record.exc_info:
            fields["exception"] = self.formatException(record.exc_info)

        # Add process info
        fields["hostname"] = self.hostname
        fields["pid"] = self.pid

        # Add request context
        context = get_request_context()
        if context:
            fields["context"] = context

        # Add extra fields (from logger.info(..., extra={}))
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName", "levelname",
            "levelno", "lineno", "module", "msecs", "pathname", "process",
            "processName", "relativeCreated", "thread", "threadName", "exc_info",
            "exc_text", "stack_info", "getMessage", "message", "hostname", "pid",
            "timestamp", "level", "logger", "exception", "context", "extra",
        }

        # Use __dict__ instead of dir() for better performance
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                if value is not None and not callable(value):
                    if "extra" not in fields:
                        fields["extra"] = {}
                    fields["extra"][key] = value

        return fields


class JSONFormatter(BaseFormatter):
    """JSON formatter for structured logging (production, Grafana Loki)."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        fields = self.get_base_fields(record)
        return json.dumps(fields, ensure_ascii=False, default=str)


class TextFormatter(BaseFormatter):
    """Human-readable text formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as text.

        Args:
            record: Log record to format

        Returns:
            Formatted text string
        """
        fields = self.get_base_fields(record)

        # Build log line
        parts = [
            fields["timestamp"],
            f"[{fields['level']}]",
            f"{fields['logger']}:",
            fields["message"],
        ]

        # Add correlation ID if present (short form for readability)
        if "context" in fields and "correlation_id" in fields["context"]:
            corr_id = fields["context"]["correlation_id"][:8]
            parts.insert(2, f"[{corr_id}]")

        log_line = " ".join(parts)

        # Add exception on new line
        if "exception" in fields:
            log_line += "\n" + fields["exception"]

        return log_line


class ColoredConsoleFormatter(TextFormatter):
    """Colored console formatter for development (ANSI colors)."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Colored formatted string
        """
        log_line = super().format(record)
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        return f"{color}{log_line}{self.COLORS['RESET']}"


class AuditFormatter(BaseFormatter):
    """
    Specialized formatter for audit logs (security, compliance).

    Always includes full context and file location.
    Never filtered, used for compliance purposes.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format audit log record.

        Args:
            record: Log record to format

        Returns:
            JSON formatted audit log
        """
        fields = self.get_base_fields(record)

        # Always include full file location for audit
        fields.update(
            {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        )

        # Mark as audit log
        fields["log_type"] = "audit"

        return json.dumps(fields, ensure_ascii=False, default=str, indent=2)
