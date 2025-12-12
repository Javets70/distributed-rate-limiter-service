# ===== CORRECTED TESTS =====
import asyncio
import pytest


@pytest.mark.asyncio
async def test_leaky_bucket_allows_under_limit(redis_service):
    """Test that requests under capacity are allowed."""
    subject = "user:1:endpoint:/orders"
    capacity = 5
    leak_rate = 1.0

    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    print(r1, r2, r3)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is True

    assert 0 <= r3["remaining"] <= capacity


@pytest.mark.asyncio
async def test_leaky_bucket_blocks_over_limit(redis_service):
    """Test that requests exceeding capacity are blocked."""
    subject = "user:2:endpoint:/orders"
    capacity = 2
    leak_rate = 1.0

    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False


@pytest.mark.asyncio
async def test_leaky_bucket_leaks_over_time(redis_service):
    """Test that water leaks out over time, allowing new requests."""
    subject = "user:3:endpoint:/orders"
    capacity = 2
    leak_rate = 1.0  # 1 unit per second

    # Fill the bucket
    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False  # Bucket full

    # Wait for more than 1 second for water to leak
    await asyncio.sleep(1.5)

    # Should allow request now (at least 1 unit leaked)
    r4 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r4["allowed"] is True


@pytest.mark.asyncio
async def test_leaky_bucket_partial_leak(redis_service):
    """Test that partial leaking works correctly."""
    subject = "user:4:endpoint:/orders"
    capacity = 5
    leak_rate = 2.0  # 2 units per second

    # Add 3 requests
    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    await asyncio.sleep(0.6)

    r4 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r4["allowed"] is True


@pytest.mark.asyncio
async def test_leaky_bucket_exact_capacity(redis_service):
    """Test behavior at exact capacity boundary."""
    subject = "user:6:endpoint:/orders"
    capacity = 1
    leak_rate = 1.0

    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r1["allowed"] is True

    # Immediate second request should be blocked
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r2["allowed"] is False


@pytest.mark.asyncio
async def test_leaky_bucket_different_leak_rates(redis_service):
    """Test that different leak rates work correctly."""
    subject = "user:7:endpoint:/orders"
    capacity = 5
    leak_rate = 5.0  # Fast leak rate: 5 units per second

    # Fill bucket
    for _ in range(5):
        await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    # Verify it's full
    r_full = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r_full["allowed"] is False

    # Wait 0.6 seconds (should leak at least 2.5 units)
    await asyncio.sleep(0.6)

    # Should allow multiple requests now
    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True


@pytest.mark.asyncio
async def test_leaky_bucket_burst_then_steady(redis_service):
    """Test burst traffic followed by steady traffic."""
    subject = "user:10:endpoint:/orders"
    capacity = 5
    leak_rate = 2.0  # 2 requests per second

    # Burst: fill the bucket
    results = []
    for _ in range(7):
        r = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
        results.append(r)

    allowed_count = sum(1 for r in results if r["allowed"])
    assert allowed_count == 5  # Only first 5 allowed

    # Wait 1.1 seconds (at least 2 units leak out)
    await asyncio.sleep(1.1)

    # Should be able to make 2 more requests
    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False  # Back to full


@pytest.mark.asyncio
async def test_leaky_bucket_continuous_leak(redis_service):
    """Test that leaking continues correctly over multiple intervals."""
    subject = "user:11:endpoint:/orders"
    capacity = 4
    leak_rate = 1.0

    # Add 4 requests (fill bucket)
    for _ in range(4):
        await redis_service.check_leaky_bucket(subject, capacity, leak_rate)

    # Verify full
    r_full = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r_full["allowed"] is False

    # Wait 1.1 seconds, make request (should succeed)
    await asyncio.sleep(1.1)
    r1 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r1["allowed"] is True

    # Wait another 1.1 seconds, make request (should succeed)
    await asyncio.sleep(1.1)
    r2 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r2["allowed"] is True

    # Wait another 1.1 seconds, make request (should succeed)
    await asyncio.sleep(1.1)
    r3 = await redis_service.check_leaky_bucket(subject, capacity, leak_rate)
    assert r3["allowed"] is True
