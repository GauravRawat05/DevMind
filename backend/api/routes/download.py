"""FastAPI router for downloading generated documentation from S3 storage."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.pg_models import Job
from backend.services.s3_service import storage_service

logger = logging.getLogger("devmind.api.download")

router = APIRouter(prefix="/api", tags=["download"])


@router.get(
    "/download/{job_id}/doc",
    summary="Download the generated README.md from S3 mock storage"
)
async def download_job_documentation(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Retrieves the generated documentation for a job from mock S3 and streams it as a file download."""
    logger.info("Request to download documentation for job: %s", job_id)
    
    # 1. Fetch job from database to verify it exists and get s3_doc_key
    job = await db.get(Job, job_id)
    if not job:
        logger.warning("Job %s not found in PostgreSQL", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID {job_id} not found."
        )
        
    if not job.s3_doc_key:
        logger.warning("Job %s has no associated S3 doc key. (status=%s)", job_id, job.status)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated documentation is not available or not stored in S3 for this job."
        )

    # 2. Fetch from S3 Mock
    try:
        content = storage_service.download_file(job.s3_doc_key)
    except FileNotFoundError as exc:
        logger.error("Documentation file for key '%s' not found in S3: %s", job.s3_doc_key, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documentation file not found in storage."
        )
    except Exception as exc:
        logger.error("Failed to download file from S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documentation from storage: {exc}"
        )

    # 3. Return file as attachment response
    filename = f"DevMind_README_{job_id[:8]}.md"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
