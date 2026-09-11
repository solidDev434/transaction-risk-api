from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional

from .model import Wallet


class WalletRepo:
    @staticmethod
    async def get_wallet_by_user_id_for_update(session: AsyncSession, user_id: UUID) -> Optional[Wallet]:
        """Locks this wallet row for the rest of the current transaction.
        Any other request trying to lock the same row blocks until this
        transaction commits or rolls back — see Lesson 7."""
        statement = (
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

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
    def stage(session: AsyncSession, wallet: Wallet) -> None:
        """Stages the wallet for saving. Does NOT commit — the service layer
        owns the commit boundary (Lesson 6: single commit per use case)."""
        session.add(wallet)


wallet_repo = WalletRepo()
