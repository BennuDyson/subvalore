from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
