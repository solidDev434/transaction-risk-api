from redis.asyncio import Redis, ConnectionPool
import logging

from app.config import config


logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.pool: ConnectionPool = None
        self.client: Redis = None

    async def connect(self):
        self.pool = ConnectionPool.from_url(
            config.REDIS_URL,
            max_connections=50,
            decode_responses=True
        )
        self.client = Redis(connection_pool=self.pool)

        logger.info("Redis client connected")

    async def disconnect(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

        logger.info("Redis client disconnected")

    def get_client(self) -> Redis:
        return self.client


redis_client = RedisClient()
