"""Constants and enums for logging configuration."""

from enum import Enum


class LogFormat(str, Enum):
    """Log output format types."""

    JSON = "json"
    TEXT = "text"
    COLORED = "colored"


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Valid log levels
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Default sensitive keys to redact
DEFAULT_SENSITIVE_KEYS = [
    "password",
    "token",
    "secret",
    "api_key",
    "authorization",
    "auth_token",
    "access_token",
    "refresh_token",
    "jwt",
    "cookie",
    "session_id",
]

# Default module log levels (reduce noise from verbose libraries)
DEFAULT_MODULE_LEVELS = {
    "uvicorn.access": "WARNING",
    "uvicorn.error": "INFO",
    "sqlalchemy.engine": "WARNING",
    "httpx": "WARNING",
    "httpcore": "WARNING",
    "asyncio": "WARNING",
}

# PII patterns for masking
PII_EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Phone pattern with negative lookbehind/lookahead to avoid false positives in URLs/order IDs
# Matches: "+380 (67) 123-45-67", "0671234567", "+380671234567"
# Does NOT match: "PF-20671234567", "/orders/0671234567"
PII_PHONE_PATTERN = r'(?<![A-Za-z0-9\-/])(?:\+?380|0)[\s\-]?\(?0?\d{2,3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?![A-Za-z0-9\-])'

# IP patterns - supports both IPv4 and IPv6
PII_IP_V4_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# IPv6 pattern - pragmatic approach for logging
# Matches most common IPv6 formats: full, compressed with ::, localhost ::1
# Note: IPv6 regex is notoriously complex. This pattern prioritizes:
# 1. Catching real IPv6 addresses (good coverage)
# 2. Minimal false positives (word boundaries help)
# 3. Readability and maintainability
#
# If you need 100% accurate IPv6 validation, use ipaddress.ip_address() instead
PII_IP_V6_PATTERN = r'(?:(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4})'

# Combined pattern for both IPv4 and IPv6
# IPv6 pattern is intentionally broad - better to mask too much than leak IP addresses
PII_IP_PATTERN = f'(?:{PII_IP_V4_PATTERN}|{PII_IP_V6_PATTERN})'

# Default log rotation settings
DEFAULT_MAX_BYTES = 10_485_760  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Database handler settings
DEFAULT_BATCH_SIZE = 10
DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
