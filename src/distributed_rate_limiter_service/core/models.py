from pydantic import BaseModel


class RateLimitCheckRequest(BaseModel):
    subject: str
    capacity: int
    refill_rate: float | None
    leak_rate: float | None
    window_size: float | None
