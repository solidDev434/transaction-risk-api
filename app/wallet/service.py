import logging
from uuid import UUID
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from .model import Wallet
from .repo import wallet_repo

logger = logging.getLogger(__name__)


class WalletService:
    @staticmethod
    async def get_wallet_by_user_id(session: AsyncSession, user_id: UUID) -> Wallet:
        wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        return wallet

    @staticmethod
    async def create_wallet(session: AsyncSession, user_id: UUID) -> Wallet:
        existing_wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)
        if existing_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet already exists for this user"
            )

        wallet = Wallet(user_id=user_id, available=100000, reserved=0)
        return await wallet_repo.create_wallet(session, wallet)

    @staticmethod
    async def reserve_funds(session: AsyncSession, user_id: UUID, amount: int) -> Wallet:
        """
        Reserve funds (move from available -> reserved)
        amound should be in cents
        """
        wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)

        if wallet.available < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds"
            )

        wallet.available -= amount
        wallet.reserved += amount
        return wallet

    @staticmethod
    async def release_funds(session: AsyncSession, user_id: UUID, amount: int) -> Wallet:
        """
        Release previously reserved funds (move from reserved -> available)
        """
        wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)

        if wallet.reserved < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough reserved funds"
            )

        wallet.reserved -= amount
        wallet.available += amount
        return wallet

    @staticmethod
    async def capture_funds(session: AsyncSession, user_id: UUID, amount: int) -> Wallet:
        """
        Finalize a successful transaction.
        Only reduce the reserved balance (money is now taken).
        """
        wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)

        if wallet.reserved < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough reserved funds to capture"
            )

        wallet.reserved -= amount
        return wallet


wallet_service = WalletService()
