from fastapi import APIRouter, Depends, HTTPException
from typing import Literal
import math

from app.core.utils import get_redis_service
from app.service.redis import RedisService
from app.core.models import RateLimitCheckRequest

router = APIRouter(prefix="/v1", tags=["RateLimitCheck"])


@router.post("/check/{algorithm}")
async def check_rate_limit(
    payload: RateLimitCheckRequest,
    algorithm: Literal["token_bucket", "leaky_bucket"],
    redis_service: RedisService = Depends(get_redis_service),
):
    if algorithm == "token_bucket":
        if not payload.refill_rate:
            raise HTTPException(status_code=400, detail="refill_rate not found")
        result = await redis_service.check_token_bucket(
            payload.subject, payload.capacity, payload.refill_rate
        )
        retry_after = math.ceil(1 / payload.refill_rate)

    elif algorithm == "leaky_bucket":
        if not payload.leak_rate:
            raise HTTPException(status_code=400, detail="leak_rate not found")
        result = await redis_service.check_leaky_bucket(
            payload.subject, payload.capacity, payload.leak_rate
        )
        retry_after = math.ceil(1 / payload.leak_rate)

    if not result["allowed"]:
        headers = {
            "Retry-After": retry_after,
            "X-RateLimit-Remaining": result["remaining"],
            "X-RateLimit-Limit": payload.capacity,
        }
        raise HTTPException(status_code=429, detail=result, headers=headers)

    return result
