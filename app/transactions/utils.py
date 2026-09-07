from uuid import UUID

from .model import Transaction
from .schema import TransactionResponse


def to_transaction_response(
    tx: Transaction,
    user_wallet_id: UUID | None = None
) -> TransactionResponse:
    status = tx.status.value.lower() if hasattr(
        tx.status, "value") else str(tx.status).lower()
    tx_type = tx.type.value if hasattr(tx.type, "value") else str(tx.type)

    if tx_type == "withdrawal":
        wallet_id = tx.sender_wallet_id
    elif tx_type == "deposit":
        wallet_id = tx.receiver_wallet_id
    elif tx_type == "transfer":
        if user_wallet_id:
            if tx.sender_wallet_id == user_wallet_id:
                wallet_id = tx.receiver_wallet_id
            else:
                wallet_id = tx.sender_wallet_id
    else:
        wallet_id = tx.sender_wallet_id

    return TransactionResponse(
        id=tx.id,
        amount=tx.amount,
        status=status,
        type=tx.type,
        wallet_id=wallet_id,
        created_at=tx.created_at
    )
