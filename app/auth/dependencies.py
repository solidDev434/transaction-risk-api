import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config as app_config
from .config import auth_config
from app.database import get_session
from app.users.model import User
from .schema import TokenData
from app.cache.redis_client import redis_client
from app.cache.cache import CacheService, get_cache
from .utils import verify_access_token

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/{app_config.VERSION}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(
        timezone.utc) + (expires_delta or timedelta(minutes=auth_config.JWT_EXP))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": int(expire.timestamp()), "jti": jti})
    return jwt.encode(to_encode, auth_config.JWT_SECRET, algorithm=auth_config.JWT_ALG)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + \
        (expires_delta or auth_config.REFRESH_TOKEN_EXP)
    jti = str(uuid.uuid4())
    to_encode.update({"exp": int(expire.timestamp()), "jti": jti})
    return jwt.encode(to_encode, auth_config.JWT_SECRET, algorithm=auth_config.JWT_ALG)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
    cache: CacheService = Depends(get_cache),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # check blacklist
    client = redis_client.get_client()
    if client:
        claims = verify_access_token(token)
        is_blacklisted = await cache.get(f"bl:{claims.get('jti', token)}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    try:
        payload = jwt.decode(token, auth_config.JWT_SECRET,
                             algorithms=[auth_config.JWT_ALG])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    # optional is_active check if model has it
    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
