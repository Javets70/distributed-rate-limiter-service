import pytest
import pytest_asyncio
import asyncio
from redis.asyncio import Redis
from distributed_rate_limiter_service.service.redis import RedisService

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def redis_client():
    # Use test database index 9 (safe for tests)
    client = Redis(host="localhost", port=6379, db=9, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def redis_service(redis_client):
    """Provide a RedisService instance for testing."""
    service = RedisService(redis=redis_client)
    return service
