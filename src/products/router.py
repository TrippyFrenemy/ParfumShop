import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.cart.router import get_optional_user
from src.products import service
from src.products.schemas import CategoryOut, ProductOut, ProductListOut
from src.users.models import User

from src.templating import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product_to_out(product) -> dict:
    """Convert a Product ORM instance to a ProductOut-compatible dict."""
    return ProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        brand=product.brand,
        volume_ml=product.volume_ml,
        retail_price=product.retail_price,
        discount_price=product.discount_price,
        effective_price=product.effective_price,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        main_image=product.main_image,
        images=product.images,
        wholesale_tiers=product.wholesale_tiers,
        created_at=product.created_at,
        updated_at=product.updated_at,
    ).model_dump()


def _category_to_out(category) -> dict:
    """Convert a Category ORM instance to a CategoryOut-compatible dict."""
    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
        image_url=category.image_url,
        sort_order=category.sort_order,
        is_active=category.is_active,
        children_count=len(category.children) if category.children else 0,
    ).model_dump()


# =========================================================================
# HTML (template) endpoints
# =========================================================================

@router.get("/catalog", response_class=HTMLResponse)
async def catalog_page(
    request: Request,
    search: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=60),
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the full catalog page with optional filters."""
    categories = await service.get_categories(session)
    brands = await service.get_brands(session)

    products, total = await service.get_products(
        session,
        search=search,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page,
    )

    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "categories": categories,
            "current_category": None,
            "search": search or "",
            "brands": brands,
            "filters": {
                "brand": brand,
                "min_price": min_price,
                "max_price": max_price,
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
            },
        },
    )


@router.get("/catalog/{slug}", response_class=HTMLResponse)
async def category_page(
    request: Request,
    slug: str,
    search: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=60),
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the catalog page filtered by a specific category."""
    category = await service.get_category_by_slug(session, slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    categories = await service.get_categories(session)
    brands = await service.get_brands(session)

    products, total = await service.get_products(
        session,
        category_id=category.id,
        search=search,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page,
    )

    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "categories": categories,
            "current_category": category,
            "search": search or "",
            "brands": brands,
            "filters": {
                "brand": brand,
                "min_price": min_price,
                "max_price": max_price,
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
            },
        },
    )


@router.get("/product/{slug}", response_class=HTMLResponse)
async def product_detail_page(
    request: Request,
    slug: str,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Render the product detail page."""
    product = await service.get_product_by_slug(session, slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    categories = await service.get_categories(session)

    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "user": user,
            "product": product,
            "categories": categories,
        },
    )


# =========================================================================
# JSON API endpoints
# =========================================================================

@router.get("/api/products", response_model=ProductListOut)
async def api_product_list(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=60),
    session: AsyncSession = Depends(get_async_session),
):
    """Return a paginated JSON list of products."""
    products, total = await service.get_products(
        session,
        category_id=category_id,
        search=search,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page,
    )

    total_pages = math.ceil(total / per_page) if total else 1

    return ProductListOut(
        items=[
            ProductOut(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                category_id=p.category_id,
                category_name=p.category.name if p.category else None,
                brand=p.brand,
                volume_ml=p.volume_ml,
                retail_price=p.retail_price,
                discount_price=p.discount_price,
                effective_price=p.effective_price,
                stock_quantity=p.stock_quantity,
                is_active=p.is_active,
                main_image=p.main_image,
                images=p.images,
                wholesale_tiers=p.wholesale_tiers,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in products
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=total_pages,
    )


@router.get("/api/products/{product_id}", response_model=ProductOut)
async def api_product_detail(
    product_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Return a single product by ID as JSON."""
    product = await service.get_product_by_id(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        brand=product.brand,
        volume_ml=product.volume_ml,
        retail_price=product.retail_price,
        discount_price=product.discount_price,
        effective_price=product.effective_price,
        stock_quantity=product.stock_quantity,
        is_active=product.is_active,
        main_image=product.main_image,
        images=product.images,
        wholesale_tiers=product.wholesale_tiers,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("/api/categories", response_model=list[CategoryOut])
async def api_category_list(
    session: AsyncSession = Depends(get_async_session),
):
    """Return the top-level category tree as JSON."""
    categories = await service.get_categories(session)

    # Eagerly load children for each category so we can report children_count
    result = []
    for cat in categories:
        child_cats = await service.get_categories(session, parent_id=cat.id)
        result.append(
            CategoryOut(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                parent_id=cat.parent_id,
                image_url=cat.image_url,
                sort_order=cat.sort_order,
                is_active=cat.is_active,
                children_count=len(child_cats),
            )
        )

    return result
