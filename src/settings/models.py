from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import Base
from src.cache.decorators import cache_result


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id = Column(Integer, primary_key=True, default=1)
    shop_name = Column(String(255), default="ParfumShop")
    min_order_amount = Column(Numeric(10, 2), default=0)
    payment_info_text = Column(Text, nullable=True)
    contacts_text = Column(Text, nullable=True)
    shop_phone = Column(String(50), nullable=True)
    shop_email = Column(String(255), nullable=True)
    about_text = Column(Text, nullable=True)
    show_out_of_stock = Column(Boolean, default=False, server_default="0")

    @classmethod
    async def get_settings(cls, session: AsyncSession) -> Optional["ShopSettings"]:
        """
        Get shop settings from database.

        Note: Caching removed - SQLAlchemy objects are not JSON serializable.
        For cached settings, convert to dict first.

        Returns:
            ShopSettings instance or None
        """
        stmt = select(cls).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    @cache_result(namespace="settings", ttl=600, key_builder=lambda cls, session: "shop:global")
    async def get_cached(cls, session: AsyncSession) -> Optional[dict]:
        """
        Get shop settings as dictionary from cache or database.
        Cached for 10 minutes.

        Returns:
            Settings dictionary or None
        """
        settings = await cls.get_settings(session)
        if settings is None:
            return None

        # Convert to dictionary for JSON serialization
        return {
            "id": settings.id,
            "shop_name": settings.shop_name,
            "min_order_amount": float(settings.min_order_amount) if settings.min_order_amount else 0.0,
            "payment_info_text": settings.payment_info_text,
            "contacts_text": settings.contacts_text,
            "shop_phone": settings.shop_phone,
            "shop_email": settings.shop_email,
            "about_text": settings.about_text,
            "show_out_of_stock": settings.show_out_of_stock,
        }
