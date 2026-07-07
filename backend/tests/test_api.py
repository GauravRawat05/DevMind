"""API integration tests for DevMind Phase 3 REST endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import engine
from backend.main import app
from backend.models.pg_models import Job


import asyncio

@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """Manually create PostgreSQL tables before any tests run, then dispose engine."""
    from backend.models.pg_models import Base
    
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    try:
        asyncio.run(create_tables())
    except Exception as exc:
        print(f"Session DB Setup failed: {exc}")


@pytest.fixture(autouse=True)
def dispose_engine() -> None:
    """Dispose the SQLAlchemy engine pool after each test to avoid closed event loop errors."""
    yield
    try:
        asyncio.run(engine.dispose())
    except Exception:
        pass


@pytest.mark.asyncio
class TestAPIEndpoints:
    """Verify that the FastAPI REST endpoints perform correctly."""

    async def test_root_endpoint(self) -> None:
        """GET / should return basic api info."""
        transport = ASGITransport(app=app)



        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "DevMind API"
            assert data["status"] == "online"

    async def test_health_check_endpoint(self) -> None:
        """GET /health should return 200 or 503 depending on database status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            # Can be 200 or 503 depending on live connections, but status must be present
            assert response.status_code in (200, 503)
            data = response.json()
            assert "status" in data
            assert "services" in data
            assert "postgresql" in data["services"]
            assert "mongodb" in data["services"]
            assert "redis" in data["services"]

    async def test_analyze_endpoint_invalid_url(self) -> None:
        """POST /api/analyze with invalid GitHub URL should return 400 Bad Request."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Non-github URL
            response = await client.post(
                "/api/analyze",
                json={"repo_url": "https://gitlab.com/some/repo"}
            )
            assert response.status_code == 400
            assert "Invalid GitHub URL" in response.json()["detail"]

            # Empty URL
            response = await client.post(
                "/api/analyze",
                json={"repo_url": "   "}
            )
            assert response.status_code == 400

    async def test_analyze_and_get_results_workflow(self) -> None:
        """Submit a valid repo, verify job creation in Postgres, and fetch results."""
        from backend.core.database import AsyncSessionLocal

        repo_url = "https://github.com/tiangolo/fastapi"
        job_id = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Submit analyze request
            response = await client.post(
                "/api/analyze",
                json={"repo_url": repo_url}
            )
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            job_id = data["job_id"]
            assert data["repo_url"] == repo_url
            assert data["status"] == "pending"

            # 2. Retrieve results for the created job
            results_response = await client.get(f"/api/results/{job_id}")
            assert results_response.status_code == 200
            res_data = results_response.json()
            assert res_data["job_id"] == job_id
            assert res_data["repo_url"] == repo_url
            assert res_data["status"] == "pending"
            assert "results" in res_data
            assert res_data["results"]["doc"] is None  # Initial status

            # 3. Retrieve non-existent job results (404)
            fake_job_id = "00000000-0000-0000-0000-000000000000"
            not_found_response = await client.get(f"/api/results/{fake_job_id}")
            assert not_found_response.status_code == 404

        # Clean up: delete the test job from the database
        if job_id:
            async with AsyncSessionLocal() as session:
                await session.execute(delete(Job).where(Job.id == job_id))
                await session.commit()

    async def test_analyze_with_auth_workflow(self) -> None:
        """Submit a repository analysis with a valid user token, and verify the job is linked."""
        from backend.core.database import AsyncSessionLocal
        from backend.models.pg_models import User
        from sqlalchemy import select

        email = "test_api_auth_workflow@example.com"
        password = "password123"
        repo_url = "https://github.com/tiangolo/fastapi"
        job_id = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register test user
            reg_res = await client.post(
                "/api/auth/register",
                json={"email": email, "password": password}
            )
            assert reg_res.status_code == 201
            token = reg_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Submit analyze request with token
            response = await client.post(
                "/api/analyze",
                json={"repo_url": repo_url},
                headers=headers
            )
            assert response.status_code == 202
            data = response.json()
            job_id = data["job_id"]

            # 3. Retrieve user's jobs and verify the job is listed
            user_jobs_res = await client.get("/api/auth/me/jobs", headers=headers)
            assert user_jobs_res.status_code == 200
            user_jobs = user_jobs_res.json()
            assert len(user_jobs) == 1
            assert user_jobs[0]["job_id"] == job_id
            assert user_jobs[0]["repo_url"] == repo_url

        # Clean up: delete the test job and user from the database
        async with AsyncSessionLocal() as session:
            if job_id:
                await session.execute(delete(Job).where(Job.id == job_id))
            await session.execute(delete(User).where(User.email == email))
            await session.commit()


