from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Numeric,
    Enum as SqlEnum
)
from src.database import Base


class DiscountType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_type = Column(SqlEnum(DiscountType), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_order_amount = Column(Numeric(10, 2), default=0)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def is_valid(self, order_total):
        now = datetime.now()
        if not self.is_active:
            return False, "Купон неактивний"
        if self.valid_from and now < self.valid_from:
            return False, "Купон ще не діє"
        if self.valid_until and now > self.valid_until:
            return False, "Термін дії купону закінчився"
        if self.max_uses and self.used_count >= self.max_uses:
            return False, "Купон вичерпано"
        if order_total < float(self.min_order_amount):
            return False, f"Мінімальна сума замовлення для купону: {self.min_order_amount} грн"
        return True, None

    def calculate_discount(self, order_total):
        if self.discount_type == DiscountType.PERCENT:
            return round(order_total * float(self.discount_value) / 100, 2)
        return min(float(self.discount_value), order_total)
