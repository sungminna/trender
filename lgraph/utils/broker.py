"""Redis Pub/Sub broker for cross-process WebSocket notifications"""
import os
import json
import asyncio
from typing import AsyncGenerator

# Prefer the modern redis-py asyncio support. This avoids the legacy
# aioredis package, which still imports the removed `distutils` module
# and therefore crashes on Python ≥3.12.
try:
    import redis.asyncio as aioredis  # type: ignore
except ImportError:  # Fallback for environments that still have aioredis installed
    import aioredis  # type: ignore

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CHANNEL_NAME = "lgraph_ws"

class RedisBroker:
    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._subscriber = None

    async def _get_conn(self) -> aioredis.Redis:
        if self._redis is None:
            # `from_url` in both redis.asyncio and aioredis ≥2 returns a connection
            # instance synchronously. No need to await.
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def publish(self, message: dict):
        redis = await self._get_conn()
        await redis.publish(CHANNEL_NAME, json.dumps(message, ensure_ascii=False))

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        redis = await self._get_conn()
        if self._subscriber is None:
            self._subscriber = redis.pubsub()
            await self._subscriber.subscribe(CHANNEL_NAME)
        async for msg in self._subscriber.listen():
            if msg["type"] == "message":
                try:
                    yield json.loads(msg["data"])
                except json.JSONDecodeError:
                    continue

broker = RedisBroker() 