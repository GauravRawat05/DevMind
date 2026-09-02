"""FastAPI router for downloading generated documentation and full reports."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.pg_models import Job
from backend.models.mongo_models import get_qa_history
from backend.services.s3_service import storage_service
from backend.services.report_generator import generate_pdf_report, generate_docx_report

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


@router.get(
    "/download/{job_id}/report",
    summary="Download a full analysis report (PDF or DOCX) combining all agent outputs"
)
async def download_full_report(
    job_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$", description="Report format: 'pdf' or 'docx'"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download a comprehensive report combining Documentation,
    Code Review, Analytics, and Q&A results."""
    logger.info("Request to download full %s report for job: %s", format, job_id)

    # 1. Fetch job from PostgreSQL
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID {job_id} not found."
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is not yet complete (status: {job.status}). Please wait for completion."
        )

    # 2. Fetch Q&A history from MongoDB
    qa_history = await get_qa_history(job_id)

    # 3. Generate report
    try:
        if format == "docx":
            content = generate_docx_report(
                job_id=job.id,
                repo_url=job.repo_url,
                doc_output=job.doc_output,
                review_output=job.review_output,
                analytics_output=job.analytics_output,
                qa_history=qa_history,
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"DevMind_Report_{job_id[:8]}.docx"
        else:
            content = generate_pdf_report(
                job_id=job.id,
                repo_url=job.repo_url,
                doc_output=job.doc_output,
                review_output=job.review_output,
                analytics_output=job.analytics_output,
                qa_history=qa_history,
            )
            media_type = "application/pdf"
            filename = f"DevMind_Report_{job_id[:8]}.pdf"
    except Exception as exc:
        logger.exception("Failed to generate %s report for job %s", format, job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {exc}"
        )

    logger.info("Generated %s report for job %s (%d bytes)", format, job_id, len(content))

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

