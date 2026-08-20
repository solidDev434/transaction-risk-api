from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import init_db, async_engine
from .config import config

# Routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    await init_db()
    yield
    # Shotdown: dispose of the engine
    await async_engine.dispose()


app = FastAPI(
    title="Transaction Risk API",
    version=config.version,
    lifespan=lifespan
)


@app.get("/health")
async def read_health():
    return {"status": "healthy"}
