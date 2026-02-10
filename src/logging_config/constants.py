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
# Improved phone pattern to match more formats including international
PII_PHONE_PATTERN = r'(?:\+?380|0)[\s\-]?\(?0?\d{2,3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
PII_IP_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

# Default log rotation settings
DEFAULT_MAX_BYTES = 10_485_760  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Database handler settings
DEFAULT_BATCH_SIZE = 10
DEFAULT_FLUSH_INTERVAL = 5.0  # seconds
