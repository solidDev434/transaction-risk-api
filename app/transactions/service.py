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

        response_items = [
            TransactionResponse.model_validate(item) for item in items
        ]

        pages = ceil(total / pagination.limit) if pagination.limit else 0

        return PaginatedResponse(
            items=response_items,
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

    @staticmethod
    async def initiate_transactions(
        session: AsyncSession,
        idempotency_key: UUID,
        user_id: UUID
    ):
        # Idempotency check + lock
        existing_key = await transaction_repo.get_idempotency_key(
            session,
            idempotency_key,
            user_id
        )
        if existing_key:
            return existing_key.response_body

        # Reserve funds (calls wallet_service.reserve funds)
        # Create pending transaction
        # Write to outbox
        # Update recovery point
        print("Initiate Transaction")


transaction_service = TransactionService()
