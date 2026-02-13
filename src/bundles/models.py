from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base


class Bundle(Base):
    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    custom_price = Column(Numeric(10, 2), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    items = relationship("BundleItem", back_populates="bundle", cascade="all, delete-orphan")

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_available(self) -> bool:
        if not self.is_active or self.is_expired:
            return False
        return all(item.product.in_stock for item in self.items if item.product)

    @property
    def display_image(self):
        if self.image_url:
            return self.image_url
        for item in self.items:
            if item.product and item.product.main_image:
                return item.product.main_image
        return None


class BundleItem(Base):
    __tablename__ = "bundle_items"

    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    bundle = relationship("Bundle", back_populates="items")
    product = relationship("Product")
