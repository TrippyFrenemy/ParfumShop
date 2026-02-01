import urllib.parse
from typing import Any, Dict, Optional

import httpx

from src.config import settings
from src.logs.middleware import logger

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def _google_redirect_uri() -> str:
    return getattr(settings, "OAUTH_GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google")


def generate_google_oauth_url(state: Optional[str] = None, redirect_uri: Optional[str] = None) -> str:
    redirect_uri = redirect_uri or _google_redirect_uri()
    scope = "openid email profile"
    client_id = settings.OAUTH_GOOGLE_CLIENT_ID

    query_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        query_params["state"] = state

    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)}"


async def exchange_google_code(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    redirect_uri = redirect_uri or _google_redirect_uri()
    logger.debug(f"[GOOGLE EXCHANGE] redirect_uri={redirect_uri}")

    data = {
        "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
        "client_secret": settings.OAUTH_GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        logger.debug(f"[GOOGLE EXCHANGE] status={resp.status_code}")
        if resp.status_code != 200:
            logger.debug(f"[GOOGLE EXCHANGE] error body={resp.text}")
        resp.raise_for_status()
        return resp.json()


async def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
        logger.debug(f"[GOOGLE VERIFY] tokeninfo status={resp.status_code}")
        if resp.status_code != 200:
            logger.debug(f"[GOOGLE VERIFY] error body={resp.text}")
        resp.raise_for_status()
        claims = resp.json()

    aud = claims.get("aud")
    iss = claims.get("iss")
    logger.debug(f"[GOOGLE VERIFY] aud={aud} iss={iss} email={claims.get('email')}")

    if aud != settings.OAUTH_GOOGLE_CLIENT_ID:
        raise ValueError("Invalid audience")

    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Invalid issuer")

    ev = claims.get("email_verified")
    if ev not in (True, "true", "True"):
        raise ValueError("Email not verified")

    return claims
