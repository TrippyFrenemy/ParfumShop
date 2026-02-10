"""
Production-grade logging configuration module.

This module provides a centralized, senior-level logging infrastructure with:
- Structured JSON logging for log aggregation (Grafana Loki)
- Automatic correlation ID tracking for async request tracing
- PII masking and sensitive data filtering
- Log rotation with configurable size/retention
- Async database handler for audit trail
- Environment-based configuration

Usage:
    # In main.py (application startup):
    from src.logging_config import setup_logging
    setup_logging()

    # In any module:
    from src.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("User action", extra={"user_id": 123})

    # In middleware (set request context):
    from src.logging_config import set_request_context, generate_correlation_id
    set_request_context(
        correlation_id=generate_correlation_id(),
        user_id=42,
        ip_address="192.168.1.1"
    )
"""

from src.logging_config.factory import setup_logging, get_logger
from src.logging_config.context import (
    set_request_context,
    get_request_context,
    clear_request_context,
    generate_correlation_id,
    RequestContextManager,
)
from src.logging_config.config import LogConfig
from src.logging_config.constants import LogFormat, Environment

__all__ = [
    # Main API
    "setup_logging",
    "get_logger",
    # Context management
    "set_request_context",
    "get_request_context",
    "clear_request_context",
    "generate_correlation_id",
    "RequestContextManager",
    # Configuration
    "LogConfig",
    "LogFormat",
    "Environment",
]

__version__ = "1.0.0"
