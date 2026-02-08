from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# ProductImage
# ---------------------------------------------------------------------------

class ProductImageCreate(BaseModel):
    url: str
    sort_order: int = 0
    is_main: bool = False


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    sort_order: int
    is_main: bool


# ---------------------------------------------------------------------------
# WholesaleTier
# ---------------------------------------------------------------------------

class WholesaleTierCreate(BaseModel):
    min_quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0, decimal_places=2)


class WholesaleTierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    min_quantity: int
    price: Decimal


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: int
    is_active: bool
    children_count: int = 0


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand: Optional[str] = Field(None, max_length=255)
    volume_ml: Optional[int] = None
    retail_price: Decimal = Field(..., gt=0, decimal_places=2)
    discount_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_start: Optional[datetime] = None
    discount_end: Optional[datetime] = None
    in_stock: bool = True
    is_active: bool = True


class ProductCreate(ProductBase):
    images: list[ProductImageCreate] = []
    wholesale_tiers: list[WholesaleTierCreate] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand: Optional[str] = Field(None, max_length=255)
    volume_ml: Optional[int] = None
    retail_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    discount_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    discount_start: Optional[datetime] = None
    discount_end: Optional[datetime] = None
    in_stock: Optional[bool] = None
    is_active: Optional[bool] = None
    images: Optional[list[ProductImageCreate]] = None
    wholesale_tiers: Optional[list[WholesaleTierCreate]] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    brand: Optional[str] = None
    volume_ml: Optional[int] = None
    retail_price: Decimal
    discount_price: Optional[Decimal] = None
    discount_start: Optional[datetime] = None
    discount_end: Optional[datetime] = None
    is_discount_active: bool = False
    effective_price: Decimal
    in_stock: bool
    is_active: bool
    main_image: Optional[str] = None
    images: list[ProductImageOut] = []
    wholesale_tiers: list[WholesaleTierOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Paginated product list
# ---------------------------------------------------------------------------

class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    per_page: int
    pages: int
