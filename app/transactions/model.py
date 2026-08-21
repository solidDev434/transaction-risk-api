import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, JSON, Column, DateTime, func, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.users.model import User


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


# class Transaction(SQLModel, table=True):
#     __tablename__ = "Transactions"

    # id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)

#     payload: Optional[dict] = Field(sa_column=Column(JSON))
#     status: TransactionStatus = Field(default=TransactionStatus.PENDING)
#     attempts: int = Field(default=0, ge=0)
    # locked_at: datetime = Field(
    #     sa_column=Column(
    #         DateTime(timezone=True),
    #         server_default=func.now(),
    #         nullable=True
    #     )
    # )

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)

    amount: int = Field(default=0, ge=0)        # stored in cents
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
            nullable=True
        )
    )

    user: Optional["User"] = Relationship(back_populates="transactions")
