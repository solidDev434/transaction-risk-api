from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum

from .model import TransactionStatus, TransactionType


class TransactionResponse(BaseModel):
    id: UUID
    amount: int
    status: TransactionStatus
    type: TransactionType
    wallet_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float = Field(..., gt=0)
    receiver_wallet_id: UUID | None = None


class TransferTransaction(BaseModel):
    receiver_wallet_id: UUID
    amount: float = Field(..., gt=0)


class WithdrawalTransaction(BaseModel):
    amount: float = Field(..., gt=0)


class DepositTransaction(BaseModel):
    receiver_wallet_id: UUID
    amount: float = Field(..., gt=0)


class TransactionTypeRequest(str, Enum):
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
