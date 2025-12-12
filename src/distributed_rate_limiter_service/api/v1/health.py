from fastapi import APIRouter, Depends

from distributed_rate_limiter_service.core.config import settings
from distributed_rate_limiter_service.core.utils import get_redis

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health_check(redis=Depends(get_redis)):
    try:
        redis_status = await redis.ping()
    except Exception:
        redis_status = False
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "redis": "UP" if redis_status else "DOWN",
    }
