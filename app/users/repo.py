import uuid
from sqlmodel import select
from typing import Optional
from pydantic import EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession
from .model import User


class UserRespository:
    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Get user by id"""
        statement = select(User).where(
            User.id == user_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: EmailStr) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = await session.execute(statement)
        return result.scalar_one_or_none()


user_repo = UserRespository()
