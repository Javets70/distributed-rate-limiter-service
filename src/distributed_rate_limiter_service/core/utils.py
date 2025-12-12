from fastapi import Request
from redis.asyncio import Redis

from distributed_rate_limiter_service.service.redis import RedisService


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_redis_service(request: Request) -> RedisService:
    return request.app.state.redis_service
