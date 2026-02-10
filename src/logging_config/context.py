"""Request context management using contextvars for async-safe logging."""

from contextvars import ContextVar
from typing import Optional
import uuid


# Request-scoped context variable (async-safe)
request_context: ContextVar[dict] = ContextVar("request_context", default={})


def set_request_context(**kwargs) -> None:
    """
    Set request context for logging.

    Args:
        **kwargs: Key-value pairs to store in context (e.g., correlation_id, user_id, ip_address)

    Example:
        set_request_context(
            correlation_id="abc-123",
            user_id=42,
            ip_address="192.168.1.1"
        )
    """
    request_context.set(kwargs)


def get_request_context() -> dict:
    """
    Get current request context.

    Returns:
        Dictionary with context data or empty dict if no context set
    """
    return request_context.get()


def clear_request_context() -> None:
    """Clear request context (call at end of request handling)."""
    request_context.set({})


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID using UUID4.

    Returns:
        String UUID for correlation tracking
    """
    return str(uuid.uuid4())


class RequestContextManager:
    """
    Context manager for request-scoped logging context.

    Automatically sets and clears context for a block of code.
    Works with both sync and async contexts.

    Example:
        async with RequestContextManager(correlation_id="abc", user_id=123):
            logger.info("User action")  # Automatically includes context
    """

    def __init__(self, **kwargs):
        """
        Initialize context manager.

        Args:
            **kwargs: Context data to set
        """
        self.context = kwargs
        self.token: Optional[object] = None

    def __enter__(self):
        """Enter sync context."""
        self.token = request_context.set(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context."""
        if self.token:
            request_context.reset(self.token)

    async def __aenter__(self):
        """Enter async context."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        return self.__exit__(exc_type, exc_val, exc_tb)
