
from fastapi import APIRouter, Query, Depends, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
from uuid import UUID
from typing import Annotated

from app.database import get_session
from app.users.model import User
from app.auth.dependencies import get_current_user
from app.common.pagination import PaginationParams, PaginatedResponse
from .service import transaction_service
from .model import TransactionStatus
from .schema import (
    TransactionResponse,
    TransferTransaction,
    WithdrawalTransaction,
    DebitTransaction
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/", response_model=PaginatedResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[TransactionStatus] = Query(
        None, description="Filter by transaction status"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    pagination = PaginationParams(page=page, limit=limit)

    return await transaction_service.get_user_transactions(
        session=session,
        user_id=user.id,
        pagination=pagination,
        status=status
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    transaction = await transaction_service.get_user_transaction_by_id(
        session,
        user.id,
        transaction_id
    )
    return transaction


@router.post("/{transaction_id}/flag")
async def flag_transaction(transaction_id: str, payload: dict):
    print(f"FLAGGING TRANSACTION {transaction_id}")
    return {"message": "DONE"}


@router.post("/transfer")
async def transfer_transaction(
    payload: TransferTransaction,
    idempotency_key: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # Idempotency check + lock
    await transaction_service.initiate_transactions(session, idempotency_key, user.id)

    # Reserve funds (calls wallet_service.reserve funds)
    # Create pending transaction
    # Write to outbox
    # Update recovery point
    return {"Idempotency-Key": idempotency_key}
