from datetime import datetime
from fastapi import Response
from .config import auth_config
from app.cache.cache import CacheService
import jwt


class TokenError(Exception):
    pass


async def blacklist_token(
    cache: CacheService,
    jti: str,
    exp: int,
    prefix: str = "bl"
) -> None:
    """Blacklist a token by it's jti until its natural expiry"""
    ttl = exp - int(datetime.utcnow().timestamp())
    print(ttl, f"{prefix}:{jti}")
    if ttl > 0:
        await cache.set(f"{prefix}:{jti}", "1", ttl=ttl)


def ste_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    """Set the refresh token as an httponly cookie with the configuted expiry."""
    max_age = int(auth_config.REFRESH_TOKEN_EXP.total_seconds())
    response.set_cookie(
        key="rft",
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="strict",
    )


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, auth_config.JWT_SECRET,
                             algorithms=[auth_config.JWT_ALG])
        return payload
    except jwt.PyJWTError as exc:
        raise TokenError from exc


def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, auth_config.JWT_SECRET,
                             algorithms=[auth_config.JWT_ALG])
        return payload
    except jwt.PyJWTError as exc:
        raise TokenError from exc
