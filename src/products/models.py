from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
)
from sqlalchemy.orm import relationship
from src.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    image_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand = Column(String(255), nullable=True)
    volume_ml = Column(Integer, nullable=True)

    retail_price = Column(Numeric(10, 2), nullable=False)
    discount_price = Column(Numeric(10, 2), nullable=True)

    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    wholesale_tiers = relationship("WholesaleTier", back_populates="product", cascade="all, delete-orphan", order_by="WholesaleTier.min_quantity")

    @property
    def main_image(self):
        for img in self.images:
            if img.is_main:
                return img.url
        if self.images:
            return self.images[0].url
        return None

    @property
    def effective_price(self):
        if self.discount_price and self.discount_price < self.retail_price:
            return self.discount_price
        return self.retail_price

    def get_price_for_quantity(self, quantity: int):
        best_price = self.effective_price
        for tier in self.wholesale_tiers:
            if quantity >= tier.min_quantity and tier.price < best_price:
                best_price = tier.price
        return best_price


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    is_main = Column(Boolean, default=False)

    product = relationship("Product", back_populates="images")


class WholesaleTier(Base):
    __tablename__ = "wholesale_tiers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

    product = relationship("Product", back_populates="wholesale_tiers")
