import secrets
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.auth.dependencies import get_current_user, pwd_context
from src.auth.service import get_user_by_email
from src.auth.tokens import create_access_token, create_refresh_token, decode_token, set_auth_cookies
from src.config import settings
from src.database import get_async_session
from src.logging_config import get_logger
from src.users.models import User, UserRole
from src.utils.ip import get_real_ip
from src.utils.ratelimit import is_blocked, register_failed_attempt, delete_attempt
from src.utils.redis_client import get_redis_client

from src.cart.service import merge_carts
from src.templating import templates

logger = get_logger(__name__)

router = APIRouter()

redis = get_redis_client()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session
)):
    ip = await get_real_ip(request)
    logger.debug("login attempt", extra={"ip": ip})

    if await is_blocked(ip):
        logger.debug("login blocked by rate limiter", extra={"ip": ip})
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Слишком много попыток. Подождите 10 минут."},
            status_code=429,
        )

    user = await get_user_by_email(session, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        await register_failed_attempt(ip)
        logger.warning("login failed: invalid credentials", extra={"ip": ip})
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Неверные данные"},
            status_code=401,
        )

    if not user.is_active:
        logger.debug("login failed: inactive user", extra={"user_id": user.id})
        raise HTTPException(status_code=403, detail="Inactive user")

    await delete_attempt(ip)
    logger.info("login successful", extra={"user_id": user.id, "ip": ip})
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await redis.set(f"refresh_token:{user.id}", refresh_token)

    cart_session_id = request.cookies.get("cart_session_id")
    if cart_session_id:
        await merge_carts(session, guest_session_id=cart_session_id, user_id=user.id)

    response = RedirectResponse(url="/", status_code=302)
    response = set_auth_cookies(response, access_token, refresh_token)
    if cart_session_id:
        response.delete_cookie("cart_session_id", path="/")
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    ip = await get_real_ip(request)
    logger.debug(f"[REGISTER] attempt email={email} ip={ip}")
    if await is_blocked(ip):
        logger.debug(f"[REGISTER] blocked ip={ip}")
        raise HTTPException(status_code=429, detail="Слишком много попыток. Подождите 10 минут.")

    email_norm = email.strip().lower()

    existing = await get_user_by_email(session, email_norm)
    if existing:
        logger.debug("[REGISTER] duplicate email attempt")
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user = User(
        email=email_norm,
        name=name.strip(),
        role=UserRole.CLIENT,  # default
        hashed_password=pwd_context.hash(password),
        is_active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    await session.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await redis.set(f"refresh_token:{user.id}", refresh_token)

    cart_session_id = request.cookies.get("cart_session_id")
    if cart_session_id:
        await merge_carts(session, guest_session_id=cart_session_id, user_id=user.id)

    response = RedirectResponse(url="/", status_code=302)
    response = set_auth_cookies(response, access_token, refresh_token)
    if cart_session_id:
        response.delete_cookie("cart_session_id", path="/")
    return response

@router.post("/refresh")
async def refresh_token(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
        saved_token = await redis.get(f"refresh_token:{user_id}")
        if saved_token != token:
            raise HTTPException(status_code=401, detail="Token mismatch")

        new_access = create_access_token({"sub": str(user_id)})
        new_refresh = create_refresh_token({"sub": str(user_id)})
        await redis.set(f"refresh_token:{user_id}", new_refresh)

        response = JSONResponse(content={"message": "Token refreshed"})
        response = set_auth_cookies(response, new_access, new_refresh)
        return response
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/google/url")
async def get_google_oauth_url():
    from src.auth.service import generate_google_oauth_url
    url = generate_google_oauth_url()
    return {"url": url}

@router.get("/google/start")
async def google_start():
    from src.auth.service import generate_google_oauth_url

    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", settings.OAUTH_STATE_TTL, "1")
    logger.debug(f"[GOOGLE START] state={state}")

    url = generate_google_oauth_url(state=state)
    logger.debug(f"[GOOGLE START] redirect_url={url}")
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/google")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    from src.auth.service import exchange_google_code, verify_google_id_token

    logger.debug(f"[GOOGLE CB] code={code[:16]}... state={state}")

    cookie_state = request.cookies.get("oauth_state")
    logger.debug(f"[GOOGLE CB] cookie_state={cookie_state} query_state={state}")
    if not state or not cookie_state or state != cookie_state:
        logger.debug("[GOOGLE CB] state mismatch")
        raise HTTPException(status_code=400, detail="Invalid state")

    exists = await redis.get(f"oauth_state:{state}")
    if not exists:
        logger.debug("[GOOGLE CB] state not found in redis (expired)")
        raise HTTPException(status_code=400, detail="State expired")
    await redis.delete(f"oauth_state:{state}")

    try:
        token_data = await exchange_google_code(code)
    except Exception as exc:
        logger.debug(f"[GOOGLE CB] code exchange failed: {exc}")
        raise HTTPException(status_code=400, detail="Google code exchange failed")

    id_token = token_data.get("id_token")
    if not id_token:
        logger.debug(f"[GOOGLE CB] no id_token in response, keys={list(token_data.keys())}")
        raise HTTPException(status_code=400, detail="Missing id_token")

    try:
        claims = await verify_google_id_token(id_token)
    except Exception as exc:
        logger.debug(f"[GOOGLE CB] token verification failed: {exc}")
        raise HTTPException(status_code=400, detail="Invalid Google token")

    email = (claims.get("email") or "").strip().lower()
    sub = claims.get("sub")
    name = claims.get("name") or claims.get("given_name") or email.split("@")[0]
    logger.debug(f"[GOOGLE CB] email={email} sub={sub} name={name}")

    if not email or not sub:
        logger.debug("[GOOGLE CB] incomplete profile")
        raise HTTPException(status_code=400, detail="Google profile incomplete")

    user = await get_user_by_email(session, email)

    if user:
        logger.debug(f"[GOOGLE CB] existing user id={user.id} google_sub={user.google_sub}")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Inactive user")
        if user.google_sub and user.google_sub != sub:
            logger.debug(f"[GOOGLE CB] sub mismatch: db={user.google_sub} google={sub}")
            raise HTTPException(status_code=403, detail="Google account mismatch")
        if not user.google_sub:
            user.google_sub = sub
            await session.commit()
            logger.debug(f"[GOOGLE CB] linked google_sub to user id={user.id}")
    else:
        random_pw = secrets.token_urlsafe(32)
        user = User(
            email=email,
            name=name,
            role=UserRole.CLIENT,
            hashed_password=pwd_context.hash(random_pw),
            google_sub=sub,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.debug(f"[GOOGLE CB] created new user id={user.id} email={email}")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await redis.set(f"refresh_token:{user.id}", refresh_token)
    logger.info(f"[GOOGLE LOGIN SUCCESS] user_id={user.id} email={email}")

    cart_session_id = request.cookies.get("cart_session_id")
    if cart_session_id:
        await merge_carts(session, guest_session_id=cart_session_id, user_id=user.id)

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("oauth_state", path="/")
    response = set_auth_cookies(response, access_token, refresh_token)
    if cart_session_id:
        response.delete_cookie("cart_session_id", path="/")
    return response


from pydantic import BaseModel


class PostOrderRegisterRequest(BaseModel):
    email: str
    password: str
    order_number: str
    name: str
    phone: str | None = None


@router.post("/post-order-register")
async def post_order_register(
    request: Request,
    body: PostOrderRegisterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Create account after placing an order and link the order to the new user."""
    ip = await get_real_ip(request)
    if await is_blocked(ip):
        raise HTTPException(status_code=429, detail="Забагато спроб. Зачекайте 10 хвилин.")

    email_norm = body.email.strip().lower()

    existing = await get_user_by_email(session, email_norm)
    if existing:
        raise HTTPException(status_code=400, detail="Користувач з таким email вже існує")

    user = User(
        email=email_norm,
        name=body.name.strip(),
        phone=body.phone,
        role=UserRole.CLIENT,
        hashed_password=pwd_context.hash(body.password),
        is_active=True,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Користувач з таким email вже існує")

    await session.refresh(user)

    # Link the order to the new user
    from src.orders.models import Order
    order_stmt = select(Order).where(
        Order.order_number == body.order_number,
        Order.user_id.is_(None),
    )
    order_result = await session.execute(order_stmt)
    order = order_result.scalar_one_or_none()
    if order:
        order.user_id = user.id
        await session.commit()

    # Merge guest cart if present
    cart_session_id = request.cookies.get("cart_session_id")
    if cart_session_id:
        await merge_carts(session, guest_session_id=cart_session_id, user_id=user.id)

    # Generate tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await redis.set(f"refresh_token:{user.id}", refresh_token)

    response = JSONResponse(content={"message": "Акаунт створено! Замовлення прив'язано."})
    response = set_auth_cookies(response, access_token, refresh_token)
    if cart_session_id:
        response.delete_cookie("cart_session_id", path="/")
    return response


@router.get("/logout")
async def logout_page(request: Request):
    cookie_auth = request.cookies.get("Authorization")
    if cookie_auth and cookie_auth.startswith("Bearer "):
        try:
            payload = decode_token(cookie_auth[7:])
            user_id = int(payload.get("sub"))
            await redis.delete(f"refresh_token:{user_id}")
            logger.debug(f"[LOGOUT] cleared refresh token for user_id={user_id}")
        except Exception:
            logger.debug("[LOGOUT] token decode failed, clearing cookies only")

    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("Authorization", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response
