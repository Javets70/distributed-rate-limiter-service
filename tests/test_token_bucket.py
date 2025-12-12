import asyncio
import pytest


@pytest.mark.asyncio
async def test_token_bucket_allows_under_limit(redis_service):
    subject = "user:1:endpoint:/orders"
    capacity = 5
    refill_rate = 1.0

    r1 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    r2 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    r3 = await redis_service.check_token_bucket(subject, capacity, refill_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is True
    assert r3["remaining"] <= capacity - 3


@pytest.mark.asyncio
async def test_token_bucket_blocks_over_limit(redis_service):
    subject = "user:2:endpoint:/orders"
    capacity = 2
    refill_rate = 1.0

    r1 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    r2 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    r3 = await redis_service.check_token_bucket(subject, capacity, refill_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time(redis_service):
    subject = "user:3:endpoint:/orders"
    capacity = 2
    refill_rate = 1.0

    r1 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    r2 = await redis_service.check_token_bucket(subject, capacity, refill_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True

    await asyncio.sleep(1.2)

    r3 = await redis_service.check_token_bucket(subject, capacity, refill_rate)
    assert r3["allowed"] is True
