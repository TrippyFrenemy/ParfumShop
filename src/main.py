import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.exc import IntegrityError

import redis.asyncio as redis

from src.auth.dependencies import get_admin_user, get_current_user, get_manager_or_admin, get_warehouse_or_manager_or_admin
from src.users.models import User, UserRole

from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.logs.router import router as logs_router

from src.utils.create_preconfig_users import create_user
from src.config import settings

from src.logs.middleware import LogUserActionMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_user(role=settings.ADMIN_ROLE, email=settings.ADMIN_EMAIL, name=settings.ADMIN_NAME, password=settings.ADMIN_PASSWORD)
    # await create_user(role=settings.MANAGER_ROLE, email=settings.MANAGER_EMAIL, name=settings.MANAGER_NAME, password=settings.MANAGER_PASSWORD)
    # await create_user(role=settings.WAREHOUSE_ROLE, email=settings.WAREHOUSE_EMAIL, name=settings.WAREHOUSE_NAME, password=settings.WAREHOUSE_PASSWORD)
    yield
    # Cleanup actions can be added here if needed

app = FastAPI(lifespan=lifespan, title="Dobrotno App", description="A FastAPI application for Dobrotno Shop", version="0.0.1")

templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="src/templates/static"), name="static")
# app.mount("/media", StaticFiles(directory="src/media"), name="media")
# app.mount("/uploads", StaticFiles(directory="src/uploads"), name="uploads")

app.add_middleware(LogUserActionMiddleware)

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


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


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
