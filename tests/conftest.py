"""
Pytest configuration and shared fixtures for Nebula test suite.

Provides:
  - async-capable test configuration
  - Integration test database setup (only loaded when DB is available)
  - FastAPI test client with auth helpers
  - Redis mock for unit tests
"""

import asyncio
import os
from typing import Generator

import pytest

# ──────────────────────────────────────────────────────────────
# Override settings BEFORE importing the app
# ──────────────────────────────────────────────────────────────
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-32-chars-long-ok")
os.environ.setdefault("POSTGRES_SERVER", "127.0.0.1")
os.environ.setdefault("POSTGRES_DB", "nebula_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("WHATSAPP_APP_SECRET", "test_app_secret_for_hmac_testing")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test_verify_token")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
