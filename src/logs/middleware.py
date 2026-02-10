"""User action logging middleware using new logging system."""

from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import re

from src.logging_config import (
    get_logger,
    set_request_context,
    generate_correlation_id,
    clear_request_context,
)
from src.auth.tokens import decode_token
from src.utils.ip import get_real_ip

# Get logger using new system
logger = get_logger(__name__)


class LogUserActionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Generates correlation ID for each request
    2. Extracts user context from JWT token
    3. Sets request context for all loggers
    4. Logs request/response (audit trail written to DB automatically via AsyncDatabaseHandler)
    """

    async def dispatch(self, request: Request, call_next):
        # 1. Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()

        # 2. Extract user info from JWT token
        token = request.cookies.get("Authorization", "").replace("Bearer ", "")
        user_id = None
        if token:
            try:
                payload = decode_token(token)
                user_id = int(payload.get("sub"))
            except Exception:
                pass  # Invalid token, user remains None

        # 3. Extract request info
        path = request.url.path
        method = request.method
        query = str(request.url.query)
        ip = await get_real_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        # Skip static/health check paths
        skip_patterns = [
            r"^/static/",
            r"^/favicon",
            r"^/auth/refresh$",
            r"^/health$",
        ]
        skip = any(re.match(pattern, path) for pattern in skip_patterns)

        if skip:
            return await call_next(request)

        # 4. Set request context (available to all loggers)
        set_request_context(
            correlation_id=correlation_id,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            path=path,
            method=method,
            query_string=query if query else None,
        )

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # 5. Log request (includes context automatically)
            # This will be logged to:
            # - File: logs/app_*.log (all requests)
            # - Console: stdout (if enabled)
            # - Database: user_logs table (via AsyncDatabaseHandler for audit trail)
            logger.info(
                f"{method} {path} {status_code}",
                extra={"status_code": status_code},
            )

            # 6. Add correlation ID to response headers (useful for support/debugging)
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Log error with full context
            logger.error(
                f"Request failed: {method} {path}",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            raise

        finally:
            # 7. Clear context after request (important for async safety)
            clear_request_context()


# Backward compatibility: Export logger for old imports
# This allows old code like "from src.logs.middleware import logger" to still work
# TODO: Remove this after all modules are migrated to new logging system
logger_compat = logger
