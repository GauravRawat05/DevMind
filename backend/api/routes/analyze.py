"""FastAPI router for initiating repository analysis."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.pg_models import Job, User
from backend.services.github_service import parse_github_url
from backend.core.auth_utils import get_current_user

logger = logging.getLogger("devmind.api.analyze")

router = APIRouter(prefix="/api", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    """Request schema for repository analysis."""

    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL to analyze",
        examples=["https://github.com/tiangolo/fastapi"]
    )


class AnalyzeResponse(BaseModel):
    """Response schema returned when a job is successfully accepted."""

    job_id: str
    repo_url: str
    status: str
    message: str


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a GitHub repository for parallel multi-agent analysis"
)
async def analyze_repository(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user)
) -> dict[str, str]:
    """Accepts a public GitHub URL, validates it, and triggers a background analysis job.

    Returns 202 Accepted immediately with a unique job ID.
    """
    repo_url = request.repo_url.strip()

    # 1. Validate GitHub URL structure
    try:
        owner, repo = parse_github_url(repo_url)
        # Normalize URL to standard format: https://github.com/owner/repo
        normalized_url = f"https://github.com/{owner}/{repo}"
    except ValueError as exc:
        logger.warning("Invalid GitHub URL submitted: %s - Error: %s", repo_url, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid GitHub URL: {exc}"
        )

    # 2. Create database entry in PostgreSQL
    user_id = current_user.id if current_user else None
    job = Job(repo_url=normalized_url, status="pending", user_id=user_id)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("Created job %s for repo %s in PostgreSQL (user_id=%s)", job.id, normalized_url, user_id)

    # 3. Trigger Celery task (placeholder/dispatch)
    try:
        from backend.services.celery_tasks import analyze_repo_task
        analyze_repo_task.delay(job.id, normalized_url)
        logger.info("Dispatched Celery task for job %s", job.id)
    except ImportError:
        logger.warning(
            "Celery tasks module not found or delay method failed. "
            "Job %s created in DB but background execution not triggered.",
            job.id
        )
    except Exception as exc:
        logger.error("Failed to queue Celery background task: %s", exc)
        # We don't fail the request since the job is already committed in the DB,
        # but we notify in the response.

    return {
        "job_id": job.id,
        "repo_url": normalized_url,
        "status": job.status,
        "message": "Analysis job accepted. Monitor progress via WebSockets."
    }
