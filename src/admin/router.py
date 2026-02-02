import math
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from slugify import slugify
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_manager_or_admin
from src.database import get_async_session
from src.orders.models import Order, OrderStatus
from src.orders.service import (
    get_all_orders,
    get_order_by_number,
    get_order_stats,
    update_order_status,
    update_order_ttn,
)
from src.products.models import Product, Category
from src.products.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductImageCreate,
    ProductUpdate,
    WholesaleTierCreate,
)
from src.products.service import (
    create_category,
    create_product,
    delete_category,
    delete_product,
    get_categories,
    get_products,
    update_category,
    update_product,
)
from src.coupons.models import Coupon, DiscountType
from src.coupons.schemas import CouponCreate
from src.coupons.service import (
    create_coupon,
    delete_coupon,
    get_all_coupons,
)
from src.settings.models import ShopSettings
from src.users.models import User

from src.templating import templates

router = APIRouter()


# =========================================================================
# Dashboard
# =========================================================================

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    stats = await get_order_stats(session)

    # Active products count
    active_count = (
        await session.execute(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        )
    ).scalar() or 0
    stats["active_products_count"] = active_count

    # Low stock products (stock_quantity <= 5 and active)
    low_stock = (
        await session.execute(
            select(func.count(Product.id)).where(
                Product.is_active.is_(True),
                Product.stock_quantity <= 5,
            )
        )
    ).scalar() or 0
    stats["low_stock_products"] = low_stock

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "active_page": "dashboard",
        },
    )


# =========================================================================
# Products
# =========================================================================

@router.get("/products", response_class=HTMLResponse)
async def admin_products_list(
    request: Request,
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    cat_id = int(category_id) if category_id else None
    products, total = await get_products(
        session,
        search=search,
        category_id=cat_id,
        page=page,
        per_page=per_page,
        active_only=False,
    )
    categories = await get_categories(session, active_only=False)
    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "admin/products/list.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "categories": categories,
            "search": search or "",
            "category_id": category_id or "",
            "page": page,
            "total_pages": total_pages,
            "active_page": "products",
        },
    )


@router.get("/products/create", response_class=HTMLResponse)
async def admin_product_create_form(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    categories = await get_categories(session, active_only=False)
    return templates.TemplateResponse(
        "admin/products/form.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "active_page": "products",
        },
    )


