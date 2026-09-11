from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import init_db, async_engine
from .config import config
from app.cache.redis_client import redis_client

# Routers
from .auth.router import router as auth_router
from .users.router import router as user_router
from .wallet.router import router as wallet_router
from .transactions.router import router as transactions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    await init_db()
    # connect redis
    await redis_client.connect()
    yield
    # Shotdown: dispose of the engine
    await async_engine.dispose()
    await redis_client.disconnect()


app = FastAPI(
    title="Transaction Risk API",
    version=config.VERSION,
    lifespan=lifespan
)


@app.get("/health")
async def read_health():
    return {"status": "healthy"}


app.include_router(auth_router, prefix=f"/api/{config.VERSION}")
app.include_router(user_router, prefix=f"/api/{config.VERSION}")
app.include_router(wallet_router, prefix=f"/api/{config.VERSION}")
app.include_router(transactions_router, prefix=f"/api/{config.VERSION}")
