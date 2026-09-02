import asyncio
import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import async_engine
from app.jobs import provider
from app.transactions.repo import transaction_repo
from app.transactions.model import TransactionOutbox, TransactionStatus

logger = logging.getLogger(__name__)

# session factory for workers
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False)

# maximum attempts before moving to dead-letter
MAX_OUTBOX_ATTEMPTS = 5


async def process_outbox_once() -> bool:
    """Process a single outbox row if available. Returns True if work was done.

    1. Reserve one pending outbox row (marks it `processing`, increments attempts).
    2. Call the provider with the outbox payload (outside DB transaction).
    3a. On success: run Phase 2 inside a DB transaction (capture funds, credit receiver, mark txn cleared, mark outbox processed).
    3b. On failure/timeout: attach provider response and leave row as `pending` for retries.
    """

    # 1) reserve an outbox row
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                outbox = await transaction_repo.reserve_pending_outbox(session)
                if not outbox:
                    return False
                outbox_id = outbox.id
                payload = outbox.payload
        except SQLAlchemyError:
            logger.exception("Failed to reserve outbox row")
            return False

    # check attempts and move to dead-letter if exceeded
    if getattr(outbox, "attempts", 0) >= MAX_OUTBOX_ATTEMPTS:
        logger.warning(
            "Outbox %s exceeded max attempts (%s), marking failed", outbox_id, outbox.attempts)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await transaction_repo.mark_outbox_failed(session, outbox_id, provider_response={"error": "max_attempts_exceeded"})
        return True

    # 2) call external provider outside DB transaction
    try:
        resp = await provider.process_payment(payload)
    except Exception as exc:
        logger.warning("Provider call failed (will retry): %s", exc)
        # attach error info and mark pending again for retry
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await transaction_repo.mark_outbox_pending(session, outbox_id, provider_response={"error": str(exc)})
        return True

    # 3) handle provider response
    if resp.get("status") == "success":
        # Phase 2: finalize everything atomically
        async with AsyncSessionLocal() as session:
            try:
                async with session.begin():
                    await transaction_repo.complete_outbox_phase2(session, outbox_id, resp)
            except Exception:
                logger.exception(
                    "Phase 2 failed for outbox %s, will reset for retry", outbox_id)
                async with AsyncSessionLocal() as session2:
                    async with session2.begin():
                        await transaction_repo.mark_outbox_pending(session2, outbox_id, provider_response={"error": "phase2_failure"})
                return True

        logger.info("Outbox %s processed successfully", outbox_id)
        return True

    # provider returned a soft failure — persist response and keep for retry
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await transaction_repo.mark_outbox_pending(session, outbox_id, provider_response=resp)

    logger.info("Outbox %s provider indicated failure, will retry", outbox_id)
    return True


async def run_worker(poll_interval: float = 10.0, max_idle_sleep: float = 20.0) -> None:
    logger.info("Starting outbox worker")
    idle_count = 0
    while True:
        try:
            did_work = await process_outbox_once()
        except asyncio.CancelledError:
            logger.info("Outbox worker cancelled")
            raise
        except Exception:
            logger.exception("Outbox worker iteration failed — continuing")
            did_work = False

        if not did_work:
            idle_count += 1
            await asyncio.sleep(min(max_idle_sleep, poll_interval * (idle_count or 1)))
        else:
            idle_count = 0
            await asyncio.sleep(0)
