from uuid import UUID
from sqlmodel import select, func, and_, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Tuple

from app.wallet.model import Wallet
from .model import Transaction, TransactionStatus, IdempotencyKey, RecoveryPoint
from app.common.pagination import PaginationParams


class TransactionRepo:
    @staticmethod
    async def get_transactions_by_user_id(
        session: AsyncSession,
        user_id: UUID,
        pagination: PaginationParams,
        status: TransactionStatus
    ) -> Tuple[List[Transaction], int]:
        statement = (
            select(Transaction)
            .join(Wallet, or_(Transaction.sender_wallet_id == Wallet.id, Transaction.receiver_wallet_id == Wallet.id))
            .where(Wallet.user_id == user_id)
            .distinct()
        )

        if status is not None:
            statement = statement.where(Transaction.status == status)

        count_statement = select(
            func.count()).select_from(statement.subquery())
        total_result = await session.execute(count_statement)
        total = total_result.scalar_one()

        statement = (
            statement
            .order_by(Transaction.created_at.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

        result = await session.execute(statement)
        items = result.scalars().all()
        return items, total

    @staticmethod
    async def get_transaction_by_id(session: AsyncSession, transaction_id: UUID) -> Optional[Transaction]:
        statement = select(Transaction).where(Transaction.id == transaction_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_transaction_by_id(
        session: AsyncSession,
        user_id: UUID,
        transaction_id: UUID
    ) -> Optional[Transaction]:
        statement = (
            select(Transaction)
            .join(Wallet, or_(Transaction.sender_wallet_id == Wallet.id, Transaction.receiver_wallet_id == Wallet.id))
            .where(
                and_(
                    Transaction.id == transaction_id,
                    Wallet.user_id == user_id,
                )
            )
            .distinct()
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_idempotency_key(session: AsyncSession, idempotency_key: str, user_id: UUID) -> Optional[IdempotencyKey]:
        statement = select(IdempotencyKey).where(
            and_(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.user_id == user_id
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_idempotency_key(
        session: AsyncSession,
        user_id: UUID,
        idempotency_key: str,
        request_params: dict | None = None,
    ) -> Tuple[IdempotencyKey, bool]:
        existing_key = await TransactionRepo.get_idempotency_key(
            session,
            idempotency_key=idempotency_key,
            user_id=user_id
        )

        if existing_key:
            return existing_key, False

        key = IdempotencyKey(
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_params=request_params
        )
        session.add(key)
        await session.flush()
        return key, True


transaction_repo = TransactionRepo()
