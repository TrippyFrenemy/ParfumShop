from celery import shared_task
from sqlalchemy import create_engine, text

from src.config import settings

SYNC_DB_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASS}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
engine = create_engine(SYNC_DB_URL)


@shared_task
def clean_old_logs() -> None:
    """Delete user_logs entries older than 90 days."""
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM user_logs
                    WHERE timestamp < CURRENT_DATE - INTERVAL '90 days'
                    """
                )
            )
            deleted = result.rowcount
        print(f"[CLEANUP] Deleted {deleted} old log entries (>90 days)")
    except Exception as exc:
        print(f"[CLEANUP] Failed to clean old logs: {exc}")


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
