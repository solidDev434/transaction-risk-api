import asyncio
from random import choices
from sqlmodel.ext.asyncio.session import AsyncSession
from app.config import config
from .celery import celery_app
from app.database import SyncSessionLocal as Session
from app.users.model import User
from app.wallet.model import Wallet
from app.transactions.model import Transaction, IdempotencyKey


@celery_app.task(name="drain_transaction_outbox")
def drain_transaction_outbox():
    try:
        random_num = choices(range(1, 200))[0]
        with Session() as session:
            new_user = User(
                name=f"Frank{random_num}",
                email=f"frankpeters{random_num}@gmail.com",
                hashed_password="dfsdfsfdsffs"
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return {"id": str(new_user.id), "email": new_user.email}
    except Exception as exc:
        print(f"Logging error {exc}")
        raise
