from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class BundleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(1, ge=1)


class BundleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    custom_price: Decimal = Field(..., gt=0)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    items: list[BundleItemCreate] = Field(default_factory=list)


class BundleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    image_url: Optional[str] = None
    custom_price: Optional[Decimal] = Field(None, gt=0)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    items: Optional[list[BundleItemCreate]] = None


class AddBundleToCartRequest(BaseModel):
    bundle_id: int
    quantity: int = Field(1, ge=1)
