"""LangGraph state-machine orchestrator for the DevMind agent pipeline.

Defines the shared ``AgentState``, wires the four agent nodes into a
fan-out / fan-in graph, and exposes the compiled graph at module level.
"""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.agents.analytics_agent import run_analytics_agent
from backend.agents.doc_agent import run_doc_agent
from backend.agents.qa_agent import run_qa_agent
from backend.agents.review_agent import run_review_agent

logger = logging.getLogger("devmind.graph")


# ---------------------------------------------------------------------------
# Shared state schema
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """State dictionary shared across all agent nodes.

    Fields are typed but optional (``total=False``) so that each node only
    needs to return its own slice of the state.
    """

    files: list[dict[str, str]]
    query: str
    collection_name: str
    doc_output: str
    review_output: list[dict[str, Any]]
    qa_output: str
    analytics_output: dict[str, Any]


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_agent_graph() -> CompiledStateGraph:
    """Construct and compile the LangGraph agent pipeline.

    Topology
    --------
    ::

        START ──┬── doc_agent ──────┬── END
                ├── review_agent ───┤
                ├── qa_agent ───────┤
                └── analytics_agent─┘

    All four agent nodes execute in parallel (fan-out from START) and their
    outputs are merged back into the shared state before reaching END.
    """
    builder: StateGraph = StateGraph(AgentState)

    # Register nodes
    builder.add_node("doc_agent", run_doc_agent)
    builder.add_node("review_agent", run_review_agent)
    builder.add_node("qa_agent", run_qa_agent)
    builder.add_node("analytics_agent", run_analytics_agent)

    # Fan-out: START → every agent
    builder.add_edge(START, "doc_agent")
    builder.add_edge(START, "review_agent")
    builder.add_edge(START, "qa_agent")
    builder.add_edge(START, "analytics_agent")

    # Fan-in: every agent → END
    builder.add_edge("doc_agent", END)
    builder.add_edge("review_agent", END)
    builder.add_edge("qa_agent", END)
    builder.add_edge("analytics_agent", END)

    compiled = builder.compile()
    logger.info("Agent graph compiled successfully")
    return compiled


# Module-level compiled graph instance
graph: CompiledStateGraph = build_agent_graph()
