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
You are an expert code reviewer.  You will receive source code from a
repository.  Analyse every file and report issues you find.

Look for:
- **Security vulnerabilities** (injection, hardcoded secrets, insecure
  defaults, missing input validation)
- **Missing error handling** (bare excepts, swallowed exceptions, missing
  null checks)
- **Code smells** (duplicated logic, god classes, excessive nesting,
  functions that are too long)
- **Naming conventions** (inconsistent style, single-letter variables in
  non-trivial scopes, misleading names)
- **Potential bugs** (off-by-one errors, race conditions, incorrect type
  usage, mutable default arguments)

Respond ONLY with a JSON array.  Each element must have exactly these keys:

```json
[
  {{
    "file": "<file path>",
    "line": <line number or null>,
    "severity": "critical" | "warning" | "info",
    "message": "<short description of the issue>",
    "suggestion": "<actionable fix recommendation>"
  }}
]
```

If you find no issues, return an empty array: `[]`.
Do NOT include any text outside the JSON array.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm() -> ChatGroq:
    """Return a configured ChatGroq instance."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
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


def _parse_review_response(raw: str) -> list[dict[str, Any]]:
    """Extract a JSON array from the LLM response.

    Handles cases where the model wraps the JSON in markdown code fences
    or includes explanatory text.
    """
    # Try direct parse first
    raw_stripped = raw.strip()
    try:
        parsed = json.loads(raw_stripped)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try extracting from a fenced code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw_stripped, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Last resort: look for the outermost [ … ]
    bracket_match = re.search(r"\[.*]", raw_stripped, re.DOTALL)
    if bracket_match:
        try:
            parsed = json.loads(bracket_match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse review JSON — returning raw text as single issue")
    return [
        {
            "file": "N/A",
            "line": None,
            "severity": "info",
            "message": "Review output could not be parsed as structured JSON.",
            "suggestion": raw_stripped[:500],
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
