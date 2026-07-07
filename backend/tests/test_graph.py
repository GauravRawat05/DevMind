"""Tests for the LangGraph agent graph — structure and compilation."""
from __future__ import annotations

import pytest
from backend.agents.graph import AgentState, build_agent_graph, graph


class TestAgentGraph:
    """Verify the LangGraph orchestrator compiles and has the right structure."""

    def test_graph_compiles(self) -> None:
        """The module-level graph should be a compiled LangGraph instance."""
        assert graph is not None

    def test_build_returns_compiled_graph(self) -> None:
        """build_agent_graph should return a compiled graph."""
        g = build_agent_graph()
        assert g is not None

    def test_agent_state_has_required_fields(self) -> None:
        """AgentState TypedDict should have the expected keys."""
        expected_fields = {
            "files", "query", "collection_name",
            "doc_output", "review_output", "qa_output", "analytics_output",
        }
        assert expected_fields.issubset(AgentState.__annotations__.keys())
