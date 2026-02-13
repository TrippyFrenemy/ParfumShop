"""Settings service — thin wrapper over the ShopSettings model.

All modules should call get_shop_settings() from here instead of
accessing ShopSettings directly with session.get(ShopSettings, 1).
This creates a clean abstraction point for future extraction.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.settings.models import ShopSettings


async def get_shop_settings(session: AsyncSession) -> Optional[ShopSettings]:
    """Return the singleton ShopSettings row, or None if not yet created."""
    return await ShopSettings.get_settings(session)


async def get_shop_settings_cached(session: AsyncSession) -> Optional[dict]:
    """Return shop settings as a cached dict (10 min TTL)."""
    return await ShopSettings.get_cached(session)
