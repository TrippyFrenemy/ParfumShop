from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Validate coupon (public endpoint)
# ---------------------------------------------------------------------------

class CouponValidateRequest(BaseModel):
    code: str
    cart_total: float = Field(..., gt=0)
    products_total: Optional[float] = None  # total of non-bundle items; used when applies_to_bundles=False


class CouponValidateResponse(BaseModel):
    valid: bool
    message: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    estimated_discount: Optional[float] = None


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------

class CouponCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    discount_type: str = Field(..., description="percent or fixed")
    discount_value: Decimal = Field(..., gt=0, decimal_places=2)
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    max_uses: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True
    applies_to_bundles: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class CouponUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    min_order_amount: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    max_uses: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None
    applies_to_bundles: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: str
    discount_value: Decimal
    min_order_amount: Decimal
    max_uses: Optional[int] = None
    used_count: int
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
