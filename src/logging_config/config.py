"""Logging configuration using Pydantic settings."""

from pathlib import Path
from typing import Dict, Optional
import platform

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.logging_config.constants import (
    LogFormat,
    Environment,
    LOG_LEVELS,
    DEFAULT_SENSITIVE_KEYS,
    DEFAULT_MODULE_LEVELS,
    DEFAULT_MAX_BYTES,
    DEFAULT_BACKUP_COUNT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_FLUSH_INTERVAL,
)


class LogConfig(BaseSettings):
    """Centralized logging configuration using Pydantic."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env variables
    )

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )

    # Global settings
    level: str = Field(default="INFO", description="Root logger level")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Log format")

    # File logging
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: Optional[Path] = Field(default=None, description="Log file path")
    file_max_bytes: int = Field(
        default=DEFAULT_MAX_BYTES, description="Max file size before rotation"
    )
    file_backup_count: int = Field(
        default=DEFAULT_BACKUP_COUNT, description="Number of backup files to keep"
    )
    file_encoding: str = Field(default="utf-8", description="File encoding")

    # Console logging
    console_enabled: bool = Field(default=True, description="Enable console logging")
    console_level: str = Field(default="DEBUG", description="Console log level")

    # Database audit logging
    db_enabled: bool = Field(default=True, description="Enable database audit logging")
    db_level: str = Field(
        default="INFO", description="Minimum level for DB logs"
    )
    db_async_batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE, description="Batch size for async DB writes"
    )
    db_flush_interval: float = Field(
        default=DEFAULT_FLUSH_INTERVAL, description="Seconds between batch flushes"
    )

    # Security
    pii_masking_enabled: bool = Field(
        default=True, description="Mask PII in logs (email, phone)"
    )
    sensitive_keys: list[str] = Field(
        default_factory=lambda: DEFAULT_SENSITIVE_KEYS.copy(),
        description="Keys to redact from logs",
    )

    # Performance
    async_logging: bool = Field(
        default=True, description="Use async handlers where possible"
    )
    buffer_size: int = Field(default=1000, description="Handler buffer size")

    # Per-module levels
    module_levels: Dict[str, str] = Field(
        default_factory=lambda: DEFAULT_MODULE_LEVELS.copy(),
        description="Per-module log levels",
    )

    # Request tracing
    correlation_id_enabled: bool = Field(
        default=True, description="Generate correlation IDs"
    )
    correlation_id_header: str = Field(
        default="X-Correlation-ID", description="HTTP header for correlation ID"
    )

    # Structured logging fields
    include_hostname: bool = Field(default=True, description="Include hostname in logs")
    include_process_info: bool = Field(
        default=True, description="Include process ID in logs"
    )
    include_thread_info: bool = Field(
        default=False, description="Include thread info in logs"
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: Optional[Path], info) -> Path:
        """Generate platform-appropriate log path if not specified."""
        if v is not None:
            return v

        # Determine base directory
        if platform.system() == "Windows":
            base_dir = Path.cwd() / "logs"
        else:
            # Check if running in Docker
            docker_path = Path("/fastapi_app/logs")
            if docker_path.parent.exists():
                base_dir = docker_path
            else:
                base_dir = Path.cwd() / "logs"

        base_dir.mkdir(parents=True, exist_ok=True)

        # Separate log files by type
        env = info.data.get("environment", Environment.DEVELOPMENT)
        if isinstance(env, Environment):
            env_name = env.value
        else:
            env_name = str(env)

        return base_dir / f"app_{env_name}.log"

    @field_validator("level", "console_level", "db_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        v_upper = v.upper()
        if v_upper not in LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: {v}. Must be one of {LOG_LEVELS}"
            )
        return v_upper

    def get_module_level(self, module_name: str) -> Optional[str]:
        """
        Get log level for a specific module.

        Args:
            module_name: Module name (e.g., "src.auth.router")

        Returns:
            Log level string or None if not configured
        """
        return self.module_levels.get(module_name)
