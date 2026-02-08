from datetime import datetime, timedelta, timezone
from jose import jwt
from src.config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def set_auth_cookies(response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=604800,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=604800,
        path="/",
    )
    return response

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET, algorithm="HS256")


def create_refresh_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET, algorithm="HS256")


def decode_token(token: str):
    return jwt.decode(token, settings.SECRET, algorithms=["HS256"])
