import logging
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import EmailStr

from .model import User
from .repo import user_repo

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    async def is_email_taken(session: AsyncSession, email: EmailStr) -> bool:
        """Check if username already exists"""
        user = await user_repo.get_user_by_email(session, email)
        return user is not None

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: EmailStr) -> bool:
        """Check if username already exists"""
        user = await user_repo.get_user_by_email(session, email)
        return user

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUID) -> bool:
        """Check if username already exists"""
        user = await user_repo.get_user_by_id(session, user_id)
        return user


user_service = UserService()
