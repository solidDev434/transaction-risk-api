import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.users.model import User
    from app.transactions.model import Transaction


class Wallet(SQLModel, table=True):
    __tablename__ = "wallet"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)

    available: int = Field(default=0, ge=0)  # Stored in cents
    reserved: int = Field(default=0, ge=0)  # Stored in cents

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
            onupdate=func.now(),
            server_default=func.now(),
            nullable=True
        )
    )

    user: Optional["User"] = Relationship(back_populates="wallet")
    sent_transactions: List["Transaction"] = Relationship(
        back_populates="sender_wallet",
        sa_relationship_kwargs={"foreign_keys": "Transaction.sender_wallet_id"}
    )
    received_transactions: List["Transaction"] = Relationship(
        back_populates="receiver_wallet",
        sa_relationship_kwargs={
            "foreign_keys": "Transaction.receiver_wallet_id"}
    )
