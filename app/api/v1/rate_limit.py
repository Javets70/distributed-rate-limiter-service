from fastapi import APIRouter, Depends, HTTPException

from app.core.utils import get_redis_service
from app.service.redis import RedisService
from app.core.models import RateLimitCheckRequest

router = APIRouter(prefix="/v1", tags=["RateLimitCheck"])


@router.post("/check/")
async def check_rate_limit(
    payload: RateLimitCheckRequest,
    redis_service: RedisService = Depends(get_redis_service),
):
    result = await redis_service.check_token_bucket(
        payload.subject, payload.capacity, payload.refill_rate
    )

    if not result["allowed"]:
        raise HTTPException(status_code=429, detail=result)

    return result
