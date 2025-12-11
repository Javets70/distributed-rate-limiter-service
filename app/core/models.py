from pydantic import BaseModel


class RateLimitCheckRequest(BaseModel):
    subject: str
    capacity: int
    refill_rate: float
