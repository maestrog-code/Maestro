from pydantic import BaseModel
from typing import Optional

class HealthCheckResponse(BaseModel):
    status: str
    database: str
    redis: str
    version: Optional[str] = None
