"""Unit and integration tests for the local S3 mock service and download endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import engine, AsyncSessionLocal
from backend.main import app
from backend.models.pg_models import Job
from backend.services.s3_service import storage_service
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_jobs() -> None:
    """Clean up any test jobs created during tests and clear mock S3 files."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Job).where(Job.repo_url == "https://github.com/test-s3/mock-repo"))
        await session.commit()
        
    # Cleanup mock S3 files for testing
    for key in storage_service.list_files(prefix="test_"):
        storage_service.delete_file(key)
        
    try:
        await engine.dispose()
    except Exception:
        pass


async def test_s3_service_file_operations() -> None:
    """Verify mock S3 service file upload, download, delete, and list operations."""
    key = "test_s3_service/test_file.txt"
    content = "Hello, local S3 mock storage!"
    
    # 1. Upload file
    upload_res = storage_service.upload_file(key, content)
    assert upload_res.startswith("s3://")
    
    # 2. Download file
    download_res = storage_service.download_file(key)
    assert download_res.decode("utf-8") == content
    
    # 3. List files
    files = storage_service.list_files(prefix="test_s3_service/")
    assert key in files
    
    # 4. Delete file
    delete_res = storage_service.delete_file(key)
    assert delete_res is True
    
    # 5. Download after delete should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        storage_service.download_file(key)


async def test_download_endpoint() -> None:
    """Verify that GET /api/download/{job_id}/doc fetches correct content from mock S3."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a test job in PG
        async with AsyncSessionLocal() as session:
            job = Job(
                repo_url="https://github.com/test-s3/mock-repo",
                status="completed",
                doc_output="This is test generated README content.",
                s3_doc_key="test_jobs/test_job_id/README.md"
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        # Upload dummy documentation to mock S3
        storage_service.upload_file(
            "test_jobs/test_job_id/README.md",
            "This is test generated README content."
        )

        try:
            # 1. Fetch file download from route
            download_response = await client.get(f"/api/download/{job_id}/doc")
            assert download_response.status_code == 200
            assert download_response.text == "This is test generated README content."
            assert "attachment" in download_response.headers.get("Content-Disposition", "")
            assert f"DevMind_README_{job_id[:8]}.md" in download_response.headers.get("Content-Disposition", "")

            # 2. Fetch download for non-existent job -> 404
            fake_job_id = "00000000-0000-0000-0000-000000000000"
            not_found_response = await client.get(f"/api/download/{fake_job_id}/doc")
            assert not_found_response.status_code == 404

        finally:
            # Clean up the specific file
            storage_service.delete_file("test_jobs/test_job_id/README.md")
