import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, JSON, Column, DateTime, func, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.wallet.model import Wallet
    from app.users.model import User


class TransactionStatus(str, Enum):
    PENDING = "pending"
    FLAGGED = "flagged"
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"


class TransactionType(str, Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class RecoveryPoint(str, Enum):
    STARTED = "started"
    FUNDS_RESERVED = "funds_reserved"
    OUTBOX_WRITTEN = "outbox_written"
    PROVIDER_CALLED = "provider_called"
    COMPLETED = "completed"
    FAILED = "failed"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    sender_wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="wallet.id",
        index=True
    )
    receiver_wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="wallet.id",
        index=True
    )

    amount: int = Field(default=0, ge=0)        # stored in cents
    type: TransactionType = Field(default=TransactionType.TRANSFER)
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=True
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=True
        )
    )

    sender_wallet: Optional["Wallet"] = Relationship(
        back_populates="sent_transactions",
        sa_relationship_kwargs={
            "foreign_keys": "[Transaction.sender_wallet_id]"}
    )
    receiver_wallet: Optional["Wallet"] = Relationship(
        back_populates="received_transactions",
        sa_relationship_kwargs={
            "foreign_keys": "[Transaction.receiver_wallet_id]"}
    )


class TransactionOutbox(SQLModel, table=True):
    __tablename__ = "transaction_outbox"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_type: str = Field(default="process_transaction",
                            max_length=100, index=True)
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="pending", max_length=50)
    attempts: int = Field(default=0, ge=0)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=True
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=True
        )
    )


class IdempotencyKey(SQLModel, table=True):
    __tablename__ = "idempotency_keys"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        index=True,
        foreign_key="users.id",
        unique=True
    )
    idempotency_key: str = Field(index=True, unique=True, max_length=100)
    recovery_point: RecoveryPoint = Field(default=RecoveryPoint.STARTED)

    request_params: dict | None = Field(default=None, sa_column=Column(JSON))
    response_code: int | None = None
    response_body: dict | None = Field(default=None, sa_column=Column(JSON))

    locked_at: datetime | None = None
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=True
        )
    )

    user: Optional["User"] = Relationship(back_populates="idempotency_keys")
