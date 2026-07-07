"""Celery background tasks for the DevMind analysis pipeline.

Configures the Celery application with the Upstash Redis broker and defines
the ``analyze_repo_task`` that orchestrates the full repository analysis:
fetch → index → LangGraph agents → persist results.

Progress events are published to a Redis Pub/Sub channel so that WebSocket
clients can stream real-time updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone

from celery import Celery

from backend.core.config import settings

logger = logging.getLogger("devmind.celery_tasks")

# ---------------------------------------------------------------------------
# Redis URL conversion for Upstash (requires rediss:// + ssl_cert_reqs)
# ---------------------------------------------------------------------------
redis_url = settings.REDIS_URL
if "upstash.io" in redis_url and redis_url.startswith("redis://"):
    logger.info("Converting Upstash Redis URL scheme to secure 'rediss://' for Celery")
    redis_url = redis_url.replace("redis://", "rediss://", 1)
    if "ssl_cert_reqs" not in redis_url:
        redis_url += "?ssl_cert_reqs=none"

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------
celery_app = Celery(
    "devmind_tasks",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _publish_progress(job_id: str, stage: str, message: str, *, status: str = "in_progress") -> None:
    """Publish a progress event to the Redis Pub/Sub channel for *job_id*.

    This uses a **synchronous** Redis connection (suitable for inside
    Celery workers which run synchronously with ``-P solo``).
    """
    import redis as sync_redis

    channel = f"job_progress:{job_id}"
    payload = json.dumps({
        "job_id": job_id,
        "stage": stage,
        "message": message,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    r_url = settings.REDIS_URL
    if "upstash.io" in r_url and r_url.startswith("redis://"):
        r_url = r_url.replace("redis://", "rediss://", 1)

    redis_kwargs = {"decode_responses": True}
    if r_url.startswith("rediss://"):
        redis_kwargs["ssl_cert_reqs"] = None

    try:
        r = sync_redis.from_url(r_url, **redis_kwargs)
        r.publish(channel, payload)
        r.close()
    except Exception as exc:
        logger.warning("Failed to publish progress for job %s: %s", job_id, exc)


def _run_async(coro):
    """Run an async coroutine from within a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _update_job_status(job_id: str, status: str, **kwargs) -> None:
    """Update the Job row in PostgreSQL with a new status and optional fields."""
    from backend.core.database import AsyncSessionLocal
    from backend.models.pg_models import Job

    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            await session.commit()
            logger.info("Updated job %s status to '%s'", job_id, status)
        else:
            logger.error("Job %s not found in database during status update", job_id)


# ---------------------------------------------------------------------------
# Main Celery task
# ---------------------------------------------------------------------------


@celery_app.task(
    name="backend.services.celery_tasks.analyze_repo_task",
    bind=True,
    max_retries=0,
)
def analyze_repo_task(self, job_id: str, repo_url: str, query: str = "What is the main purpose of this project?") -> None:
    """Run the full DevMind analysis pipeline as a Celery background task.

    Pipeline stages:
        1. Mark job as ``processing``
        2. Download repository files from GitHub
        3. Chunk, embed, and index files into ChromaDB
        4. Run the parallel LangGraph agent pipeline
        5. Persist outputs to PostgreSQL and mark job as ``completed``

    Progress events are published to Redis Pub/Sub at each stage so that
    WebSocket clients can show real-time updates.
    """
    logger.info("Starting analysis pipeline for job=%s, repo=%s", job_id, repo_url)

    try:
        # ---- Stage 1: Mark as processing ----
        _publish_progress(job_id, "init", "Starting analysis pipeline...")
        _run_async(_update_job_status(job_id, "processing"))
        _publish_progress(job_id, "init", "Job status updated to processing")

        # ---- Stage 2: Fetch repository ----
        _publish_progress(job_id, "fetching", f"Downloading repository from {repo_url}...")

        from backend.services.github_service import fetch_repository
        files = _run_async(fetch_repository(repo_url))

        _publish_progress(
            job_id, "fetching",
            f"Repository downloaded successfully. {len(files)} source files extracted."
        )
        logger.info("Fetched %d files for job %s", len(files), job_id)

        # ---- Stage 3: Index into ChromaDB ----
        _publish_progress(job_id, "indexing", "Chunking and embedding source files into vector store...")

        from backend.services.vector_store import index_repository
        collection_name = f"job_{job_id.replace('-', '_')}"
        num_chunks = index_repository(collection_name, files)

        _publish_progress(
            job_id, "indexing",
            f"Indexed {num_chunks} chunks into ChromaDB collection '{collection_name}'."
        )
        logger.info("Indexed %d chunks for job %s", num_chunks, job_id)

        # ---- Stage 4: Run LangGraph agent pipeline ----
        _publish_progress(job_id, "agents", "Running parallel agent pipeline (Doc, Review, Q&A, Analytics)...")

        from backend.agents.graph import graph

        initial_state = {
            "files": files,
            "query": query,
            "collection_name": collection_name,
        }

        result = graph.invoke(initial_state)

        doc_output = result.get("doc_output", "")
        review_output = result.get("review_output", [])
        qa_output = result.get("qa_output", "")
        analytics_output = result.get("analytics_output", {})

        _publish_progress(job_id, "agents", "All agents completed successfully.")
        logger.info("Agent pipeline completed for job %s", job_id)

        # ---- Stage 5: Persist results and mark completed ----
        _publish_progress(job_id, "saving", "Persisting analysis results to database...")

        s3_key = None
        if doc_output:
            try:
                from backend.services.s3_service import storage_service
                s3_key = f"{job_id}/README.md"
                storage_service.upload_file(s3_key, doc_output)
                logger.info("Uploaded generated README to S3 mock under key: %s", s3_key)
            except Exception as s3_exc:
                logger.error("Failed to upload README to mock S3: %s", s3_exc)
                s3_key = None

        _run_async(_update_job_status(
            job_id, "completed",
            doc_output=doc_output,
            s3_doc_key=s3_key,
            review_output=review_output,
            analytics_output=analytics_output,
        ))

        # Save Q&A output to MongoDB if available
        if qa_output:
            try:
                from backend.models.mongo_models import save_qa_record
                _run_async(save_qa_record(job_id, query, qa_output))
                logger.info("Saved Q&A record to MongoDB for job %s", job_id)
            except Exception as mongo_exc:
                logger.warning("Failed to save Q&A record to MongoDB: %s", mongo_exc)

        _publish_progress(
            job_id, "complete",
            "Analysis complete! Results are ready.",
            status="completed",
        )
        logger.info("Analysis pipeline finished successfully for job %s", job_id)

    except Exception as exc:
        error_msg = f"Pipeline failed: {exc}"
        logger.error("Analysis pipeline failed for job %s: %s", job_id, exc)
        logger.debug(traceback.format_exc())

        _publish_progress(job_id, "error", error_msg, status="failed")

        try:
            _run_async(_update_job_status(job_id, "failed"))
        except Exception as db_exc:
            logger.error("Failed to update job %s to 'failed' status: %s", job_id, db_exc)

        raise
