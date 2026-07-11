from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class MessageResponse(BaseModel):
    message: str
