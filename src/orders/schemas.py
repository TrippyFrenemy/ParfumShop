from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckoutForm(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    delivery_method: str = Field(..., pattern=r"^(nova_poshta|ukrposhta)$")
    city: str = Field(..., min_length=1, max_length=255)
    city_ref: Optional[str] = Field(None, max_length=64)
    warehouse: Optional[str] = Field(None, max_length=255)
    warehouse_ref: Optional[str] = Field(None, max_length=64)
    address: Optional[str] = Field(None, max_length=500)
    comment: Optional[str] = None
    coupon_code: Optional[str] = Field(None, max_length=50)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_name: str
    product_image_url: Optional[str] = None
    price_per_unit: Decimal
    quantity: int
    total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_number: str
    status: str
    status_ua: str
    delivery_status: str
    delivery_status_ua: str
    delivery_method_ua: str
    full_name: str
    phone: str
    email: Optional[str] = None
    items: List[OrderItemOut] = []
    subtotal: Decimal
    discount_amount: Decimal
    total: Decimal
    ttn: Optional[str] = None
    created_at: datetime


class OrderListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_number: str
    status_ua: str
    total: Decimal
    created_at: datetime
    items_count: int


class OrderListOut(BaseModel):
    items: List[OrderListItem]
    total: int
    page: int
    per_page: int
    pages: int
