import logging
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import EmailStr
from typing import Optional

from app.users.service import user_service
from app.users.model import User
from app.users.schema import UserCreate
from .dependencies import verify_password, get_password_hash

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    async def login_user(session: AsyncSession, email: EmailStr, password: str) -> Optional[User]:
        logger.info("Checking if user exists")
        user = await user_service.get_user_by_email(session, email)
        if not user:
            return None

        logger.info("Verifying user password")
        if not verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    async def create_user(session: AsyncSession, payload: UserCreate) -> User:
        """
        Create new user
        Check if user with the email exists
        """
        logger.info("Checking if user exist by email")
        is_email_taken = await user_service.is_email_taken(session, payload.email)
        if is_email_taken:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        hashed_password = get_password_hash(payload.password)
        db_user = User(
            name=payload.name,
            email=payload.email,
            hashed_password=hashed_password
        )

        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user


auth_service = AuthService()
