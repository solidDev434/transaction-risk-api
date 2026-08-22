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
