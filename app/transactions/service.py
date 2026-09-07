from datetime import datetime, timedelta
from fastapi import HTTPException, status
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from math import ceil

from app.wallet.repo import wallet_repo
from app.wallet.service import wallet_service
from app.wallet.utils import to_cent
from .utils import to_transaction_response
from .repo import transaction_repo
from .model import TransactionStatus, Transaction, TransactionType, RecoveryPoint, TransactionOutbox
from .schema import TransactionCreate, TransactionResponse
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

        user_wallet = await wallet_repo.get_wallet_by_user_id(session, user_id)
        user_wallet_id = user_wallet.id if user_wallet else None

        response_items = [
            to_transaction_response(item, user_wallet_id=user_wallet_id)
            for item in items
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
    async def initiate_transaction(
        session: AsyncSession,
        sender_user_id: UUID,
        payload: TransactionCreate,
        idempotency_key: str,
    ) -> dict:
        amount_cents = to_cent(payload.amount)
        return await TransactionService._do_initiate(
            session,
            sender_user_id,
            payload,
            idempotency_key,
            amount_cents
        )

    @staticmethod
    async def _do_initiate(
        session: AsyncSession,
        sender_user_id: UUID,
        payload: TransactionCreate,
        idempotency_key: str,
        amount_cents: int,
    ) -> dict:
        key, is_new = await transaction_repo.get_or_create_idempotency_key(
            session,
            user_id=sender_user_id,
            idempotency_key=idempotency_key,
            request_params=payload.model_dump(mode="json")
        )

        if not is_new:
            if key.recovery_point == RecoveryPoint.COMPLETED:
                return {
                    "short_circuit": True,
                    "status_code": key.response_code or status.HTTP_200_OK,
                    "body": key.response_body or {},
                }

            if key.locked_at and key.locked_at > datetime.utcnow() - timedelta(seconds=30):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Request already in progress"
                )

        sender_wallet = await wallet_service.get_wallet_by_user_id(session, sender_user_id)

        if payload.type == TransactionType.TRANSFER:
            if not payload.receiver_wallet_id:
                raise HTTPException(
                    status_code=400, detail="receiver_wallet_id is required for transfers")

            receiver_wallet = await wallet_repo.get_wallet_by_id(session, payload.receiver_wallet_id)
            if not receiver_wallet:
                raise HTTPException(
                    status_code=404, detail="Receiver wallet not found")

            await wallet_service.reserve_funds(session, sender_user_id, amount_cents)

        elif payload.type == TransactionType.WITHDRAWAL:
            await wallet_service.reserve_funds(session, sender_user_id, amount_cents)

        elif payload.type == TransactionType.DEPOSIT:
            if not payload.receiver_wallet_id:
                raise HTTPException(
                    status_code=400, detail="receiver_wallet_id is required for deposits")

            receiver_wallet = await wallet_repo.get_wallet_by_id(session, payload.receiver_wallet_id)
            if not receiver_wallet:
                raise HTTPException(
                    status_code=404, detail="Receiver wallet not found")

        transaction = Transaction(
            sender_wallet_id=sender_wallet.id if payload.type != TransactionType.DEPOSIT else None,
            receiver_wallet_id=payload.receiver_wallet_id,
            amount=amount_cents,
            type=payload.type,
            status=TransactionStatus.PENDING,
        )
        session.add(transaction)
        await session.flush()

        outbox = TransactionOutbox(
            event_type="process_transaction",
            payload={
                "transaction_id": str(transaction.id),
                "type": payload.type.value,
                "amount": amount_cents,
                "sender_wallet_id": str(sender_wallet.id) if payload.type != TransactionType.DEPOSIT else None,
                "receiver_wallet_id": str(payload.receiver_wallet_id) if payload.receiver_wallet_id else None,
                "idempotency_key": idempotency_key,
                "user_id": str(sender_user_id),
            },
            status="pending",
            attempts=0,
        )
        session.add(outbox)

        key.recovery_point = RecoveryPoint.OUTBOX_WRITTEN
        key.locked_at = None
        key.response_code = status.HTTP_202_ACCEPTED
        key.response_body = {
            "transaction_id": str(transaction.id),
            "status": "pending",
            "type": payload.type.value,
        }
        session.add(key)

        return {
            "short_circuit": False,
            "transaction_id": str(transaction.id),
            "status": "pending",
        }


transaction_service = TransactionService()
