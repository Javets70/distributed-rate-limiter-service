from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Distributed Rate Limiter"
    environment: str = "dev"
    redis_url: str = "redis://localhost:6397/0"

    class Config:
        env_file = ".env"


settings = Settings()
