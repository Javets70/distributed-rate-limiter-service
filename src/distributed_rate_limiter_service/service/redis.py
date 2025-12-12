from redis.asyncio import Redis
import time

CHECK_TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local data = redis.call("HGETALL" , key)

local tokens = nil
local last_refill = nil

for i = 1, #data, 2 do
    if data[i] == "tokens" then
        tokens = tonumber(data[i+1])
    elseif data[i] == "last_refill_ts" then
        last_refill = tonumber(data[i+1])
    end
end

local new_tokens
local elapsed_ts

if tokens == nil or last_refill == nil then
    new_tokens = capacity
else
    elapsed_ts = now - last_refill
    new_tokens = math.min(capacity , tokens + (elapsed_ts * refill_rate ))
end

if new_tokens < 1 then
    return {0, new_tokens}
end

new_tokens = new_tokens - 1
redis.call('HSET' , key , "tokens" , new_tokens , "last_refill_ts" , now)
return {1 , new_tokens}

"""

CHECK_LEAKY_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local leak_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local data = redis.call("HGETALL", key)
local water_level = nil
local last_leaked_ts = nil

for i = 1, #data, 2 do
    if data[i] == "water_level" then
        water_level = tonumber(data[i+1])
    elseif data[i] == "last_leaked_ts" then
        last_leaked_ts = tonumber(data[i+1])
    end
end

if water_level == nil or last_leaked_ts == nil then
    water_level = 0
    last_leaked_ts = now
else
    local elapsed_ts = now - last_leaked_ts
    local leaked = elapsed_ts * leak_rate
    water_level = math.max(0, water_level - leaked)
end

if water_level + 1 > capacity then
    return {0, water_level}
end

water_level = water_level + 1
redis.call("HSET", key, "water_level", tostring(water_level), "last_leaked_ts", tostring(now))

redis.call("EXPIRE", key, math.ceil(capacity / leak_rate) + 60)

return {1, water_level}
"""

CHECK_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]

local capacity = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

redis.call("ZREMRANGEBYSCORE" , key , "-inf", now - window_size)

local count = redis.call("ZCARD" , key)

if count >= capacity then
    return {0, count}
end

redis.call("ZADD" , key, now, now)

redis.call("EXPIRE" , key, window_size)

return {1, count+1}

"""


class RedisService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_token_bucket(
        self, subject: str, capacity: float, refill_rate: float
    ):
        key = f"tb:{subject}"
        now = time.time()

        script = self.redis.register_script(CHECK_TOKEN_BUCKET_SCRIPT)

        allowed, remaining = await script(keys=[key], args=[capacity, refill_rate, now])

        return {"allowed": bool(allowed), "remaining": remaining}

    async def check_leaky_bucket(self, subject: str, capacity: float, leak_rate: float):
        key = f"lb:{subject}"
        now = time.time()

        script = self.redis.register_script(CHECK_LEAKY_BUCKET_SCRIPT)

        allowed, water_level = await script(keys=[key], args=[capacity, leak_rate, now])

        print("REDIS FUNC", capacity, water_level)
        return {"allowed": bool(allowed), "remaining": max(0, capacity - water_level)}

    async def check_sliding_window(
        self, subject: str, capacity: float, window_size: float
    ):
        key = f"sw:{subject}"
        now = time.time()

        script = self.redis.register_script(CHECK_SLIDING_WINDOW_SCRIPT)

        allowed, count = await script(keys=[key], args=[capacity, window_size, now])

        return {"allowed": bool(allowed), "remaining": capacity - count}
