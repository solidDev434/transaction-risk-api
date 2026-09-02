from collections.abc import AsyncGenerator

from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from .config import config

# Async Engine
async_engine = AsyncEngine(
    create_engine(
        url=config.ASYNC_DATABASE_URL,
        echo=False
    )
)


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Sync Engine
sync_engine = create_engine(
    url=config.SYNC_DATABASE_URL,
    echo=False
)
