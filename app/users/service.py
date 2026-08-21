import uuid
import logging
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
        return user

    @staticmethod
    async def check_if_user_exists(session: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repo.get_user_by_id(session, user_id)
        # if not user:
        #     raise ForbiddenRequest(
        #         "You aren't authorized to access this resource")

        return user


user_service = UserService()
