import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.wallet.model import Wallet
    from app.transactions.model import IdempotencyKey


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=50)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field(max_length=100)
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

    wallet: Optional["Wallet"] = Relationship(back_populates="user")
    idempotency_key: Optional["IdempotencyKey"] = Relationship(
        back_populates="user")
