from sqlmodel import select
from sqlalchemy.orm.session import Session as SyncSession
from typing import List

from .celery import celery_app
from .payment_provider import process_payment, PaymentFailedError, PaymentTimeoutError

from app.database import SyncSessionLocal as Session
from app.users.model import User
from app.wallet.model import Wallet
from app.transactions.model import Transaction, TransactionOutbox, IdempotencyKey


@celery_app.task(name="drain_transaction_outbox")
def drain_transaction_outbox():
    try:
        with Session() as session:
            rows = claim_pending_outbox_rows(session, limit=10)

            # Process Outbox Row
            for row in rows:
                process_outbox_row(session, row)

    except Exception as exc:
        print(f"Logging error {exc}")
        raise


def claim_pending_outbox_rows(
        session: SyncSession,
        limit: int = 10
) -> List[TransactionOutbox]:
    statement = (
        select(TransactionOutbox)
        .where(TransactionOutbox.status == "pending")
        .order_by(TransactionOutbox.created_at)
        .limit(10)
        .with_for_update(skip_locked=True)
    )
    result = session.execute(statement)
    rows = list(result.scalars().all())

    # Mark outbox rows as  processing
    for row in rows:
        row.status = "processing"
        row.attempts = (row.attempts or 0) + 1
        session.add(row)

    session.commit()
    return rows


def process_outbox_row(
    session: SyncSession,
    row: TransactionOutbox
):
    payload = row.payload or {}

    txn_id = payload.get("transaction_id")
    sender_wallet_id = payload.get("sender_wallet_id")
    receiver_wallet_id = payload.get("receiver_wallet_id")
    amount = int(payload.get("amount") or 0)
    idempotency_key = payload.get("idempotency_key")
    transaction_type = payload.get("type")

    print(
        f"\nTXN ID: {txn_id}\n"
        f"SENDER WALLET ID: {sender_wallet_id}\n"
        f"RECEIVER WALLET ID: {receiver_wallet_id}\n"
        f"AMOUNT: {amount}\n"
        f"IDEMPOTENCY KEY: {idempotency_key}\n"
        f"TRANSACTION TYPE: {transaction_type}"
    )

    try:
        # Call payment provider
        provider_result = process_payment(payload)
        print(provider_result, "PROVIDER RESULT")

        # Store provider reference after call
        row.payload = {
            **payload,
            "provider_response": provider_result
        }
        session.add(row)

        # On Success
    except PaymentFailedError as exc:
        print(exc, "AN ERROR OCCURED")
