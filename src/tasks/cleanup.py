from celery import shared_task
from sqlalchemy import text

from src.tasks.db import engine


@shared_task
def clean_old_logs() -> None:
    """Delete user_logs entries older than 7 days."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM user_logs
                    WHERE timestamp < CURRENT_DATE - INTERVAL '7 days'
                    """
                )
            )
            deleted = result.rowcount
        print(f"[CLEANUP] Deleted {deleted} old log entries (>7 days)")
    except Exception as exc:
        print(f"[CLEANUP] Failed to clean old logs: {exc}")


@shared_task
def deactivate_expired_bundles() -> None:
    """Set is_active=False for bundles whose expires_at has passed."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE bundles
                    SET is_active = false
                    WHERE expires_at IS NOT NULL
                      AND expires_at <= NOW()
                      AND is_active = true
                    """
                )
            )
            updated = result.rowcount
        print(f"[CLEANUP] Deactivated {updated} expired bundles")
        if updated > 0:
            import asyncio
            from src.cache.invalidation import invalidate_bundles_cache
            asyncio.run(invalidate_bundles_cache())
            print(f"[CLEANUP] Bundles cache invalidated")
    except Exception as exc:
        print(f"[CLEANUP] Failed to deactivate expired bundles: {exc}")


@shared_task
def clean_expired_carts() -> None:
    """Delete carts that have no items and are older than 7 days."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM carts
                    WHERE id NOT IN (
                        SELECT DISTINCT cart_id FROM cart_items
                    )
                    AND updated_at < CURRENT_DATE - INTERVAL '7 days'
                    """
                )
            )
            deleted = result.rowcount
        print(f"[CLEANUP] Deleted {deleted} expired empty carts (>7 days)")
    except Exception as exc:
        print(f"[CLEANUP] Failed to clean expired carts: {exc}")
