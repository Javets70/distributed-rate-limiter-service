from fastapi import FastAPI
from redis.asyncio import Redis
from contextlib import asynccontextmanager

from distributed_rate_limiter_service.api.v1.health import router as health_router
from distributed_rate_limiter_service.api.v1.rate_limit import (
    router as rate_limit_router,
)
from distributed_rate_limiter_service.core.config import settings
from distributed_rate_limiter_service.service.redis import RedisService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup
    app.state.redis = Redis.from_url(settings.redis_url)
    app.state.redis_service = RedisService(app.state.redis)
    yield

    # App shuts down
    await app.state.redis.close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # include routers
    app.include_router(health_router)
    app.include_router(rate_limit_router)

    return app


app = create_app()
