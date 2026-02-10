"""Async database handler for audit trail logging."""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from collections import deque
import atexit
import sys


class AsyncDatabaseHandler(logging.Handler):
    """
    Async database handler that batches log writes for performance.

    Logs are buffered and written in batches to avoid blocking.
    Suitable for audit trail logging (auth, orders), not all application logs.
    """

    def __init__(
        self, level=logging.INFO, batch_size: int = 10, flush_interval: float = 5.0,
        max_buffer_size: int = 1000
    ):
        """
        Initialize async database handler.

        Args:
            level: Minimum log level to handle
            batch_size: Number of logs to batch before writing
            flush_interval: Seconds between periodic flushes
            max_buffer_size: Maximum buffer size to prevent memory leaks
        """
        super().__init__(level)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        self._buffer: deque = deque()
        self._flush_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._closed = False
        self._consecutive_errors = 0  # Track DB errors

        # Start background flush task when event loop is available
        try:
            self._loop = asyncio.get_running_loop()
            self._flush_task = self._loop.create_task(self._flush_worker())
        except RuntimeError:
            # No event loop running yet (during startup)
            # Will be started when first log is emitted
            pass

        # Register cleanup
        atexit.register(self.close)

    def _start_flush_task_if_needed(self):
        """Start background flush task if not already running."""
        if self._flush_task is None or self._flush_task.done():
            try:
                self._loop = asyncio.get_running_loop()
                self._flush_task = self._loop.create_task(self._flush_worker())
            except RuntimeError:
                # No event loop available
                pass

    async def _flush_worker(self):
        """Background worker that flushes buffer periodically."""
        while not self._closed:
            await asyncio.sleep(self.flush_interval)
            if len(self._buffer) > 0:
                try:
                    await self._flush_buffer()
                except Exception as e:
                    # Print error to stderr (avoid recursion)
                    print(
                        f"Error in flush worker: {e}",
                        file=sys.stderr,
                    )

    def emit(self, record: logging.LogRecord):
        """
        Add log record to buffer.

        Args:
            record: Log record to buffer
        """
        if self._closed:
            return

        try:
            # Check buffer size to prevent memory leaks
            if len(self._buffer) >= self.max_buffer_size:
                print(
                    f"WARNING: Log buffer full ({self.max_buffer_size}), dropping oldest entries",
                    file=sys.stderr,
                )
                # Drop oldest entries to make room
                for _ in range(self.batch_size):
                    if self._buffer:
                        self._buffer.popleft()

            log_entry = self._record_to_dict(record)
            self._buffer.append(log_entry)

            # Start flush task if needed
            self._start_flush_task_if_needed()

            # Flush if batch size reached
            if len(self._buffer) >= self.batch_size:
                if self._loop and self._loop.is_running():
                    # Create task and track it
                    task = self._loop.create_task(self._flush_buffer())
                    # Add error callback
                    task.add_done_callback(self._handle_flush_error)
        except Exception:
            self.handleError(record)

    def _handle_flush_error(self, task: asyncio.Task):
        """Handle errors from async flush tasks."""
        try:
            task.result()  # This will raise if task failed
            self._consecutive_errors = 0  # Reset error counter on success
        except Exception as e:
            self._consecutive_errors += 1
            print(
                f"Error in async flush task (errors: {self._consecutive_errors}): {e}",
                file=sys.stderr,
            )

    def _record_to_dict(self, record: logging.LogRecord) -> dict:
        """
        Convert log record to database fields.

        Args:
            record: Log record to convert

        Returns:
            Dictionary matching UserLog model fields
        """
        # Extract user_id and request info from context
        user_id = getattr(record, "user_id", None)
        ip_address = getattr(record, "ip_address", None)
        user_agent = getattr(record, "user_agent", None)
        correlation_id = getattr(record, "correlation_id", None)
        path = getattr(record, "path", None)
        method = getattr(record, "method", None)
        status_code = getattr(record, "status_code", None)

        # Build action string
        action = record.getMessage()
        if method and path:
            action = f"{method} {path}"

        # Add correlation_id to action if available
        if correlation_id:
            action = f"[{correlation_id[:8]}] {action}"

        return {
            "user_id": user_id,
            "action": action[:500],  # Limit length
            "path": path[:500] if path else None,
            "ip_address": ip_address[:50] if ip_address else None,
            "user_agent": user_agent[:250] if user_agent else None,
            "status_code": status_code,
            "query_string": getattr(record, "query_string", None),
        }

    async def _flush_buffer(self):
        """Write buffered logs to database."""
        if not self._buffer:
            return

        # Get logs to write
        batch = []
        while self._buffer and len(batch) < self.batch_size:
            batch.append(self._buffer.popleft())

        if not batch:
            return

        try:
            # Import here to avoid circular dependency
            from src.database import async_session_maker
            from src.logs.models import UserLog

            async with async_session_maker() as session:
                for log_data in batch:
                    log = UserLog(**log_data)
                    session.add(log)
                await session.commit()

            # Success - reset error counter
            self._consecutive_errors = 0
        except Exception as e:
            self._consecutive_errors += 1

            # Only put logs back if we haven't had too many errors
            # This prevents infinite buffer growth when DB is down
            if self._consecutive_errors < 5:
                # Put logs back in buffer on temporary error
                self._buffer.extendleft(reversed(batch))
                print(
                    f"Error writing logs to database (attempt {self._consecutive_errors}): {e}",
                    file=sys.stderr,
                )
            else:
                # Too many errors - drop logs to prevent memory leak
                print(
                    f"Dropping {len(batch)} log entries after {self._consecutive_errors} consecutive DB errors",
                    file=sys.stderr,
                )

    def close(self):
        """Cleanup: flush remaining logs and cancel background task."""
        if self._closed:
            return

        self._closed = True

        # Cancel background task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()

        # Flush remaining logs (best effort)
        if self._buffer and self._loop:
            try:
                # Only try to flush if loop is running and not closed
                if self._loop.is_running() and not self._loop.is_closed():
                    # Create a task to flush (fire and forget during shutdown)
                    self._loop.create_task(self._flush_buffer())
                # Don't use run_until_complete during shutdown - too risky
            except Exception as e:
                # Log to stderr but don't raise
                print(f"Error during handler shutdown: {e}", file=sys.stderr)

        super().close()
