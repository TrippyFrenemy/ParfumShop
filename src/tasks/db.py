"""Shared synchronous SQLAlchemy engine for Celery tasks.

All task modules should import `engine` from here instead of creating
their own connection pool. This reduces resource usage and centralises
database configuration.
"""
from sqlalchemy import create_engine

from src.config import settings

_SYNC_DB_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASS}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# Single shared engine for all Celery tasks.
# pool_pre_ping ensures stale connections are recycled automatically.
engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)
