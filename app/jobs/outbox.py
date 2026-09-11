import random
import logging
from sqlmodel import select
from fastapi import status
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm.session import Session as SyncSession
from typing import List

from .celery import celery_app
from .payment_provider import process_payment, PaymentFailedError, PaymentTimeoutError

from app.config import config
from app.database import SyncSessionLocal as Session
from app.users.model import User
from app.wallet.model import Wallet
from app.transactions.model import (
    Transaction,
    TransactionStatus,
    TransactionOutbox,
    IdempotencyKey,
    RecoveryPoint
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = config.MAX_ATTEMPTS


def compute_backoff_seconds(attempts: int, base: float = 2.0, cap: float = 300.0) -> float:
    """Exponential backoff, full jitter"""
    exp_delay = min(cap, base * (2 ** max(attempts - 1, 0)))
    return random.uniform(0, exp_delay)


@celery_app.task(name="drain_transaction_outbox")
def drain_transaction_outbox():
    outbox_ids: list[str] = []
    try:
        with Session() as session:
            outbox_ids = claim_pending_outbox_rows(session, limit=10)
    except Exception as exc:
        logger.error(f"Failed to claim outbox rows: {exc}")

    # Process Outbox row independently
    for outbox_id in outbox_ids:
        try:
            process_outbox_row(outbox_id)
        except Exception as exc:
            logger.error(f"Row {outbox_id} raised during processing: {exc}")


def claim_pending_outbox_rows(
    session: SyncSession,
    limit: int = 10
) -> List[str]:
    logger.info("Claiming pending Outbox Rows")
    statement = (
        select(TransactionOutbox)
        .where(TransactionOutbox.status == "pending")
        .where(
            (TransactionOutbox.next_retry_at.is_(None))
            | (TransactionOutbox.next_retry_at <= datetime.utcnow())
        )
        .order_by(TransactionOutbox.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = session.execute(statement)
    rows = list(result.scalars().all())

    # Mark outbox rows as processing and increment attempts
    logger.info("Mark all pending Outbox Rows as processing")
    ids = []
    for row in rows:
        row.status = "processing"
        row.attempts = (row.attempts or 0) + 1
        session.add(row)
        ids.append(str(row.id))

    session.commit()
    return ids


def process_outbox_row(outbox_id: str):
    """
    Loads the outbox payload, calls the payment provider, then routes the
    result to exactly one of settle_success / settle_failure / settle_retry.
    No ORM object survives past this function — only plain IDs are passed on.
    """
    logger.info(
        "Processing Outbox Rows. Return/Stop if rows is already processed or failed")
    with Session() as session:
        row = session.get(
            TransactionOutbox,
            UUID(outbox_id),
            with_for_update=True
        )
        if not row or row.status in ("processed", "failed"):
            return

        payload = row.payload or {}
        attempts = row.attempts or 0

    try:
        # Call payment provider
        provider_result = process_payment(payload)
        settle_success(
            outbox_id=outbox_id,
            payload=payload,
            provider_result=provider_result
        )

    except PaymentFailedError as exc:
        settle_failure(
            outbox_id=outbox_id,
            payload=payload,
            provider_result={"error": str(exc)}
        )

    except PaymentTimeoutError as exc:
        settle_retry(
            outbox_id=outbox_id,
            error={"error": str(exc)},
            attempts=attempts
        )

    except Exception as exc:
        settle_retry(
            outbox_id=outbox_id,
            error={"error": f"unexpected: {exc}"},
            attempts=attempts
        )


def settle_success(
    outbox_id: str,
    payload: dict,
    provider_result: dict
):
    """
    One ACID transaction: move funds per transaction type, clear the transaction,
    mark the outbox processed, update the idempotency key to COMPLETED.
    """

    # idempotency_key = payload.get("idempotency_key")
    txn_id = payload.get("transaction_id")
    sender_wallet_id = payload.get("sender_wallet_id")
    receiver_wallet_id = payload.get("receiver_wallet_id")
    amount = int(payload.get("amount") or 0)
    transaction_type = (payload.get("type") or "").lower()
    idempotency_key = payload.get("idempotency_key")
    user_id = payload.get("user_id")

    with Session() as session:
        with session.begin():
            row = session.get(TransactionOutbox, UUID(
                outbox_id), with_for_update=True)
            if not row or row.status in ("processed", "failed"):
                return

            # Record Provider Response
            update_idempotency_recovery(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
                recovery_point=RecoveryPoint.PROVIDER_CALLED,
            )

            transaction = get_transaction_for_update(session, txn_id)

            # TRANSACTION_TYPE: Transfer | Wallet
            # Debits/Removes from sender reserved funds
            if transaction_type in ("transfer", "withdrawal"):
                if sender_wallet_id:
                    capture_funds(
                        session,
                        sender_wallet_id,
                        amount
                    )

            # TRANSACTION_TYPE: Transfer | Debit
            # Credits funds to receiver
            if transaction_type in ("transfer", "deposit"):
                if receiver_wallet_id:
                    credit_wallet(
                        session,
                        receiver_wallet_id,
                        amount
                    )

            if transaction:
                transaction.status = TransactionStatus.CLEARED
                session.add(transaction)

            row.status = "processed"
            row.payload = {
                **(row.payload or {}),
                "provider_response": provider_result
            }
            session.add(row)

            update_idempotency_recovery(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
                recovery_point=RecoveryPoint.COMPLETED,
                response_code=status.HTTP_200_OK,
                response_body={
                    "transaction_id": txn_id,
                    "status": "cleared",
                    "provider_response": provider_result,
                },
            )


def settle_failure(
    outbox_id: str,
    payload: dict,
    provider_result: dict
):
    """
    One ACID transaction: release any reserved funds, reject the transaction,
    mark the outbox failed (no further retries — the provider made a final decision)."""

    txn_id = payload.get("transaction_id")
    sender_wallet_id = payload.get("sender_wallet_id")
    amount = int(payload.get("amount") or 0)
    transaction_type = (payload.get("type") or "").lower()
    idempotency_key = payload.get("idempotency_key")
    user_id = payload.get("user_id")

    with Session() as session:
        with session.begin():
            row = session.get(TransactionOutbox, UUID(
                outbox_id), with_for_update=True)
            if not row or row.status in ("processed", "failed"):
                return

            transaction = get_transaction_for_update(session, txn_id)

            if transaction_type in ("transfer", "withdrawal") and sender_wallet_id:
                release_funds(
                    session,
                    sender_wallet_id,
                    amount
                )

            if transaction:
                transaction.status = TransactionStatus.REJECTED
                session.add(transaction)

            row.status = "failed"
            row.payload = {
                **(row.payload or {}),
                "provider_response": provider_result
            }
            session.add(row)

            update_idempotency_recovery(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
                recovery_point=RecoveryPoint.FAILED,
                response_code=status.HTTP_402_PAYMENT_REQUIRED,
                response_body={
                    "transaction_id": txn_id,
                    "status": "rejected",
                    "provider_response": provider_result,
                },
            )


def settle_retry(
    outbox_id: str,
    error: dict,
    attempts: int
):
    """
    Marks the row pending again with a backoff delay, or dead-letters it
    past MAX_ATTEMPTS. Deliberately does NOT touch wallet/transaction state —
    a transient failure means we don't yet know the final outcome.
    """

    with Session() as session:
        with session.begin():
            row = session.get(TransactionOutbox, UUID(
                outbox_id), with_for_update=True)
            if not row or row.status in ("processed", "failed"):
                return

            row.payload = {
                **(row.payload or {}),
                "last_error": error
            }

            if attempts >= MAX_ATTEMPTS:
                row.status = "failed"
                row.next_retry_at = None
            else:
                row.status = "pending"
                row.next_retry_at = datetime.utcnow(
                ) + timedelta(seconds=compute_backoff_seconds(attempts=attempts))
            session.add(row)


def get_transaction_for_update(session: SyncSession, txn_id: UUID | None) -> Transaction | None:
    if not txn_id:
        return None

    statement = (
        select(Transaction)
        .where(Transaction.id == txn_id)
        .with_for_update()
    )
    return session.execute(statement).scalar_one_or_none()


def capture_funds(
    session: SyncSession,
    wallet_id: str,
    amount: int
):
    logger.info(f"DEBITTING FROM {wallet_id}")
    wallet = get_wallet_for_update(session, wallet_id)
    if wallet.reserved < amount:
        raise Exception("Insufficient reserved funds to capture")

    wallet.reserved -= amount
    session.add(wallet)


def release_funds(
    session: SyncSession,
    wallet_id: str,
    amount: int
):
    logger.info(f"RELEASE {wallet_id} RESERVERD FUNDS")
    wallet = get_wallet_for_update(session, wallet_id)
    if wallet.reserved < amount:
        raise Exception("Insufficient reserved funds to release")

    wallet.reserved -= amount
    wallet.available += amount
    session.add(wallet)


def credit_wallet(session, wallet_id: str, amount: int):
    logger.info(f"CREDITTING {wallet_id}")
    wallet = get_wallet_for_update(session, wallet_id)
    wallet.available += amount
    session.add(wallet)


def update_idempotency_recovery(
    session: SyncSession,
    user_id: str,
    idempotency_key: str | None,
    recovery_point: RecoveryPoint,
    response_code: int | None = None,
    response_body: dict | None = None
) -> None:
    if not user_id or not IdempotencyKey:
        return

    statement = (
        select(IdempotencyKey)
        .where(
            IdempotencyKey.user_id == UUID(str(user_id)),
            IdempotencyKey.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    key = session.execute(statement).scalar_one_or_none()
    if not key:
        return

    key.recovery_point = recovery_point
    key.locked_at = None

    if response_code is not None:
        key.response_code = response_code
    if response_body is not None:
        key.response_body = response_body

    session.add(key)


def get_wallet_for_update(session: SyncSession, wallet_id: UUID | None) -> Wallet | None:
    if not wallet_id:
        return None

    statement = (
        select(Wallet)
        .where(Wallet.id == wallet_id)
        .with_for_update()
    )
    return session.execute(statement).scalar_one_or_none()
