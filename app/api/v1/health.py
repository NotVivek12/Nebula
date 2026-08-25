"""
Health check endpoints.

GET /health        — Combined liveness + readiness (legacy compatibility)
GET /health/live   — Liveness probe: is the process running? Always 200.
GET /health/ready  — Readiness probe: are required dependencies available?

Kubernetes / Docker:
  livenessProbe  → GET /api/v1/health/live
  readinessProbe → GET /api/v1/health/ready
"""

import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.health import HealthResponse, ServiceStatus
from app.services.redis import redis_service

router = APIRouter()


@router.get("/live")
async def liveness() -> Any:
    """
    Liveness probe.

    Returns 200 if the process is alive. Does not check dependencies.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness() -> Any:
    """
    Readiness probe.

    Returns 200 only if all required dependencies are reachable.
    Returns 503 if any required dependency is unhealthy.
    Used by load balancers and orchestrators to route traffic.
    """
    checks: dict[str, bool] = {}

    # Database check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Redis check
    try:
        checks["redis"] = await redis_service.ping()
    except Exception:
        checks["redis"] = False

    all_ready = all(checks.values())
    http_status = 200 if all_ready else 503

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        },
    )


@router.get("", response_model=HealthResponse)
async def health_check() -> Any:
    """
    Combined health check with latency measurements.

    For Kubernetes probes, prefer /health/live and /health/ready.
    """
    # Database
    db_status = "healthy"
    db_latency = 0.0
    db_details: str | None = None
    try:
        start = time.perf_counter()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - start) * 1000
    except Exception as exc:
        db_status = "unhealthy"
        db_details = str(exc)

    # Redis
    redis_status = "healthy"
    redis_latency = 0.0
    redis_details: str | None = None
    try:
        start = time.perf_counter()
        ok = await redis_service.ping()
        redis_latency = (time.perf_counter() - start) * 1000
        if not ok:
            redis_status = "unhealthy"
            redis_details = "Ping returned False"
    except Exception as exc:
        redis_status = "unhealthy"
        redis_details = str(exc)

    overall = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"

    return HealthResponse(
        status=overall,
        database=ServiceStatus(status=db_status, latency_ms=round(db_latency, 2), details=db_details),
        redis=ServiceStatus(status=redis_status, latency_ms=round(redis_latency, 2), details=redis_details),
        environment=settings.ENVIRONMENT,
    )
