from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from .model import TransactionStatus


class TransactionResponse(BaseModel):
    id: UUID
    amount: int
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransferTransaction(BaseModel):
    sender_wallet_id: UUID
    receiver_wallet_id: UUID
    amount: float


class WithdrawalTransaction(BaseModel):
    sender_wallet_id: UUID
    amount: float


class DebitTransaction(BaseModel):
    receiver_wallet_id: UUID
    amount: float
