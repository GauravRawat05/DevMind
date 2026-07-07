"""API integration tests for DevMind Phase 5 JWT Auth endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import engine, AsyncSessionLocal
from backend.main import app
from backend.models.pg_models import User, Job
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_users() -> None:
    """Clean up any test users created during tests."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.email.like("test_%@example.com")))
        await session.commit()
    try:
        await engine.dispose()
    except Exception:
        pass


class TestAuthAPI:
    """Verify that the FastAPI Auth endpoints perform correctly."""

    async def test_register_and_login_flow(self) -> None:
        """Register a user, try registering again with same email, then login."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = "test_user_register@example.com"
            password = "testpassword123"

            # 1. Register successfully
            reg_response = await client.post(
                "/api/auth/register",
                json={"email": email, "password": password}
            )
            assert reg_response.status_code == 201
            reg_data = reg_response.json()
            assert "access_token" in reg_data
            assert reg_data["email"] == email

            # 2. Register again with same email -> 400 Bad Request
            dup_response = await client.post(
                "/api/auth/register",
                json={"email": email, "password": "differentpassword"}
            )
            assert dup_response.status_code == 400
            assert "already exists" in dup_response.json()["detail"]

            # 3. Login with correct credentials
            login_response = await client.post(
                "/api/auth/login",
                json={"email": email, "password": password}
            )
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "access_token" in login_data
            assert login_data["email"] == email

            # 4. Login with incorrect password
            wrong_pass_response = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "wrongpassword"}
            )
            assert wrong_pass_response.status_code == 401
            assert "Incorrect email or password" in wrong_pass_response.json()["detail"]

    async def test_get_profile_endpoints(self) -> None:
        """Get profile details using JWT auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = "test_profile_endpoint@example.com"
            password = "testpassword123"

            # 1. Try accessing /me without token -> 401
            unauth_response = await client.get("/api/auth/me")
            assert unauth_response.status_code == 401

            # 2. Register to get token
            reg_response = await client.post(
                "/api/auth/register",
                json={"email": email, "password": password}
            )
            assert reg_response.status_code == 201
            token = reg_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 3. Access /me with token -> 200
            profile_response = await client.get("/api/auth/me", headers=headers)
            assert profile_response.status_code == 200
            profile_data = profile_response.json()
            assert profile_data["email"] == email
            assert "id" in profile_data

            # 4. Access /me/jobs with token -> 200 (empty list initially)
            jobs_response = await client.get("/api/auth/me/jobs", headers=headers)
            assert jobs_response.status_code == 200
            assert isinstance(jobs_response.json(), list)
            assert len(jobs_response.json()) == 0
