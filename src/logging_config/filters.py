"""Log filters for context injection, PII masking, and sensitive data redaction."""

import logging
import re
from typing import Set, Any, Dict
import time

from src.logging_config.context import get_request_context
from src.logging_config.constants import (
    PII_EMAIL_PATTERN,
    PII_PHONE_PATTERN,
    PII_IP_PATTERN,
)


class ContextFilter(logging.Filter):
    """
    Inject request context into log records.

    Adds correlation_id, user_id, ip_address, etc. from contextvars.
    Makes context available as record attributes for formatters.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject context into record.

        Args:
            record: Log record to modify

        Returns:
            True (always allow record through)
        """
        context = get_request_context()

        # Inject context as record attributes
        for key, value in context.items():
            if not hasattr(record, key):
                setattr(record, key, value)

        return True


class PIIFilter(logging.Filter):
    """
    Mask Personally Identifiable Information (PII) in log messages.

    Patterns:
    - Email addresses
    - Phone numbers (Ukrainian format)
    - IP addresses (optional)
    """

    def __init__(
        self, mask_emails: bool = True, mask_phones: bool = True, mask_ips: bool = False
    ):
        """
        Initialize PII filter.

        Args:
            mask_emails: Mask email addresses
            mask_phones: Mask phone numbers
            mask_ips: Mask IP addresses
        """
        super().__init__()
        self.mask_emails = mask_emails
        self.mask_phones = mask_phones
        self.mask_ips = mask_ips

        # Compile patterns
        self.email_pattern = re.compile(PII_EMAIL_PATTERN) if mask_emails else None
        self.phone_pattern = re.compile(PII_PHONE_PATTERN) if mask_phones else None
        self.ip_pattern = re.compile(PII_IP_PATTERN) if mask_ips else None

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Mask PII in log message.

        Args:
            record: Log record to modify

        Returns:
            True (always allow record through)
        """
        # Mask PII in message
        if isinstance(record.msg, str):
            if self.email_pattern:
                record.msg = self.email_pattern.sub("[EMAIL]", record.msg)
            if self.phone_pattern:
                record.msg = self.phone_pattern.sub("[PHONE]", record.msg)
            if self.ip_pattern:
                record.msg = self.ip_pattern.sub("[IP]", record.msg)

        return True


class SensitiveDataFilter(logging.Filter):
    """
    Redact sensitive keys from log records.

    Removes values for keys like 'password', 'token', 'api_key', etc.
    Works recursively on nested dictionaries.
    """

    def __init__(self, sensitive_keys: Set[str] | list[str]):
        """
        Initialize sensitive data filter.

        Args:
            sensitive_keys: Set or list of keys to redact (case-insensitive)
        """
        super().__init__()
        if isinstance(sensitive_keys, list):
            sensitive_keys = set(sensitive_keys)
        self.sensitive_keys = {k.lower() for k in sensitive_keys}

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Redact sensitive data from record.

        Args:
            record: Log record to modify

        Returns:
            True (always allow record through)
        """
        # Check args for dictionaries
        if hasattr(record, "args") and isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)

        # Check all attributes for sensitive data using __dict__ (faster than dir())
        for attr_name, value in list(record.__dict__.items()):
            if not attr_name.startswith("_") and isinstance(value, dict):
                try:
                    setattr(record, attr_name, self._redact_dict(value))
                except (AttributeError, TypeError):
                    continue

        return True

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively redact sensitive keys from dictionary.

        Args:
            data: Dictionary to redact

        Returns:
            Redacted dictionary
        """
        redacted = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_keys:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted


class RateLimitFilter(logging.Filter):
    """
    Rate limit repetitive log messages to prevent log flooding.

    Useful for high-frequency operations like cache hits.
    Tracks message counts per minute and suppresses messages over threshold.
    """

    def __init__(self, max_per_minute: int = 60):
        """
        Initialize rate limit filter.

        Args:
            max_per_minute: Maximum messages per minute for same message
        """
        super().__init__()
        self.max_per_minute = max_per_minute
        self.message_counts: Dict[str, int] = {}
        self.last_reset = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Check if message should be allowed through rate limit.

        Args:
            record: Log record to check

        Returns:
            True if allowed, False if suppressed
        """
        current_time = int(time.time() / 60)  # Current minute

        # Reset counts every minute
        if current_time != self.last_reset:
            self.message_counts.clear()
            self.last_reset = current_time

        # Count this message
        msg_key = f"{record.name}:{record.levelno}:{record.msg}"
        count = self.message_counts.get(msg_key, 0)

        if count >= self.max_per_minute:
            return False  # Suppress

        self.message_counts[msg_key] = count + 1
        return True


class AuditLogFilter(logging.Filter):
    """
    Filter for audit trail - only allows critical events.

    Used with AsyncDatabaseHandler to log only auth and order events to database.
    """

    # Modules that should be logged to database
    AUDIT_MODULES = [
        "src.auth",
        "src.orders",
        "src.logs.middleware",  # Request/response logging
    ]

    # Minimum level for database logging
    MIN_LEVEL = logging.INFO

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Check if record should be logged to database.

        Args:
            record: Log record to check

        Returns:
            True if should be logged to DB, False otherwise
        """
        # Check level
        if record.levelno < self.MIN_LEVEL:
            return False

        # Check if module is in audit list
        for audit_module in self.AUDIT_MODULES:
            if record.name.startswith(audit_module):
                return True

        return False
