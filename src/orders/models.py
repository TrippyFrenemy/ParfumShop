from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, ForeignKey,
    Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from src.database import Base
from src.delivery.models import DeliveryStatus  # noqa: F401 — re-exported for backwards compat


class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class DeliveryMethod(str, Enum):
    NOVA_POSHTA = "nova_poshta"
    UKRPOSHTA = "ukrposhta"


ORDER_STATUS_UA = {
    OrderStatus.CREATED: "Нове замовлення",
    OrderStatus.PAID: "Оплачено",
    OrderStatus.PROCESSING: "В обробці",
    OrderStatus.SHIPPED: "Відправлено",
    OrderStatus.CANCELLED: "Скасовано",
}

# Statuses that count towards revenue and reports
REVENUE_STATUSES = [
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
]

DELIVERY_STATUS_UA = {
    DeliveryStatus.PENDING: "Очікується",
    DeliveryStatus.IN_TRANSIT: "Доставляється",
    DeliveryStatus.DELIVERED: "Доставлено",
    DeliveryStatus.RECEIVED: "Отримано",
    DeliveryStatus.RETURNED: "Повернено",
}

DELIVERY_METHOD_UA = {
    DeliveryMethod.NOVA_POSHTA: "Нова Пошта",
    DeliveryMethod.UKRPOSHTA: "Укрпошта",
}


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(SqlEnum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    delivery_status = Column(SqlEnum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False)

    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)

    delivery_method = Column(SqlEnum(DeliveryMethod), nullable=False)
    city = Column(String(255), nullable=True)
    city_ref = Column(String(64), nullable=True)
    warehouse = Column(String(255), nullable=True)
    warehouse_ref = Column(String(64), nullable=True)
    address = Column(String(500), nullable=True)
    comment = Column(Text, nullable=True)

    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)
    total = Column(Numeric(10, 2), nullable=False)

    ttn = Column(String(30), nullable=True)
    payment_info = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    last_viewed_by = Column(String(255), nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    last_modified_by = Column(String(255), nullable=True)
    last_modified_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="orders")
    coupon = relationship("Coupon")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def status_ua(self):
        return ORDER_STATUS_UA.get(self.status, self.status)

    @property
    def delivery_status_ua(self):
        return DELIVERY_STATUS_UA.get(self.delivery_status, self.delivery_status)

    @property
    def delivery_method_ua(self):
        return DELIVERY_METHOD_UA.get(self.delivery_method, self.delivery_method)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=True)
    bundle_name = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=False)
    product_image_url = Column(String(500), nullable=True)
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    bundle = relationship("Bundle")
