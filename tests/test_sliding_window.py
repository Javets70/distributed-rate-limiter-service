import asyncio
import pytest


@pytest.mark.asyncio
async def test_sliding_window_allows_under_limit(redis_service):
    """Test that requests under the limit are allowed."""
    subject = "user:1:endpoint:/api"
    limit = 5
    window_seconds = 10

    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r3 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is True
    assert r3["remaining"] >= 2  # At least 2 requests remaining


@pytest.mark.asyncio
async def test_sliding_window_blocks_over_limit(redis_service):
    """Test that requests exceeding the limit are blocked."""
    subject = "user:2:endpoint:/api"
    limit = 3
    window_seconds = 10

    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r3 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r4 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is True
    assert r4["allowed"] is False  # Should be blocked
    assert r4["remaining"] == 0


@pytest.mark.asyncio
async def test_sliding_window_slides_over_time(redis_service):
    """Test that the window slides and old requests expire."""
    subject = "user:3:endpoint:/api"
    limit = 2
    window_seconds = 2  # Short window for testing

    # Fill the bucket
    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r3 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False  # Bucket full

    # Wait for window to slide (first request expires)
    await asyncio.sleep(2.1)

    r4 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r4["allowed"] is True  # Should be allowed now


@pytest.mark.asyncio
async def test_sliding_window_partial_expiry(redis_service):
    """Test that only expired requests are removed from the window."""
    subject = "user:4:endpoint:/api"
    limit = 3
    window_seconds = 3

    # Make 2 requests
    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True

    # Wait 1.5 seconds and make another request
    await asyncio.sleep(1.5)
    r3 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r3["allowed"] is True

    # This should be blocked (3 requests in window)
    r4 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r4["allowed"] is False

    # Wait another 1.6 seconds (total 3.1s from start)
    # First two requests should have expired
    await asyncio.sleep(1.6)

    r5 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r5["allowed"] is True  # r1 and r2 expired, only r3 in window


@pytest.mark.asyncio
async def test_sliding_window_exact_limit(redis_service):
    """Test behavior at exact limit boundary."""
    subject = "user:5:endpoint:/api"
    limit = 1
    window_seconds = 5

    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r1["allowed"] is True
    assert r1["remaining"] == 0

    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r2["allowed"] is False
    assert r2["remaining"] == 0


@pytest.mark.asyncio
async def test_sliding_window_multiple_subjects(redis_service):
    """Test that different subjects have independent windows."""
    limit = 2
    window_seconds = 10

    subject_a = "user:6:endpoint:/api"
    subject_b = "user:7:endpoint:/api"

    # Fill subject_a
    r1 = await redis_service.check_sliding_window(subject_a, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject_a, limit, window_seconds)
    r3 = await redis_service.check_sliding_window(subject_a, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True
    assert r3["allowed"] is False  # subject_a is full

    # subject_b should still be available
    r4 = await redis_service.check_sliding_window(subject_b, limit, window_seconds)
    r5 = await redis_service.check_sliding_window(subject_b, limit, window_seconds)

    assert r4["allowed"] is True
    assert r5["allowed"] is True


@pytest.mark.asyncio
async def test_sliding_window_rapid_requests(redis_service):
    """Test behavior with rapid successive requests."""
    subject = "user:8:endpoint:/api"
    limit = 10
    window_seconds = 5

    # Make rapid requests
    results = []
    for _ in range(12):
        result = await redis_service.check_sliding_window(
            subject, limit, window_seconds
        )
        results.append(result)

    allowed_count = sum(1 for r in results if r["allowed"])
    blocked_count = sum(1 for r in results if not r["allowed"])

    assert allowed_count == 10  # Exactly 10 should be allowed
    assert blocked_count == 2  # Exactly 2 should be blocked


@pytest.mark.asyncio
async def test_sliding_window_reset_after_full_window(redis_service):
    """Test that limit resets after full window duration passes."""
    subject = "user:9:endpoint:/api"
    limit = 2
    window_seconds = 1

    # Use up the limit
    r1 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r2 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r1["allowed"] is True
    assert r2["allowed"] is True

    r3 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    assert r3["allowed"] is False

    # Wait for full window to pass
    await asyncio.sleep(1.1)

    # Should have full limit again
    r4 = await redis_service.check_sliding_window(subject, limit, window_seconds)
    r5 = await redis_service.check_sliding_window(subject, limit, window_seconds)

    assert r4["allowed"] is True
    assert r5["allowed"] is True
