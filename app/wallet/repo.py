from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional

from .model import Wallet


class WalletRepo:
    @staticmethod
    async def get_wallet_by_id(session: AsyncSession, wallet_id: UUID) -> Optional[Wallet]:
        statement = select(Wallet).where(Wallet.id == wallet_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_wallet_by_user_id(session: AsyncSession, user_id: UUID) -> Optional[Wallet]:
        statement = select(Wallet).where(Wallet.user_id == user_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_wallet(session: AsyncSession, wallet: Wallet) -> Wallet:
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        return wallet

    @staticmethod
    async def save(session: AsyncSession, wallet: Wallet) -> Wallet:
        session.add(wallet)
        await session.commit()
        await session.refresh(wallet)
        return wallet


wallet_repo = WalletRepo()
