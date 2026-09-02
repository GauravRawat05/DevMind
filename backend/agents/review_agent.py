"""Code review agent using LangChain + Groq.

Sends selected source files to the Groq LLM with instructions to identify
security vulnerabilities, missing error handling, code smells, naming issues,
and potential bugs.  Returns a structured list of issues.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.core.config import settings

logger = logging.getLogger("devmind.review_agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_FILES = 5
_MAX_CONTENT_CHARS = 1200

_SYSTEM_PROMPT = """\
You are an expert automated code reviewer. You will receive source code from a repository.
Analyze every file and report security vulnerabilities, missing error handling, code smells, and potential bugs.

CRITICAL INSTRUCTION:
Your entire response must be ONLY a valid JSON array. Do not include any text, reasoning, thoughts, or markdown formatting before or after the JSON.

JSON Schema:
[
  {
    "file": "path/to/file.py",
    "line": 12,
    "severity": "critical",
    "message": "Brief description of the issue",
    "suggestion": "Actionable fix recommendation"
  }
]

Allowed severity values: "critical", "warning", "info".
If you find no issues, return an empty array: []
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm() -> ChatGroq:
    """Return a configured ChatGroq instance."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.0,
        max_tokens=2048,
    )


def _prepare_code_for_review(
    files: list[dict[str, str]],
    max_files: int = _MAX_FILES,
) -> str:
    """Select the most relevant files and format them for the prompt.

    Python files are prioritised.  Content is truncated per file to stay
    within token limits.
    """
    # Prioritise Python files, then sort by path for determinism
    sorted_files = sorted(
        files,
        key=lambda f: (
            0 if f.get("path", "").endswith(".py") and "test" not in f.get("path", "").lower() else 1,
            f.get("path", "")
        ),
    )
    selected = sorted_files[:max_files]

    parts: list[str] = []
    total_chars = 0
    for f in selected:
        if total_chars > 8000:
            parts.append("\n... (remaining files skipped for review token budget)")
            break
        path = f.get("path", "unknown")
        content = f.get("content", "")
        if len(content) > _MAX_CONTENT_CHARS:
            content = content[:_MAX_CONTENT_CHARS] + f"\n... (truncated, {len(f.get('content', ''))} chars total)"
        
        file_block = f"### FILE: {path}\n```\n{content}\n```"
        parts.append(file_block)
        total_chars += len(file_block)

    return "\n\n".join(parts)


def _clean_and_repair_json(text: str) -> str:
    """Remove comments, markdown wrappers, and trailing commas from JSON string."""
    # Strip markdown code blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1)
    
    text = text.strip()
    # Strip single line comments
    text = re.sub(r"//.*?\n", "\n", text)
    # Strip multi line comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Strip trailing commas
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text.strip()


def _normalize_issue(item: Any) -> dict[str, Any] | None:
    """Validate and sanitize a single review issue dict."""
    if not isinstance(item, dict):
        return None
    severity = str(item.get("severity", "info")).lower()
    if severity not in ("critical", "warning", "info"):
        severity = "info"
    return {
        "file": str(item.get("file", "N/A")),
        "line": item.get("line"),
        "severity": severity,
        "message": str(item.get("message", "Potential issue identified")),
        "suggestion": str(item.get("suggestion", "")),
    }


def _parse_review_response(raw: str) -> list[dict[str, Any]]:
    """Extract and validate a JSON array of issues from the LLM response."""
    raw_cleaned = _clean_and_repair_json(raw)

    # 1. Try parsing directly or from outer brackets
    for candidate in [raw_cleaned, raw.strip()]:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                valid = [_normalize_issue(x) for x in parsed if _normalize_issue(x) is not None]
                return valid
            if isinstance(parsed, dict):
                # If wrapped in {"issues": [...]} or similar
                for val in parsed.values():
                    if isinstance(val, list):
                        valid = [_normalize_issue(x) for x in val if _normalize_issue(x) is not None]
                        return valid
        except Exception:
            pass

    # 2. Extract outermost [...] block
    bracket_match = re.search(r"\[.*\]", raw_cleaned, re.DOTALL)
    if bracket_match:
        try:
            parsed = json.loads(bracket_match.group(0))
            if isinstance(parsed, list):
                valid = [_normalize_issue(x) for x in parsed if _normalize_issue(x) is not None]
                return valid
        except Exception:
            pass

    # 3. Fallback: extract individual JSON objects {...}
    obj_matches = re.finditer(r"\{[^{}]*\}", raw_cleaned)
    fallback_items: list[dict[str, Any]] = []
    for m in obj_matches:
        try:
            item = json.loads(m.group(0))
            normalized = _normalize_issue(item)
            if normalized and ("message" in item or "file" in item):
                fallback_items.append(normalized)
        except Exception:
            continue

    if fallback_items:
        return fallback_items

    logger.warning("Failed to parse review JSON — returning raw text as single issue")
    return [
        {
            "file": "N/A",
            "line": None,
            "severity": "info",
            "message": "Review output could not be parsed as structured JSON.",
            "suggestion": raw.strip()[:500],
        }
    ]


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def run_review_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — perform code review on repository files."""
    files: list[dict[str, str]] = state.get("files", [])
    logger.info("Review agent received %d files", len(files))

    if not files:
        logger.warning("No files provided for review")
        return {"review_output": []}

    code_block = _prepare_code_for_review(files)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "Review the following code:\n\n{code}\n\nReturn your findings as a JSON array."),
    ])

    chain = prompt | _get_llm() | StrOutputParser()

    # Retry with exponential backoff for Groq rate-limit (429) errors.
    # The free tier allows only 6000 TPM and all 4 agents fire concurrently.
    max_retries = 4
    raw_response = None
    for attempt in range(1, max_retries + 1):
        try:
            raw_response = chain.invoke({"code": code_block})
            break  # success
        except Exception as exc:
            is_rate_limit = "rate_limit" in str(exc).lower() or "429" in str(exc)
            if is_rate_limit and attempt < max_retries:
                wait = 10 * attempt  # 10s, 20s, 30s
                logger.warning(
                    "Review agent hit rate limit (attempt %d/%d). "
                    "Retrying in %ds...",
                    attempt, max_retries, wait,
                )
                time.sleep(wait)
            else:
                logger.exception("LLM call failed during code review (attempt %d/%d)", attempt, max_retries)
                return {
                    "review_output": [
                        {
                            "file": "N/A",
                            "line": None,
                            "severity": "info",
                            "message": "Code review failed due to an LLM error.",
                            "suggestion": "Retry the analysis.",
                        }
                    ]
                }

    issues = _parse_review_response(raw_response)
    logger.info("Review agent found %d issues", len(issues))
    return {"review_output": issues}
