import math
from typing import Optional

from slugify import slugify
from sqlalchemy import select, func, distinct, or_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.products.models import Category, Product, ProductImage, WholesaleTier
from src.products.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
)


# =========================================================================
# Categories
# =========================================================================

async def get_categories(
    session: AsyncSession,
    parent_id: Optional[int] = None,
    active_only: bool = True,
) -> list[Category]:
    """Return categories optionally filtered by parent and active status."""
    stmt = select(Category).order_by(Category.sort_order, Category.name)

    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)
    else:
        stmt = stmt.where(Category.parent_id.is_(None))

    if active_only:
        stmt = stmt.where(Category.is_active.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_slug(
    session: AsyncSession,
    slug: str,
) -> Optional[Category]:
    """Return a single category by its slug, with eagerly loaded children."""
    stmt = (
        select(Category)
        .options(selectinload(Category.children))
        .where(Category.slug == slug)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_category(
    session: AsyncSession,
    data: CategoryCreate,
) -> Category:
    """Create a new category, auto-generating a slug from the name."""
    category = Category(
        name=data.name,
        slug=slugify(data.name),
        parent_id=data.parent_id,
        image_url=data.image_url,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def update_category(
    session: AsyncSession,
    category_id: int,
    data: CategoryUpdate,
) -> Optional[Category]:
    """Update an existing category. Returns None if not found."""
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    if category is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    # Regenerate slug when name changes
    if "name" in update_data:
        category.slug = slugify(update_data["name"])

    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(
    session: AsyncSession,
    category_id: int,
    s3_client=None,
) -> bool:
    """Delete a category. Returns True if deleted, False if not found."""
    stmt = select(Category).where(Category.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    if category is None:
        return False

    if s3_client and category.image_url:
        await s3_client.delete_by_url(category.image_url)

    await session.delete(category)
    await session.commit()
    return True


# =========================================================================
# Products
# =========================================================================

async def get_products(
    session: AsyncSession,
    *,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    brand: Optional[str] = None,
    page: int = 1,
    per_page: int = 12,
    active_only: bool = True,
) -> tuple[list[Product], int]:
    """
    Return a paginated list of products with optional filtering.

    Returns a tuple of (products, total_count).
    """
    base = select(Product).options(
        selectinload(Product.images),
        selectinload(Product.wholesale_tiers),
        selectinload(Product.category),
    )

    conditions = []

    if active_only:
        conditions.append(Product.is_active.is_(True))

    if category_id is not None:
        conditions.append(Product.category_id == category_id)

    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Product.name.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )

    if min_price is not None:
        conditions.append(Product.retail_price >= min_price)

    if max_price is not None:
        conditions.append(Product.retail_price <= max_price)

    if brand:
        conditions.append(Product.brand.ilike(brand))

    if conditions:
        base = base.where(*conditions)

    # Total count (separate lightweight query)
    count_stmt = select(func.count(Product.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginated results
    offset = (page - 1) * per_page
    stmt = base.order_by(Product.created_at.desc()).offset(offset).limit(per_page)
    result = await session.execute(stmt)
    products = list(result.scalars().unique().all())

    return products, total


async def get_product_by_slug(
    session: AsyncSession,
    slug: str,
) -> Optional[Product]:
    """Return a single product by slug with all relationships eagerly loaded."""
    stmt = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.wholesale_tiers),
            selectinload(Product.category),
        )
        .where(Product.slug == slug)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_id(
    session: AsyncSession,
    product_id: int,
) -> Optional[Product]:
    """Return a single product by ID with all relationships eagerly loaded."""
    stmt = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.wholesale_tiers),
            selectinload(Product.category),
        )
        .where(Product.id == product_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_product(
    session: AsyncSession,
    data: ProductCreate,
) -> Product:
    """Create a product together with its images and wholesale tiers."""
    product = Product(
        name=data.name,
        slug=slugify(data.name),
        description=data.description,
        category_id=data.category_id,
        brand=data.brand,
        volume_ml=data.volume_ml,
        retail_price=data.retail_price,
        discount_price=data.discount_price,
        stock_quantity=data.stock_quantity,
        is_active=data.is_active,
    )

    # Attach images
    for img_data in data.images:
        product.images.append(
            ProductImage(
                url=img_data.url,
                sort_order=img_data.sort_order,
                is_main=img_data.is_main,
            )
        )

    # Attach wholesale tiers
    for tier_data in data.wholesale_tiers:
        product.wholesale_tiers.append(
            WholesaleTier(
                min_quantity=tier_data.min_quantity,
                price=tier_data.price,
            )
        )

    session.add(product)
    await session.commit()
    await session.refresh(product, attribute_names=["images", "wholesale_tiers", "category"])
    return product


async def update_product(
    session: AsyncSession,
    product_id: int,
    data: ProductUpdate,
) -> Optional[Product]:
    """
    Update a product and optionally sync its images and wholesale tiers.

    If images or wholesale_tiers are provided in *data*, existing children are
    replaced with the new set (full sync).  Returns None if the product is not
    found.
    """
    stmt = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.wholesale_tiers),
            selectinload(Product.category),
        )
        .where(Product.id == product_id)
    )
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Handle images replacement
    new_images = update_data.pop("images", None)
    if new_images is not None:
        # Delete old images
        await session.execute(
            sa_delete(ProductImage).where(ProductImage.product_id == product_id)
        )
        product.images = [
            ProductImage(
                product_id=product_id,
                url=img["url"],
                sort_order=img.get("sort_order", 0),
                is_main=img.get("is_main", False),
            )
            for img in new_images
        ]

    # Handle wholesale tiers replacement
    new_tiers = update_data.pop("wholesale_tiers", None)
    if new_tiers is not None:
        await session.execute(
            sa_delete(WholesaleTier).where(WholesaleTier.product_id == product_id)
        )
        product.wholesale_tiers = [
            WholesaleTier(
                product_id=product_id,
                min_quantity=tier["min_quantity"],
                price=tier["price"],
            )
            for tier in new_tiers
        ]

    # Apply scalar field updates
    for field, value in update_data.items():
        setattr(product, field, value)

    # Regenerate slug when name changes
    if "name" in update_data:
        product.slug = slugify(update_data["name"])

    await session.commit()
    await session.refresh(product, attribute_names=["images", "wholesale_tiers", "category"])
    return product


async def delete_product(
    session: AsyncSession,
    product_id: int,
    s3_client=None,
) -> bool:
    """Delete a product. Returns True if deleted, False if not found."""
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        return False

    if s3_client:
        await s3_client.delete_by_prefix(f"images/products/{product_id}/")

    await session.delete(product)
    await session.commit()
    return True


# =========================================================================
# Featured & Brands
# =========================================================================

async def get_featured_products(
    session: AsyncSession,
    limit: int = 8,
) -> list[Product]:
    """
    Return featured products: those with a discount first, then the newest.

    Products with a discount_price set are prioritised; the rest are filled
    by the most recently created products up to *limit*.
    """
    stmt = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.wholesale_tiers),
            selectinload(Product.category),
        )
        .where(Product.is_active.is_(True))
        .order_by(
            # Push products with a discount to the top
            Product.discount_price.is_(None).asc(),
            Product.created_at.desc(),
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_brands(
    session: AsyncSession,
) -> list[str]:
    """Return a sorted list of distinct brand names (non-null)."""
    stmt = (
        select(distinct(Product.brand))
        .where(Product.brand.isnot(None))
        .where(Product.is_active.is_(True))
        .order_by(Product.brand)
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
