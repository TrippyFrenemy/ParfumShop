from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class CartItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    price_per_unit: Decimal
    quantity: int
    line_total: Decimal

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    items: List[CartItemOut] = []
    total_items: int = 0
    total_price: Decimal = Decimal("0")

    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int
