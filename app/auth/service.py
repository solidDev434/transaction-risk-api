from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import EmailStr
from typing import Optional

from app.users.service import user_service
from app.users.model import User
from app.wallet.service import wallet_service
from app.wallet.model import Wallet
from app.users.schema import UserCreate
from .dependencies import verify_password, get_password_hash


class AuthService:
    @staticmethod
    async def login_user(session: AsyncSession, email: EmailStr, password: str) -> Optional[User]:
        user = await user_service.is_email_taken(session, email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    async def create_user(session: AsyncSession, user: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            name=user.name,
            email=user.email,
            hashed_password=hashed_password
        )
        session.add(db_user)

        # Flush to get user.id without committing yet
        await session.flush()
        print(db_user.model_dump())

        # Create wallet for the user
        await wallet_service.create_wallet(session, db_user.id)

        # Commit
        await session.commit()
        await session.refresh(db_user)
        return db_user


auth_service = AuthService()
