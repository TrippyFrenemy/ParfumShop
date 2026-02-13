"""Settings domain — public API surface."""
from src.settings.service import get_shop_settings, get_shop_settings_cached

__all__ = ["get_shop_settings", "get_shop_settings_cached"]
