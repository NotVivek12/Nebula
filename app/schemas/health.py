from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Schema for individual system service health statuses."""

    status: str
    latency_ms: float | None = None
    details: str | None = None


class HealthResponse(BaseModel):
    """Schema for the overall application health check endpoint response."""

    status: str
    database: ServiceStatus
    redis: ServiceStatus
    environment: str
