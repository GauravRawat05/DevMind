"""Documentation generation agent using LangChain + Groq.

Summarises repository files and calls the Groq LLM to produce a
comprehensive README.md for the codebase.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.core.config import settings

logger = logging.getLogger("devmind.doc_agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_LINES_PER_FILE = 25
_SYSTEM_PROMPT = """\
You are an expert technical writer specialising in software documentation.
You will receive a condensed summary of every file in a code repository.

Your task is to generate a comprehensive, well-structured **README.md** that
includes the following sections:

1. **Project Title & Description** — a concise overview of the project's
   purpose, value proposition, and target users.
2. **Features** — a bullet-point list of the major capabilities.
3. **Architecture Overview** — a brief description of the tech stack, folder
   structure, and how the main components interact.
4. **Getting Started** — installation prerequisites, environment setup,
   dependency installation, and first-run instructions.
5. **Configuration** — environment variables and configuration files that
   must be provided.
6. **Usage** — common CLI commands, API endpoints, or usage patterns.
7. **Project Structure** — a concise tree or table showing key directories
   and files with one-line descriptions.
8. **Contributing** — guidelines for contributors (branching model, PR
   process, coding standards).
9. **License** — a placeholder for the project's licence.

Write in clear, professional Markdown.  Use code fences, tables, and badges
where appropriate.  Do NOT invent features that are not evident from the
source files — base every claim on the provided code summaries.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm() -> ChatGroq:
    """Return a configured ChatGroq instance."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.3,
        max_tokens=2048,
    )


def _summarize_files(files: list[dict[str, str]]) -> str:
    """Create a condensed textual summary of repository files.

    Each file is represented by its path and the first *_MAX_LINES_PER_FILE*
    lines of content.  This keeps the prompt within token limits even for
    large repositories.
    """
    # Prioritise non-test Python files, then sort for determinism
    sorted_files = sorted(
        files,
        key=lambda f: (
            0 if f.get("path", "").endswith(".py") and "test" not in f.get("path", "").lower() else 1,
            f.get("path", "")
        )
    )

    parts: list[str] = []
    total_chars = 0
    for f in sorted_files:
        if total_chars > 6000:
            parts.append(f"\n... (remaining {len(sorted_files) - len(parts)} files skipped for token budget)")
            break
        path = f.get("path", "unknown")
        content = f.get("content", "")
        lines = content.splitlines()
        truncated = "\n".join(lines[:_MAX_LINES_PER_FILE])
        if len(lines) > _MAX_LINES_PER_FILE:
            truncated += f"\n... ({len(lines) - _MAX_LINES_PER_FILE} more lines)"
        
        file_summary = f"### FILE: {path}\n```\n{truncated}\n```"
        parts.append(file_summary)
        total_chars += len(file_summary)

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def run_doc_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — generate README documentation for the repository."""
    files: list[dict[str, str]] = state.get("files", [])
    logger.info("Doc agent received %d files for documentation generation", len(files))

    if not files:
        logger.warning("No files provided — returning placeholder README")
        return {"doc_output": "# Project\n\nNo source files were provided for documentation generation.\n"}

    summary = _summarize_files(files)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "Here are the repository files:\n\n{file_summary}\n\nGenerate the README.md now."),
    ])

    chain = prompt | _get_llm() | StrOutputParser()

    # Retry with exponential backoff for Groq rate-limit (429) errors.
    max_retries = 4
    readme = None
    for attempt in range(1, max_retries + 1):
        try:
            readme = chain.invoke({"file_summary": summary})
            break  # success
        except Exception as exc:
            is_rate_limit = "rate_limit" in str(exc).lower() or "429" in str(exc)
            if is_rate_limit and attempt < max_retries:
                wait = 10 * attempt  # 10s, 20s, 30s
                logger.warning(
                    "Doc agent hit rate limit (attempt %d/%d). Retrying in %ds...",
                    attempt, max_retries, wait,
                )
                time.sleep(wait)
            else:
                logger.exception("LLM call failed during documentation generation (attempt %d/%d)", attempt, max_retries)
                readme = "# Project\n\n_Documentation generation failed. Please retry._\n"
                break

    logger.info("Doc agent produced README of %d characters", len(readme))
    return {"doc_output": readme}
