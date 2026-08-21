from fastapi import HTTPException, status
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from math import ceil

from .repo import transaction_repo
from .model import TransactionStatus, Transaction
from .schema import TransactionResponse
from app.common.pagination import PaginatedResponse, PaginationParams


class TransactionService:
    @staticmethod
    async def get_user_transactions(
        session: AsyncSession,
        user_id: UUID,
        status: TransactionStatus,
        pagination: PaginationParams
    ) -> PaginatedResponse:
        items, total = await transaction_repo.get_transactions_by_user_id(
            session,
            user_id,
            pagination,
            status
        )

        pages = ceil(total / pagination.limit) if pagination.limit else 0

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1
        )

    @staticmethod
    async def get_user_transaction_by_id(
        session: AsyncSession,
        user_id: UUID,
        transaction_id: UUID
    ) -> Transaction:
        transaction = await transaction_repo.get_user_transaction_by_id(
            session,
            user_id,
            transaction_id
        )

        if not transaction:
            raise HTTPException(
                status=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        return transaction


transaction_service = TransactionService()
