from uuid import UUID
from pydantic import BaseModel, Field


class WalletRead(BaseModel):
    id: UUID
    user_id: UUID
    available: int              # in cents
    reserved: int               # in cents
    available_display: str      # "$200.32"

    class Config:
        from_attributes = True


class WalletUpdate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")
