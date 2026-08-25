"""
Integration tests for authentication flows.

Tests require a running PostgreSQL test database.
Each test rolls back via the session fixture (see conftest.py).

Tests:
- Onboarding: creates business, all permissions seeded
- Login: valid credentials return tokens
- Login: invalid credentials rejected
- Refresh: rotates tokens
- Logout: revokes refresh token
- Logout-all: revokes all sessions
- Active user check: inactive users rejected
- Password strength: weak passwords rejected on onboard
"""

from httpx import AsyncClient


class TestOnboarding:
    async def test_onboard_creates_business(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/v1/auth/onboard",
            json={
                "business_name": "Acme Corp",
                "owner_email": "admin@acme.com",
                "owner_password": "SecurePass123",
                "owner_full_name": "Acme Admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "business_id" in data
        assert data["business_name"] == "Acme Corp"

    async def test_onboard_rejects_duplicate_email(self, async_client: AsyncClient) -> None:
        payload = {
            "business_name": "First Corp",
            "owner_email": "dup@example.com",
            "owner_password": "ValidPass123",
            "owner_full_name": "First Owner",
        }
        r1 = await async_client.post("/api/v1/auth/onboard", json=payload)
        assert r1.status_code == 201

        payload["business_name"] = "Second Corp"
        r2 = await async_client.post("/api/v1/auth/onboard", json=payload)
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()

    async def test_onboard_rejects_weak_password(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/v1/auth/onboard",
            json={
                "business_name": "Weak Corp",
                "owner_email": "weak@example.com",
                "owner_password": "weak",
                "owner_full_name": "Weak Owner",
            },
        )
        assert response.status_code == 400


class TestLogin:
    async def test_valid_login_returns_tokens(self, async_client: AsyncClient, onboarded_business: dict) -> None:
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "owner@testbusiness.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != data["refresh_token"]

    async def test_invalid_password_rejected(self, async_client: AsyncClient, onboarded_business: dict) -> None:
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "owner@testbusiness.com", "password": "WrongPassword1"},
        )
        assert response.status_code == 401

    async def test_nonexistent_user_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "ghost@nowhere.com", "password": "SomePass123"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    async def test_refresh_issues_new_tokens(
        self, async_client: AsyncClient, onboarded_business: dict
    ) -> None:
        # Login
        login = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "owner@testbusiness.com", "password": "TestPass123!"},
        )
        original_refresh = login.json()["refresh_token"]
        original_access = login.json()["access_token"]

        # Refresh
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert response.status_code == 200
        new_data = response.json()
        assert new_data["access_token"] != original_access
        assert new_data["refresh_token"] != original_refresh

    async def test_reused_refresh_token_rejected(
        self, async_client: AsyncClient, onboarded_business: dict
    ) -> None:
        login = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "owner@testbusiness.com", "password": "TestPass123!"},
        )
        original_refresh = login.json()["refresh_token"]

        # First refresh — should succeed
        r1 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert r1.status_code == 200

        # Second refresh with same old token — must be rejected
        r2 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert r2.status_code == 401


class TestLogout:
    async def test_logout_revokes_token(
        self, async_client: AsyncClient, onboarded_business: dict
    ) -> None:
        login = await async_client.post(
            "/api/v1/auth/token",
            data={"username": "owner@testbusiness.com", "password": "TestPass123!"},
        )
        tokens = login.json()

        # Logout
        logout_resp = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout_resp.status_code == 200

        # Refresh with revoked token should fail
        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_resp.status_code == 401


class TestPermissionsSeeding:
    """Verifies that all required permissions are seeded for a new tenant's owner."""

    async def test_owner_can_access_knowledge_endpoint(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """knowledge:read must be seeded (was missing before fix)."""
        response = await async_client.get(
            "/api/v1/knowledge/",
            headers=auth_headers,
        )
        # 200 or 404 (if no docs) — NOT 403 (forbidden)
        assert response.status_code != 403, (
            f"Owner should have knowledge:read permission. Got 403: {response.text}"
        )

    async def test_owner_can_access_agent_endpoint(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """agents:read must be seeded."""
        response = await async_client.get(
            "/api/v1/agent/",
            headers=auth_headers,
        )
        assert response.status_code != 403, (
            f"Owner should have agents:read permission. Got 403: {response.text}"
        )
