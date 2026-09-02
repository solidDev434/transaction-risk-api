from uuid import UUID
from sqlmodel import select, func, and_, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional, Tuple

from app.wallet.model import Wallet
from .model import Transaction, TransactionStatus, IdempotencyKey, RecoveryPoint, TransactionOutbox
from app.common.pagination import PaginationParams
from sqlalchemy import func


class TransactionRepo:
    @staticmethod
    async def get_transactions_by_user_id(
        session: AsyncSession,
        user_id: UUID,
        pagination: PaginationParams,
        status: TransactionStatus
    ) -> Tuple[List[Transaction], int]:
        statement = (
            select(Transaction)
            .join(Wallet, or_(Transaction.sender_wallet_id == Wallet.id, Transaction.receiver_wallet_id == Wallet.id))
            .where(Wallet.user_id == user_id)
            .distinct()
        )

        if status is not None:
            statement = statement.where(Transaction.status == status)

        count_statement = select(
            func.count()).select_from(statement.subquery())
        total_result = await session.execute(count_statement)
        total = total_result.scalar_one()

        statement = (
            statement
            .order_by(Transaction.created_at.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

        result = await session.execute(statement)
        items = result.scalars().all()
        return items, total

    @staticmethod
    async def get_transaction_by_id(session: AsyncSession, transaction_id: UUID) -> Optional[Transaction]:
        statement = select(Transaction).where(Transaction.id == transaction_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_transaction_by_id(
        session: AsyncSession,
        user_id: UUID,
        transaction_id: UUID
    ) -> Optional[Transaction]:
        statement = (
            select(Transaction)
            .join(Wallet, or_(Transaction.sender_wallet_id == Wallet.id, Transaction.receiver_wallet_id == Wallet.id))
            .where(
                and_(
                    Transaction.id == transaction_id,
                    Wallet.user_id == user_id,
                )
            )
            .distinct()
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_idempotency_key(session: AsyncSession, idempotency_key: str, user_id: UUID) -> Optional[IdempotencyKey]:
        statement = select(IdempotencyKey).where(
            and_(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.user_id == user_id
            )
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_idempotency_key(
        session: AsyncSession,
        user_id: UUID,
        idempotency_key: str,
        request_params: dict | None = None,
    ) -> Tuple[IdempotencyKey, bool]:
        """Selects and returns idempotency key if it exists.

        Else it creates a new key row
        """
        existing_key = await TransactionRepo.get_idempotency_key(
            session,
            idempotency_key=idempotency_key,
            user_id=user_id
        )

        if existing_key:
            return existing_key, False

        key = IdempotencyKey(
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_params=request_params
        )
        session.add(key)
        await session.flush()
        return key, True

    async def reserve_pending_outbox(self, session: AsyncSession) -> Optional[TransactionOutbox]:
        """Select a single pending outbox row and mark it processing.

        Uses FOR UPDATE SKIP LOCKED to avoid contention between workers.
        Returns the reserved outbox row or None.
        """
        statement = (
            select(TransactionOutbox)
            .where(TransactionOutbox.status == "pending")
            .order_by(TransactionOutbox.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(statement)
        rows = result.scalars().all()

        for outbox in rows:
            outbox.status = "processing"
            outbox.attempts = (outbox.attempts or 0) + 1
            session.add(outbox)

        if rows:
            await session.flush()

        return rows

    async def mark_outbox_failed(self, session: AsyncSession, outbox_id: UUID, provider_response: dict | None = None) -> None:
        outbox = await session.get(TransactionOutbox, outbox_id)
        if not outbox:
            return

        outbox.status = "failed"
        if provider_response is not None:
            outbox.payload = {
                **(outbox.payload or {}),
                "provider_response": provider_response
            }
        session.add(outbox)
        await session.flush()

    async def mark_outbox_pending(self, session: AsyncSession, outbox_id: UUID, provider_response: dict | None = None) -> None:
        outbox = await session.get(TransactionOutbox, outbox_id)
        if not outbox:
            return

        outbox.status = "failed"
        if provider_response is not None:
            outbox.payload = {
                **(outbox.payload or {}),
                "provider_response": provider_response
            }
        session.add(outbox)
        await session.flush()

    async def complete_outbox_phase2(self, session: AsyncSession, outbox_id: UUID, provider_response: dict) -> None:
        """
        Success path:
        - capture reserved funds when needed
        - credit receiver when needed
        - mark transaction success/cleared
        - mark outbox processed
        """
        outbox = await session.get(TransactionOutbox, outbox_id)
        if not outbox:
            return

        payload = outbox.payload or {}
        txn_id = payload.get("transaction_id")
        amount = int(payload.get("amount") or 0)
        tx_type = payload.get("type")

        if not txn_id:
            outbox.status = "processed"
            session.add(outbox)
            await session.flush()
            return

        txn = await session.get(Transaction, txn_id)
        if not txn or txn.status != TransactionStatus.PENDING:
            outbox.status = "processed"
            session.add(outbox)
            await session.flush()
            return

        # lock and update sender wallet
        sender_wallet_id = payload.get("sender_wallet_id")
        receiver_wallet_id = payload.get("receiver_wallet_id")

        if tx_type in ("transfer", "withdrawal"):
            if sender_wallet_id:
                sender = await TransactionRepo._get_wallet_for_update(session, UUID(sender_wallet_id))
                if not sender:
                    raise Exception("Sender wallet not found during capture")
                if sender.reserved < amount:
                    raise Exception(
                        "Insufficient reserved funds during capture")
                sender.reserved -= amount
                session.add(sender)

        if tx_type in ("transfer", "deposit"):
            if receiver_wallet_id:
                receiver = await TransactionRepo._get_wallet_for_update(session, UUID(receiver_wallet_id))
                if not receiver:
                    raise Exception("Receiver wallet not found during credit")
                receiver.available += amount
                session.add(receiver)

        txn.status = TransactionStatus.CLEARED
        outbox.status = "processed"
        outbox.payload = {**(outbox.payload or {}),
                          "provider_response": provider_response}

        session.add(txn)
        session.add(outbox)
        await session.flush()

    async def append_outbox_provider_response(self, session: AsyncSession, outbox_id: UUID, provider_response: dict) -> None:
        ob = await session.get(TransactionOutbox, outbox_id)
        if not ob:
            return
        ob.payload = {**(ob.payload or {}),
                      "provider_response": provider_response}
        session.add(ob)
        await session.flush()

    async def update_idempotency_recovery(self, session: AsyncSession, idempotency_key: str, user_id: UUID, recovery_point: RecoveryPoint, response_code: int | None = None, response_body: dict | None = None) -> None:
        existing = await TransactionRepo.get_idempotency_key(session, idempotency_key=idempotency_key, user_id=user_id)
        if not existing:
            return
        existing.recovery_point = recovery_point
        if response_code is not None:
            existing.response_code = response_code
        if response_body is not None:
            existing.response_body = response_body
        session.add(existing)
        await session.flush()

    # async def mark_outbox_failed(self, session: AsyncSession, outbox_id: UUID, provider_response: dict | None = None) -> None:
    #     """Mark outbox as failed/dead-lettered and update idempotency record if present."""
    #     ob = await session.get(TransactionOutbox, outbox_id)
    #     if not ob:
    #         return
    #     ob.status = "failed"
    #     if provider_response is not None:
    #         ob.payload = {**(ob.payload or {}),
    #                       "provider_response": provider_response}
    #     session.add(ob)
    #     await session.flush()

    #     payload = ob.payload or {}
    #     idemp = payload.get("idempotency_key")
    #     user_id = payload.get("user_id")
    #     if idemp and user_id:
    #         try:
    #             await self.update_idempotency_recovery(session, idempotency_key=idemp, user_id=UUID(user_id), recovery_point=RecoveryPoint.FAILED, response_code=502, response_body=provider_response)
    #         except Exception:
    #             # Best-effort: don't fail the outbox failure handling
    #             pass


transaction_repo = TransactionRepo()
