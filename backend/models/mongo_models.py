"""MongoDB models and helper functions for DevMind Q&A history and detailed agent run logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.core.database import mongo_db


class QARecord(BaseModel):
    """Pydantic model representing a single Q&A query and answer."""

    job_id: str
    question: str
    answer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentRunLog(BaseModel):
    """Pydantic model representing an execution log message from an agent."""

    job_id: str
    agent_name: str
    log_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# MongoDB Helper operations
# ---------------------------------------------------------------------------

async def save_qa_record(job_id: str, question: str, answer: str) -> dict[str, Any]:
    """Insert a Q&A conversation record into the `qa_history` collection.

    Args:
        job_id: The ID of the repository analysis job.
        question: The user's question about the codebase.
        answer: The Q&A agent's generated answer.

    Returns:
        The inserted document dict (with `_id` converted to string).
    """
    try:
        record = QARecord(job_id=job_id, question=question, answer=answer)
        doc = record.model_dump()
        result = await mongo_db.qa_history.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc
    except Exception as e:
        import logging
        logging.getLogger("devmind.mongo").warning("Failed to save Q&A record to MongoDB: %s", e)
        return {"job_id": job_id, "question": question, "answer": answer, "timestamp": datetime.utcnow()}


async def get_qa_history(job_id: str) -> list[dict[str, Any]]:
    """Retrieve all Q&A conversation records for a given job, ordered by time.

    Args:
        job_id: The ID of the repository analysis job.

    Returns:
        A list of Q&A record dicts.
    """
    try:
        cursor = mongo_db.qa_history.find({"job_id": job_id}).sort("timestamp", 1)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        import logging
        logging.getLogger("devmind.mongo").warning("Failed to get Q&A history from MongoDB: %s", e)
        return []


async def save_agent_log(job_id: str, agent_name: str, log_message: str) -> dict[str, Any]:
    """Insert a detailed execution log entry for an agent into `agent_logs`.

    Args:
        job_id: The ID of the repository analysis job.
        agent_name: The name of the agent (e.g. 'doc_agent', 'review_agent').
        log_message: The detail or intermediate status message.

    Returns:
        The inserted document dict (with `_id` converted to string).
    """
    try:
        log = AgentRunLog(job_id=job_id, agent_name=agent_name, log_message=log_message)
        doc = log.model_dump()
        result = await mongo_db.agent_logs.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc
    except Exception as e:
        import logging
        logging.getLogger("devmind.mongo").warning("Failed to save agent log to MongoDB: %s", e)
        return {"job_id": job_id, "agent_name": agent_name, "log_message": log_message, "timestamp": datetime.utcnow()}


async def get_agent_logs(job_id: str) -> list[dict[str, Any]]:
    """Retrieve all detailed execution log entries for a job, ordered by time.

    Args:
        job_id: The ID of the repository analysis job.

    Returns:
        A list of log dicts.
    """
    try:
        cursor = mongo_db.agent_logs.find({"job_id": job_id}).sort("timestamp", 1)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        import logging
        logging.getLogger("devmind.mongo").warning("Failed to get agent logs from MongoDB: %s", e)
        return []
