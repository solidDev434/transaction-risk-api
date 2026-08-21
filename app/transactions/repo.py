from uuid import UUID
from sqlmodel import select, func, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Tuple

from .model import Transaction, TransactionStatus
from app.common.pagination import PaginationParams


class TransactionRepo:
    @staticmethod
    async def get_transactions_by_user_id(
        session: AsyncSession,
        user_id: UUID,
        pagination: PaginationParams,
        status: TransactionStatus
    ) -> Tuple[List[Transaction], int]:
        statement = select(Transaction).where(Transaction.user_id == user_id)

        # Filter by status if it was provided
        if status is not None:
            statement = statement.where(Transaction.status == status)

        # Count Total items
        count_statement = select(
            func.count()).select_from(statement.subquery())
        total_result = await session.execute(count_statement)
        total = total_result.scalar_one()

        # Apply ordering + pagination
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
        statement = select(Transaction).where(
            and_(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()


transaction_repo = TransactionRepo()
