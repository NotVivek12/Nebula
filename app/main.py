"""
Nebula FastAPI application entry point.

Startup sequence:
1. Validate configuration (production safety guard runs at import time in config.py)
2. Connect Redis
3. Load plugins
4. Register routers

Middleware stack (applied in reverse order — outermost first):
1. CORS
2. Rate limiting (Redis-backed)
3. Request ID + structured logging
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.services.plugins.loader import PluginLoader
from app.services.redis import redis_service

# Initialize structured logging before anything else
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Manages startup and shutdown lifecycle."""
    # Startup
    logger.info(
        "Starting Nebula",
        environment=settings.ENVIRONMENT,
        project=settings.PROJECT_NAME,
    )
    await redis_service.connect()

    # Load plugins from plugins/ directory
    loader = PluginLoader()
    loader.load_all_plugins()

    yield

    # Shutdown
    await redis_service.disconnect()
    logger.info("Nebula shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered customer communication and automation platform",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────────────────────────
# CORS — configured from environment, not hardcoded to "*"
# ──────────────────────────────────────────────────────────────
_cors_origins = settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Redis-backed rate limiting
# ──────────────────────────────────────────────────────────────
app.add_middleware(
    RateLimitMiddleware,
    limit=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


# ──────────────────────────────────────────────────────────────
# Request ID + structured logging middleware
# ──────────────────────────────────────────────────────────────
@app.middleware("http")
async def logging_and_request_id_middleware(request: Request, call_next: Any) -> Response:
    """Injects a unique request ID and logs request metadata + latency."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "Unhandled exception",
            status_code=500,
            latency_ms=round(elapsed_ms, 2),
            error=type(exc).__name__,
            # Do NOT include exc details that may contain secrets
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "request_id": request_id,
            },
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "Request processed",
        status_code=response.status_code,
        latency_ms=round(elapsed_ms, 2),
    )

    return response


# ──────────────────────────────────────────────────────────────
# Global exception handlers
# ──────────────────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Formats all HTTPExceptions into a consistent JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


# ──────────────────────────────────────────────────────────────
# Router registration
# ──────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)
