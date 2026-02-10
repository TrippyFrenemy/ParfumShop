"""Logger factory for creating and managing loggers."""

import logging
import logging.handlers
from typing import Optional, Dict
from pathlib import Path
import atexit

from src.logging_config.config import LogConfig
from src.logging_config.constants import LogFormat, Environment
from src.logging_config.formatters import (
    JSONFormatter,
    ColoredConsoleFormatter,
    TextFormatter,
)
from src.logging_config.filters import (
    ContextFilter,
    PIIFilter,
    SensitiveDataFilter,
    AuditLogFilter,
)
from src.logging_config.handlers import AsyncDatabaseHandler


class LoggerFactory:
    """
    Singleton factory for creating and managing loggers.

    Usage:
        factory = LoggerFactory.get_instance()
        logger = factory.get_logger(__name__)
    """

    _instance: Optional["LoggerFactory"] = None
    _initialized: bool = False

    def __init__(self, config: Optional[LogConfig] = None):
        """
        Initialize logger factory.

        Args:
            config: Optional LogConfig instance. If None, loads from environment.
        """
        if LoggerFactory._initialized:
            return

        self.config = config or LogConfig()
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: list = []
        self._db_handler: Optional[AsyncDatabaseHandler] = None

        self._configure_root_logger()
        LoggerFactory._initialized = True

        # Register cleanup
        atexit.register(self.shutdown)

    @classmethod
    def get_instance(cls, config: Optional[LogConfig] = None) -> "LoggerFactory":
        """
        Get or create singleton instance.

        Args:
            config: Optional LogConfig instance

        Returns:
            LoggerFactory singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset factory (for testing purposes)."""
        if cls._instance:
            cls._instance.shutdown()
        cls._instance = None
        cls._initialized = False

    def _configure_root_logger(self):
        """Configure the root logger with handlers and filters."""
        root = logging.getLogger()
        root.setLevel(self.config.level)

        # Clear only OUR handlers (don't touch handlers from other libraries)
        # This prevents conflicts with uvicorn, pytest, etc.
        handlers_to_remove = [h for h in root.handlers if h in self._handlers]
        for handler in handlers_to_remove:
            root.removeHandler(handler)

        # Add console handler
        if self.config.console_enabled:
            console_handler = self._create_console_handler()
            root.addHandler(console_handler)
            self._handlers.append(console_handler)

        # Add file handler
        if self.config.file_enabled:
            file_handler = self._create_file_handler()
            root.addHandler(file_handler)
            self._handlers.append(file_handler)

        # Add database handler (for audit logs)
        if self.config.db_enabled:
            db_handler = self._create_database_handler()
            root.addHandler(db_handler)
            self._handlers.append(db_handler)
            self._db_handler = db_handler

        # Configure per-module levels
        for module_name, level in self.config.module_levels.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(level)

    def _create_console_handler(self) -> logging.Handler:
        """
        Create console handler with appropriate formatter.

        Returns:
            Configured console handler
        """
        handler = logging.StreamHandler()
        handler.setLevel(self.config.console_level)

        # Select formatter based on config
        if self.config.format == LogFormat.COLORED:
            formatter = ColoredConsoleFormatter()
        elif self.config.format == LogFormat.JSON:
            formatter = JSONFormatter()
        else:
            formatter = TextFormatter()

        handler.setFormatter(formatter)

        # Add filters
        if self.config.correlation_id_enabled:
            handler.addFilter(ContextFilter())
        if self.config.pii_masking_enabled:
            handler.addFilter(PIIFilter())
        if self.config.sensitive_keys:
            handler.addFilter(SensitiveDataFilter(self.config.sensitive_keys))

        return handler

    def _create_file_handler(self) -> logging.Handler:
        """
        Create rotating file handler.

        Returns:
            Configured file handler
        """
        handler = logging.handlers.RotatingFileHandler(
            filename=self.config.file_path,
            maxBytes=self.config.file_max_bytes,
            backupCount=self.config.file_backup_count,
            encoding=self.config.file_encoding,
        )
        handler.setLevel(self.config.level)

        # Use JSON format in production for parsing
        if (
            self.config.environment == Environment.PRODUCTION
            or self.config.format == LogFormat.JSON
        ):
            formatter = JSONFormatter()
        else:
            formatter = TextFormatter()

        handler.setFormatter(formatter)

        # Add filters
        if self.config.correlation_id_enabled:
            handler.addFilter(ContextFilter())
        if self.config.pii_masking_enabled:
            handler.addFilter(PIIFilter())
        if self.config.sensitive_keys:
            handler.addFilter(SensitiveDataFilter(self.config.sensitive_keys))

        return handler

    def _create_database_handler(self) -> AsyncDatabaseHandler:
        """
        Create async database handler for audit logs.

        Returns:
            Configured database handler
        """
        handler = AsyncDatabaseHandler(
            level=getattr(logging, self.config.db_level),
            batch_size=self.config.db_async_batch_size,
            flush_interval=self.config.db_flush_interval,
        )

        # Add audit log filter (only auth and orders)
        handler.addFilter(AuditLogFilter())

        # Add context filter for correlation IDs
        if self.config.correlation_id_enabled:
            handler.addFilter(ContextFilter())

        return handler

    def get_logger(self, name: str, extra: Optional[dict] = None) -> logging.Logger:
        """
        Get or create a logger with the given name.

        Args:
            name: Logger name (typically __name__)
            extra: Extra context to include in all logs (not currently used)

        Returns:
            Configured logger instance
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)

        # Logger inherits root configuration, no need to add handlers
        # But we can set module-specific level if configured
        module_level = self.config.get_module_level(name)
        if module_level:
            logger.setLevel(module_level)

        self._loggers[name] = logger
        return logger

    def shutdown(self):
        """Cleanup handlers and flush buffers."""
        # Flush and close database handler
        if self._db_handler:
            self._db_handler.close()

        # Flush and close all handlers
        for handler in self._handlers:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass  # Ignore errors during shutdown

        self._handlers.clear()
        self._loggers.clear()


# Public API functions
def setup_logging(config: Optional[LogConfig] = None):
    """
    Initialize logging system. Call once at application startup.

    Args:
        config: Optional LogConfig instance. If None, loads from environment.

    Example:
        setup_logging()
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    LoggerFactory.get_instance(config)


def get_logger(name: str, extra: Optional[dict] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (use __name__ in modules)
        extra: Optional extra context (not currently used)

    Returns:
        Configured logger

    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": 123})
    """
    factory = LoggerFactory.get_instance()
    return factory.get_logger(name, extra)
