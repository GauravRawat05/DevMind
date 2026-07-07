"""FastAPI router for retrieving repository analysis results and interactive Q&A."""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.pg_models import Job
from backend.models.mongo_models import get_qa_history, save_qa_record

logger = logging.getLogger("devmind.api.results")

router = APIRouter(prefix="/api", tags=["results"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AnalysisResults(BaseModel):
    """Container for the structured outputs of each agent."""

    doc: str | None = None
    review: list[dict[str, Any]] | None = None
    analytics: dict[str, Any] | None = None


class JobResultsResponse(BaseModel):
    """Response schema returned when fetching analysis job details."""

    job_id: str
    repo_url: str
    status: str
    created_at: str
    updated_at: str
    results: AnalysisResults


class QAPairResponse(BaseModel):
    """Single question-answer pair returned by the Q&A endpoints."""

    question: str
    answer: str
    timestamp: str | None = None


class SubmitQARequest(BaseModel):
    """Request schema for submitting a new Q&A question."""

    question: str = Field(
        ...,
        min_length=3,
        description="A natural-language question about the analysed codebase",
        examples=["What is the main purpose of this project?"],
    )


# ---------------------------------------------------------------------------
# GET /api/results/{job_id}
# ---------------------------------------------------------------------------


@router.get(
    "/results/{job_id}",
    response_model=JobResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve results and status for a specific analysis job"
)
async def get_job_results(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Retrieves the analysis status and completed outputs for a given job ID.

    Returns the current state and intermediate or final results.
    """
    logger.info("Fetching job results for job_id: %s", job_id)

    # 1. Fetch the job from PostgreSQL
    job = await db.get(Job, job_id)
    if not job:
        logger.warning("Job %s not found in PostgreSQL database", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID {job_id} not found."
        )

    # 2. Map database fields to the response structure
    return {
        "job_id": job.id,
        "repo_url": job.repo_url,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "results": {
            "doc": job.doc_output,
            "review": job.review_output,
            "analytics": job.analytics_output
        }
    }


# ---------------------------------------------------------------------------
# GET /api/results/{job_id}/qa  — retrieve Q&A history
# ---------------------------------------------------------------------------


@router.get(
    "/results/{job_id}/qa",
    response_model=list[QAPairResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve the Q&A conversation history for a job"
)
async def get_job_qa_history(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all question-answer pairs stored in MongoDB for *job_id*."""
    # Verify the job exists
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID {job_id} not found.",
        )

    records = await get_qa_history(job_id)
    return [
        {
            "question": r["question"],
            "answer": r["answer"],
            "timestamp": r.get("timestamp", "").isoformat()
                if hasattr(r.get("timestamp", ""), "isoformat")
                else str(r.get("timestamp", "")),
        }
        for r in records
    ]


# ---------------------------------------------------------------------------
# POST /api/results/{job_id}/qa  — submit a new interactive question
# ---------------------------------------------------------------------------


@router.post(
    "/results/{job_id}/qa",
    response_model=QAPairResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a new question about the analysed codebase"
)
async def submit_qa_question(
    job_id: str,
    body: SubmitQARequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run the RAG Q&A Agent against the job's ChromaDB collection and persist the result."""
    # Verify the job exists and has been completed
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID {job_id} not found.",
        )
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is not yet completed (status={job.status}). "
                   "Q&A is only available after analysis finishes.",
        )

    collection_name = f"job_{job_id.replace('-', '_')}"

    # Execute the QA agent synchronously (lightweight — single LLM call)
    from backend.agents.qa_agent import run_qa_agent

    qa_state: dict[str, Any] = {
        "query": body.question,
        "collection_name": collection_name,
    }
    result = run_qa_agent(qa_state)
    answer = result.get("qa_output", "Unable to generate an answer.")

    # Persist to MongoDB
    try:
        saved = await save_qa_record(job_id, body.question, answer)
        timestamp = str(saved.get("timestamp", ""))
    except Exception as exc:
        logger.warning("Failed to persist Q&A record to MongoDB: %s", exc)
        timestamp = ""

    return {
        "question": body.question,
        "answer": answer,
        "timestamp": timestamp,
    }
