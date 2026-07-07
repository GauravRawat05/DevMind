"""RAG-powered Q&A agent.

Retrieves relevant code chunks from ChromaDB via the vector store service,
feeds them as context to the Groq LLM, and returns a natural-language answer.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.core.config import settings
from backend.services.vector_store import search

logger = logging.getLogger("devmind.qa_agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOP_K = 5

_SYSTEM_PROMPT = """\
You are a knowledgeable code assistant.  You answer questions about a
software codebase using ONLY the context provided below.  If the context
does not contain enough information to answer, say so honestly rather than
guessing.

When referencing code, include the file path and relevant snippets.
Keep answers concise, accurate, and well-structured in Markdown.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm() -> ChatGroq:
    """Return a configured ChatGroq instance."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=settings.GROQ_API_KEY,
        temperature=0.3,
        max_tokens=2048,
    )


def _format_context(results: list[dict[str, Any]]) -> str:
    """Convert vector store search results into a readable context string."""
    if not results:
        return "No relevant code chunks were found."

    parts: list[str] = []
    for idx, result in enumerate(results, start=1):
        text = result.get("text", "")
        meta = result.get("metadata", {})
        source = meta.get("file_path", "unknown")
        parts.append(f"**Chunk {idx}** — `{source}`\n```\n{text}\n```")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def run_qa_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — answer a user question using RAG over the codebase."""
    query: str = state.get("query", "")
    collection_name: str = state.get("collection_name", "default")

    if not query or not query.strip():
        logger.info("QA agent invoked without a query")
        return {
            "qa_output": "No question provided. Submit a query to ask about the codebase."
        }

    logger.info(
        "QA agent answering query '%s' against collection '%s'",
        query[:80],
        collection_name,
    )

    # Retrieve relevant chunks from ChromaDB
    try:
        results = search(collection_name, query, n_results=_TOP_K)
    except Exception:
        logger.exception("Vector store search failed")
        return {"qa_output": "An error occurred while searching the code index. Please retry."}

    context = _format_context(results)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:",
        ),
    ])

    chain = prompt | _get_llm() | StrOutputParser()

    try:
        answer = chain.invoke({"context": context, "question": query})
    except Exception:
        logger.exception("LLM call failed during Q&A")
        answer = "Sorry, I was unable to generate an answer. Please try again."

    logger.info("QA agent produced answer of %d characters", len(answer))
    return {"qa_output": answer}
