
from datetime import timedelta, timezone, datetime
from fastapi import APIRouter, status, Depends, HTTPException, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.users.schema import UserCreate
from app.database import get_session, AsyncSession
from .dependencies import create_access_token, create_refresh_token, oauth2_scheme
from .service import auth_service
from .config import auth_config
from .schema import RefreshRequest
from app.cache.cache import CacheService, get_cache
from .utils import (
    blacklist_token,
    ste_refresh_token_cookie,
    verify_access_token,
    verify_refresh_token,
    TokenError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    await auth_service.create_user(session, payload)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    cache: CacheService = Depends(get_cache),
):
    user = await auth_service.login_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": user.email, "type": "access"}, expires_delta=timedelta(
            minutes=auth_config.JWT_EXP))
    refresh_token = create_refresh_token(
        data={"sub": user.email, "type": "refresh"})

    # persist refresh token in cache and set cookie
    await cache.set(f"refresh:{user.email}", refresh_token, ttl=int(auth_config.REFRESH_TOKEN_EXP.total_seconds()))
    ste_refresh_token_cookie(response, refresh_token)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    cache: CacheService = Depends(get_cache),
    token: str = Depends(oauth2_scheme),
    rft: Annotated[str | None, Cookie()] = None,
):
    try:
        claims = verify_access_token(token)
        await blacklist_token(cache, claims.get("jti", token), claims.get("exp", 0))
    except TokenError:
        pass

    # Blacklist the refresh token too
    if rft:
        try:
            refresh_claims = verify_refresh_token(rft)
            await blacklist_token(cache, refresh_claims.get("jti", rft), refresh_claims.get("exp", 0), "bl_ref")
        except TokenError:
            pass

    # Clear cookie
    response.delete_cookie(
        key="rft",
        httponly=True,
        secure=True,
        samesite="strict"
    )

    return {"message": "Logged out successfully"}


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    response: Response,
    cache: CacheService = Depends(get_cache),
    rft: Annotated[str | None, Cookie()] = None
):
    if not rft:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        claims = verify_refresh_token(rft)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    if await cache.get(f"bl_ref:{claims.get('jti')}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token has been revoked")

    await blacklist_token(cache, claims.get('jti'), claims.get('exp'), "bl_ref")

    access_token = create_access_token(
        data={"sub": claims.get("sub"), "type": "access"}, expires_delta=timedelta(
            minutes=auth_config.JWT_EXP))
    refresh_token = create_refresh_token(
        data={"sub": claims.get("sub"), "type": "refresh"})

    ste_refresh_token_cookie(response, refresh_token)

    return {"access_token": access_token}
