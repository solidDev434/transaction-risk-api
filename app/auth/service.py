from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import EmailStr
from typing import Optional

from app.users.service import user_service
from app.users.model import User
from app.users.schema import UserCreate
from .dependencies import verify_password, get_password_hash


class AuthService:
    @staticmethod
    async def login_user(db: AsyncSession, email: EmailStr, password: str) -> Optional[User]:
        user = await user_service.is_email_taken(db, email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    async def create_user(db: AsyncSession, user: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            name=user.name,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user


auth_service = AuthService()
