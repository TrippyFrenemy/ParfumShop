import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

import redis.asyncio as redis

from src.auth.dependencies import get_admin_user
from src.users.models import User, UserRole
from src.database import get_async_session
from src.settings.models import ShopSettings

from src.bundles.router import router as bundles_router
from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.logs.router import router as logs_router
from src.products.router import router as products_router
from src.auth.dependencies import get_optional_user
from src.cart.router import router as cart_router
from src.coupons.router import router as coupons_router
from src.delivery.router import router as delivery_router
from src.orders.router import router as orders_router
from src.admin.router import router as admin_router
from src.reports.router import router as reports_router

from src.exceptions import BusinessRuleError, NotFoundError
from src.utils.create_preconfig_users import create_user
from src.config import settings
from src.products.service import get_categories, get_featured_products, get_products
from src.bundles.service import get_bundles_cached

from src.logs.middleware import LogUserActionMiddleware
from src.content.middleware import ContentMiddleware
from src.content.seed import seed_content
from src.database import async_session_maker
from src.templating import templates

# Import new logging system
from src.logging_config import setup_logging, get_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # FIRST: Initialize logging system
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Application starting up...")

    await create_user(role=settings.ADMIN_ROLE, email=settings.ADMIN_EMAIL, name=settings.ADMIN_NAME, password=settings.ADMIN_PASSWORD)
    # await create_user(role=settings.MANAGER_ROLE, email=settings.MANAGER_EMAIL, name=settings.MANAGER_NAME, password=settings.MANAGER_PASSWORD)
    # await create_user(role=settings.WAREHOUSE_ROLE, email=settings.WAREHOUSE_EMAIL, name=settings.WAREHOUSE_NAME, password=settings.WAREHOUSE_PASSWORD)
    async with async_session_maker() as session:
        await seed_content(session)
        # Ensure ShopSettings row exists so settings are always available
        existing = await session.get(ShopSettings, 1)
        if not existing:
            session.add(ShopSettings(id=1))
            await session.commit()

    logger.info("Application startup complete")
    yield

    # Cleanup actions
    logger.info("Application shutting down...")
    from src.logging_config.factory import LoggerFactory
    LoggerFactory.get_instance().shutdown()

app = FastAPI(lifespan=lifespan, title="Dobrotno App", description="A FastAPI application for Dobrotno Shop", version="0.0.1")

app.mount("/static", StaticFiles(directory="src/templates/static"), name="static")
# app.mount("/media", StaticFiles(directory="src/media"), name="media")
# app.mount("/uploads", StaticFiles(directory="src/uploads"), name="uploads")

app.add_middleware(LogUserActionMiddleware)
app.add_middleware(ContentMiddleware)

origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],  # "GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"
    allow_headers=["*"]   # "Content-Type", "Set-Cookie", "Access-Control-Allow-Headers",
                          # "Access-Control-Allow-Origin", "Authorization"
)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == 401:
        return RedirectResponse("/auth/login")
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(request: Request, exc: BusinessRuleError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    categories = await get_categories(session)
    featured_products = await get_featured_products(session, limit=8)

    # New products: latest 8 active products
    new_products_list, _ = await get_products(session, page=1, per_page=8)

    shop_settings = await ShopSettings.get_settings(session)
    show_oos = bool(shop_settings and shop_settings.show_out_of_stock)
    bundles = await get_bundles_cached(session, show_out_of_stock=show_oos)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "categories": categories,
            "featured_products": featured_products,
            "new_products": new_products_list,
            "bundles": bundles,
            "settings": shop_settings,
        },
    )


@app.get("/contacts", response_class=HTMLResponse)
async def contacts_page(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: Optional[User] = Depends(get_optional_user),
):
    shop_settings = await ShopSettings.get_settings(session)
    return templates.TemplateResponse(
        "contacts.html",
        {
            "request": request,
            "user": user,
            "shop_settings": shop_settings,
        },
    )


app.include_router(
    router=auth_router,
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(
    router=users_router,
    prefix="/users",
    tags=["Users"],
)

app.include_router(
    router=logs_router,
    prefix="/logs",
    tags=["Logs"],
    dependencies=[Depends(get_admin_user)]
)

app.include_router(
    router=products_router,
    tags=["Products"],
)

app.include_router(
    router=cart_router,
    tags=["Cart"],
)

app.include_router(
    router=coupons_router,
    prefix="/coupons",
    tags=["Coupons"],
)

app.include_router(
    router=delivery_router,
    prefix="/delivery",
    tags=["Delivery"],
)

app.include_router(
    router=orders_router,
    tags=["Orders"],
)

app.include_router(
    router=bundles_router,
    tags=["Bundles"],
)

app.include_router(
    router=admin_router,
    prefix="/admin",
    tags=["Admin"],
)

app.include_router(
    router=reports_router,
    prefix="/admin",
    tags=["Reports"],
)
