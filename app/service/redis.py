from redis.asyncio import Redis
import time


class RedisService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_token_bucket(self, subject, capacity, refill_rate):
        key = f"tb:{subject}"
        result = await self.redis.hgetall(key)

        # sainity validation
        now = time.time()
        # no existing bucket
        if not result.get("tokens") or not result.get("last_refill_ts"):
            elapsed_ts = now
            new_tokens = capacity
        else:
            elapsed_ts = now - float(result.get("last_refill_ts"))
            new_tokens = min(
                capacity, elapsed_ts * refill_rate + int(result.get("tokens"))
            )

        if new_tokens < 1:
            return {"allowed": False, "remaining": new_tokens}

        new_tokens -= 1
        await self.redis.hset(
            name=key, mapping={"tokens": new_tokens, "last_refill_ts": now}
        )

        return {"allowed": True, "remaining": new_tokens}
