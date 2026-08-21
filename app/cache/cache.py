import json
from redis.asyncio import Redis
from typing import Any, Optional, TypeVar

T = TypeVar("T")


class CacheService:
    def __init__(self, redis: Redis, prefix: str = "cache"):
        self.redis = redis
        self.prefix = prefix

    def _key(self, name: str) -> str:
        return f"{self.prefix}:{name}"

    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(self._key(key))

        if data:
            return json.loads(data)

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300
    ) -> None:
        await self.redis.setex(
            self._key(key),
            ttl,
            json.dumps(value, default=str)
        )

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(self._key(key)) > 0


def get_cache() -> CacheService:
    """Dependency provider for CacheService using the global redis client."""
    from app.cache.redis_client import redis_client

    client = redis_client.get_client()
    return CacheService(client)