@router.post("/products/create")
async def admin_product_create(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    volume_ml: Optional[str] = Form(None),
    retail_price: str = Form(...),
    discount_price: Optional[str] = Form(None),
    stock_quantity: str = Form("0"),
    image_files: list[UploadFile] = File(default=[]),
    tier_quantities: Optional[str] = Form(None),
    tier_prices: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    tiers = []
    if tier_quantities and tier_prices:
        qtys = [q.strip() for q in tier_quantities.split(",") if q.strip()]
        prices = [p.strip() for p in tier_prices.split(",") if p.strip()]
        for q, p in zip(qtys, prices):
            try:
                tiers.append(WholesaleTierCreate(min_quantity=int(q), price=Decimal(p)))
            except (ValueError, TypeError):
                pass

    data = ProductCreate(
        name=name,
        description=description or None,
        category_id=int(category_id) if category_id else None,
        brand=brand or None,
        volume_ml=int(volume_ml) if volume_ml else None,
        retail_price=Decimal(retail_price),
        discount_price=Decimal(discount_price) if discount_price else None,
        stock_quantity=int(stock_quantity),
        is_active=is_active == "1",
        images=[],
        wholesale_tiers=tiers,
    )

    product = await create_product(session, data)

    # Upload images to S3
    from src.products.models import ProductImage as ProductImageModel
    from src.utils.s3 import get_s3_client, validate_image_upload

    s3 = get_s3_client()
    for i, file in enumerate(image_files):
        if file.filename and file.size:
            file_data = await validate_image_upload(file)
            url = await s3.upload_product_image(file_data, product.id, file.filename)
            session.add(ProductImageModel(
                product_id=product.id,
                url=url,
                sort_order=i,
                is_main=(i == 0),
            ))
    await session.commit()

    return RedirectResponse("/admin/products?success=Товар+створено", status_code=302)


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def admin_product_edit_form(
    request: Request,
    product_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from src.products.service import get_product_by_id

    product = await get_product_by_id(session, product_id)
    if not product:
        return RedirectResponse("/admin/products?error=Товар+не+знайдено", status_code=302)

    categories = await get_categories(session, active_only=False)
    return templates.TemplateResponse(
        "admin/products/form.html",
        {
            "request": request,
            "user": user,
            "product": product,
            "categories": categories,
            "active_page": "products",
        },
    )


@router.post("/products/{product_id}/edit")
async def admin_product_edit(
    request: Request,
    product_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    volume_ml: Optional[str] = Form(None),
    retail_price: str = Form(...),
    discount_price: Optional[str] = Form(None),
    stock_quantity: str = Form("0"),
    existing_image_urls: Optional[list[str]] = Form(None),
    image_files: list[UploadFile] = File(default=[]),
    tier_quantities: Optional[str] = Form(None),
    tier_prices: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from src.products.service import get_product_by_id
    from src.utils.s3 import get_s3_client, validate_image_upload

    product = await get_product_by_id(session, product_id)
    if not product:
        return RedirectResponse("/admin/products?error=Товар+не+знайдено", status_code=302)

    old_image_urls = {img.url for img in product.images}

    # Build new image list: retained existing + newly uploaded
    images = []
    sort_idx = 0

    retained_urls = set()
    if existing_image_urls:
        for url in existing_image_urls:
            url = url.strip()
            if url:
                images.append({"url": url, "sort_order": sort_idx, "is_main": (sort_idx == 0)})
                retained_urls.add(url)
                sort_idx += 1

    s3 = get_s3_client()
    for file in image_files:
        if file.filename and file.size:
            file_data = await validate_image_upload(file)
            url = await s3.upload_product_image(file_data, product_id, file.filename)
            images.append({"url": url, "sort_order": sort_idx, "is_main": (sort_idx == 0)})
            sort_idx += 1

    # Delete removed images from S3
    for old_url in old_image_urls:
        if old_url not in retained_urls:
            await s3.delete_by_url(old_url)

    tiers = []
    if tier_quantities and tier_prices:
        qtys = [q.strip() for q in tier_quantities.split(",") if q.strip()]
        prices = [p.strip() for p in tier_prices.split(",") if p.strip()]
        for q, p in zip(qtys, prices):
            try:
                tiers.append({"min_quantity": int(q), "price": Decimal(p)})
            except (ValueError, TypeError):
                pass

    data = ProductUpdate(
        name=name,
        description=description or None,
        category_id=int(category_id) if category_id else None,
        brand=brand or None,
        volume_ml=int(volume_ml) if volume_ml else None,
        retail_price=Decimal(retail_price),
        discount_price=Decimal(discount_price) if discount_price else None,
        stock_quantity=int(stock_quantity),
        is_active=is_active == "1",
        images=images if images else None,
        wholesale_tiers=tiers if tiers else None,
    )

    await update_product(session, product_id, data)
    return RedirectResponse(f"/admin/products?success=Товар+оновлено", status_code=302)


@router.post("/products/{product_id}/delete")
async def admin_product_delete(
    product_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from src.utils.s3 import get_s3_client

    s3 = get_s3_client()
    await delete_product(session, product_id, s3_client=s3)
    return RedirectResponse("/admin/products?success=Товар+видалено", status_code=302)


# =========================================================================
# Categories
# =========================================================================

@router.get("/categories", response_class=HTMLResponse)
async def admin_categories_list(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    # Get all categories (including non-root) for admin
    stmt = (
        select(Category)
        .order_by(Category.sort_order, Category.name)
    )
    result = await session.execute(stmt)
    categories = list(result.scalars().all())

    return templates.TemplateResponse(
        "admin/categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "active_page": "categories",
        },
    )


@router.get("/categories/create", response_class=HTMLResponse)
async def admin_category_create_form(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    categories = await get_categories(session, active_only=False)
    return templates.TemplateResponse(
        "admin/categories/form.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "active_page": "categories",
        },
    )


@router.post("/categories/create")
async def admin_category_create(
    name: str = Form(...),
    parent_id: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    sort_order: str = Form("0"),
    is_active: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    data = CategoryCreate(
        name=name,
        parent_id=int(parent_id) if parent_id else None,
        image_url=None,
        sort_order=int(sort_order),
        is_active=is_active == "1",
    )
    category = await create_category(session, data)

    if image_file and image_file.filename and image_file.size:
        from src.utils.s3 import get_s3_client, validate_image_upload

        s3 = get_s3_client()
        file_data = await validate_image_upload(image_file)
        category.image_url = await s3.upload_category_image(
            file_data, category.id, image_file.filename
        )
        await session.commit()

    return RedirectResponse("/admin/categories?success=Категорiю+створено", status_code=302)


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def admin_category_edit_form(
    request: Request,
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    category = await session.get(Category, category_id)
    if not category:
        return RedirectResponse("/admin/categories?error=Категорiю+не+знайдено", status_code=302)

    categories = await get_categories(session, active_only=False)
    return templates.TemplateResponse(
        "admin/categories/form.html",
        {
            "request": request,
            "user": user,
            "category": category,
            "categories": categories,
            "active_page": "categories",
        },
    )


@router.post("/categories/{category_id}/edit")
async def admin_category_edit(
    category_id: int,
    name: str = Form(...),
    parent_id: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    remove_image: Optional[str] = Form(None),
    sort_order: str = Form("0"),
    is_active: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from src.utils.s3 import get_s3_client, validate_image_upload

    category = await session.get(Category, category_id)
    if not category:
        return RedirectResponse("/admin/categories?error=Категорiю+не+знайдено", status_code=302)

    s3 = get_s3_client()
    new_image_url = category.image_url

    if image_file and image_file.filename and image_file.size:
        # Delete old image if exists
        if category.image_url:
            await s3.delete_by_url(category.image_url)
        file_data = await validate_image_upload(image_file)
        new_image_url = await s3.upload_category_image(
            file_data, category_id, image_file.filename
        )
    elif remove_image == "1":
        if category.image_url:
            await s3.delete_by_url(category.image_url)
        new_image_url = None

    data = CategoryUpdate(
        name=name,
        parent_id=int(parent_id) if parent_id else None,
        image_url=new_image_url,
        sort_order=int(sort_order),
        is_active=is_active == "1",
    )
    await update_category(session, category_id, data)
    return RedirectResponse("/admin/categories?success=Категорiю+оновлено", status_code=302)


@router.post("/categories/{category_id}/delete")
async def admin_category_delete(
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from src.utils.s3 import get_s3_client

    s3 = get_s3_client()
    await delete_category(session, category_id, s3_client=s3)
    return RedirectResponse("/admin/categories?success=Категорiю+видалено", status_code=302)


# =========================================================================
# Orders
# =========================================================================

@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_list(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    orders, total = await get_all_orders(
        session,
        status=status,
        search=search,
        page=page,
        per_page=per_page,
    )
    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "admin/orders/list.html",
        {
            "request": request,
            "user": user,
            "orders": orders,
            "search": search or "",
            "status": status or "",
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "statuses": OrderStatus,
            "active_page": "orders",
        },
    )


@router.post("/orders/{order_id}/status")
async def admin_order_update_status(
    order_id: int,
    status: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await update_order_status(session, order_id, OrderStatus(status))
    return RedirectResponse(f"/admin/orders?success=Статус+оновлено", status_code=302)


@router.post("/orders/{order_id}/ttn")
async def admin_order_set_ttn(
    order_id: int,
    ttn: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await update_order_ttn(session, order_id, ttn)
    return RedirectResponse(f"/admin/orders?success=ТТН+встановлено", status_code=302)


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def admin_order_detail(
    request: Request,
    order_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        return RedirectResponse("/admin/orders?error=Замовлення+не+знайдено", status_code=302)

    return templates.TemplateResponse(
        "admin/orders/detail.html",
        {
            "request": request,
            "user": user,
            "order": order,
            "active_page": "orders",
        },
    )


# =========================================================================
# Coupons
# =========================================================================

@router.get("/coupons", response_class=HTMLResponse)
async def admin_coupons_list(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    coupons, total = await get_all_coupons(session, page=page, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total else 1

    return templates.TemplateResponse(
        "admin/coupons/list.html",
        {
            "request": request,
            "user": user,
            "coupons": coupons,
            "page": page,
            "total_pages": total_pages,
            "active_page": "coupons",
        },
    )


@router.get("/coupons/create", response_class=HTMLResponse)
async def admin_coupon_create_form(
    request: Request,
    user: User = Depends(get_manager_or_admin),
):
    return templates.TemplateResponse(
        "admin/coupons/form.html",
        {
            "request": request,
            "user": user,
            "active_page": "coupons",
        },
    )


@router.post("/coupons/create")
async def admin_coupon_create(
    code: str = Form(...),
    discount_type: str = Form(...),
    discount_value: str = Form(...),
    min_order_amount: str = Form("0"),
    max_uses: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    valid_from: Optional[str] = Form(None),
    valid_until: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    from datetime import datetime

    data = CouponCreate(
        code=code,
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
        min_order_amount=Decimal(min_order_amount) if min_order_amount else Decimal("0"),
        max_uses=int(max_uses) if max_uses else None,
        is_active=is_active == "1",
        valid_from=datetime.fromisoformat(valid_from) if valid_from else None,
        valid_until=datetime.fromisoformat(valid_until) if valid_until else None,
    )
    await create_coupon(session, data)
    return RedirectResponse("/admin/coupons?success=Купон+створено", status_code=302)


@router.post("/coupons/{coupon_id}/delete")
async def admin_coupon_delete(
    coupon_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await delete_coupon(session, coupon_id)
    return RedirectResponse("/admin/coupons?success=Купон+видалено", status_code=302)


# =========================================================================
# Settings
# =========================================================================

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    shop_settings = await session.get(ShopSettings, 1)
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "user": user,
            "settings": shop_settings,
            "active_page": "settings",
        },
    )


@router.post("/settings")
async def admin_settings_save(
    shop_name: Optional[str] = Form(None),
    min_order_amount: str = Form("0"),
    shop_phone: Optional[str] = Form(None),
    shop_email: Optional[str] = Form(None),
    payment_info_text: Optional[str] = Form(None),
    contacts_text: Optional[str] = Form(None),
    about_text: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    shop_settings = await session.get(ShopSettings, 1)
    if not shop_settings:
        shop_settings = ShopSettings(id=1)
        session.add(shop_settings)

    shop_settings.shop_name = shop_name or "ParfumShop"
    shop_settings.min_order_amount = Decimal(min_order_amount) if min_order_amount else Decimal("0")
    shop_settings.shop_phone = shop_phone or None
    shop_settings.shop_email = shop_email or None
    shop_settings.payment_info_text = payment_info_text or None
    shop_settings.contacts_text = contacts_text or None
    shop_settings.about_text = about_text or None

    await session.commit()
    return RedirectResponse("/admin/settings?success=Налаштування+збережено", status_code=302)


# =========================================================================
# Site Content Management
# =========================================================================

from src.content.service import (
    get_page_entries,
    save_drafts,
    publish_page as publish_page_content,
    publish_all as publish_all_content,
    discard_drafts,
    toggle_visibility,
    reorder_entries,
    create_entry,
    delete_entry,
)
from src.content.cache import invalidate_content_cache

CONTENT_PAGES = [
    ("global", "Загальне (навiгацiя, футер)"),
    ("home", "Головна сторiнка"),
    ("contacts", "Контакти"),
    ("catalog", "Каталог"),
    ("product", "Сторiнка товару"),
    ("cart", "Кошик"),
    ("checkout", "Оформлення замовлення"),
    ("orders", "Мої замовлення"),
    ("order_confirm", "Пiдтвердження замовлення"),
    ("auth", "Авторизацiя"),
]

CONTENT_PAGE_PREVIEW_URLS = {
    "global": "/",
    "home": "/",
    "contacts": "/contacts",
    "catalog": "/catalog",
    "product": "/catalog",
    "cart": "/cart",
    "checkout": "/checkout",
    "orders": "/orders/my",
    "order_confirm": "/",
    "auth": "/auth/login",
}


@router.get("/content", response_class=HTMLResponse)
async def admin_content_page(
    request: Request,
    page: str = Query("global"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    entries = await get_page_entries(session, page)
    preview_url = CONTENT_PAGE_PREVIEW_URLS.get(page, "/")
    return templates.TemplateResponse(
        "admin/content/editor.html",
        {
            "request": request,
            "user": user,
            "entries": entries,
            "current_page": page,
            "pages": CONTENT_PAGES,
            "preview_url": preview_url,
            "active_page": "content",
        },
    )


@router.post("/content/save")
async def admin_content_save(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    form = await request.form()
    page = form.get("page", "global")

    updates = {}
    for field_name, value in form.items():
        if field_name.startswith("content:"):
            key = field_name[len("content:"):]
            updates[key] = value

    await save_drafts(session, updates)
    return RedirectResponse(
        f"/admin/content?page={page}&success=Чернетку+збережено",
        status_code=302,
    )


@router.post("/content/publish")
async def admin_content_publish(
    page: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await publish_page_content(session, page)
    await invalidate_content_cache()
    return RedirectResponse(
        f"/admin/content?page={page}&success=Контент+опублiковано",
        status_code=302,
    )


@router.post("/content/publish-all")
async def admin_content_publish_all(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await publish_all_content(session)
    await invalidate_content_cache()
    return RedirectResponse(
        "/admin/content?success=Весь+контент+опублiковано",
        status_code=302,
    )


@router.post("/content/discard")
async def admin_content_discard(
    page: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await discard_drafts(session, page)
    return RedirectResponse(
        f"/admin/content?page={page}&success=Чернетку+скасовано",
        status_code=302,
    )


@router.post("/content/toggle-visibility")
async def admin_content_toggle_visibility(
    entry_id: int = Form(...),
    page: str = Form("global"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await toggle_visibility(session, entry_id)
    await invalidate_content_cache()
    return RedirectResponse(
        f"/admin/content?page={page}&success=Видимість+змінено",
        status_code=302,
    )


@router.post("/content/reorder")
async def admin_content_reorder(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    form = await request.form()
    page = form.get("page", "global")
    ids_raw = form.get("ordered_ids", "")
    ordered_ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    if ordered_ids:
        await reorder_entries(session, ordered_ids)
    return RedirectResponse(
        f"/admin/content?page={page}&success=Порядок+збережено",
        status_code=302,
    )


@router.post("/content/create")
async def admin_content_create(
    page: str = Form(...),
    key: str = Form(...),
    label: str = Form(""),
    content_type: str = Form("short"),
    published_value: str = Form(""),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await create_entry(session, key=key, page=page, label=label, content_type=content_type, published_value=published_value)
    await invalidate_content_cache()
    return RedirectResponse(
        f"/admin/content?page={page}&success=Запис+створено",
        status_code=302,
    )


@router.post("/content/delete")
async def admin_content_delete(
    entry_id: int = Form(...),
    page: str = Form("global"),
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
):
    await delete_entry(session, entry_id)
    await invalidate_content_cache()
    return RedirectResponse(
        f"/admin/content?page={page}&success=Запис+видалено",
        status_code=302,
    )
