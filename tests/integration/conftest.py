"""
Integration test conftest — requires running PostgreSQL and Redis.

Fixtures:
  - db: per-test session that rolls back after each test
  - async_client: httpx AsyncClient with DB override
  - auth_headers: pre-authenticated headers for owner user
  - onboarded_business: creates + returns a test business tenant
"""

from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models.agent  # noqa: F401
import app.models.agent_handoff  # noqa: F401
import app.models.business  # noqa: F401
import app.models.business_user  # noqa: F401
import app.models.contact  # noqa: F401
import app.models.contact_memory  # noqa: F401
import app.models.conversation  # noqa: F401
import app.models.integration  # noqa: F401
import app.models.invitation  # noqa: F401
import app.models.knowledge  # noqa: F401
import app.models.message  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.role  # noqa: F401
import app.models.tag  # noqa: F401

# Import all models to register metadata
import app.models.user  # noqa: F401
import app.models.webhook_event  # noqa: F401
import app.models.workflow  # noqa: F401
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.base import Base

# Test database — separate from dev database
TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/nebula_test"
)

test_engine = create_async_engine(TEST_DB_URL, pool_pre_ping=True, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables() -> AsyncGenerator[None, None]:
    """Creates all tables for the test session, drops them afterwards."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Per-test database session that rolls back after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        async with TestAsyncSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()


@pytest_asyncio.fixture()
async def async_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing async endpoints."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def onboarded_business(async_client: AsyncClient) -> dict:
    """Creates a new business tenant and returns the response data."""
    response = await async_client.post(
        "/api/v1/auth/onboard",
        json={
            "business_name": "Test Business",
            "owner_email": "owner@testbusiness.com",
            "owner_password": "TestPass123!",
            "owner_full_name": "Test Owner",
        },
    )
    assert response.status_code == 201, f"Onboard failed: {response.text}"
    return response.json()


@pytest_asyncio.fixture()
async def auth_headers(async_client: AsyncClient, onboarded_business: dict) -> dict:
    """Returns Authorization + X-Business-ID headers for the onboarded owner."""
    business_id = str(onboarded_business["business_id"])
    response = await async_client.post(
        "/api/v1/auth/token",
        data={
            "username": "owner@testbusiness.com",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Business-ID": business_id,
    }
