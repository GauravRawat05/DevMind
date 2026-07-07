"""Tests for the analytics agent — AST parsing, metrics, and clustering."""
from __future__ import annotations

import pytest
from backend.agents.analytics_agent import (
    ComplexityVisitor,
    analyze_file,
    compute_repository_metrics,
    run_analytics_agent,
)


# ---------------------------------------------------------------------------
# Sample Python code fixtures
# ---------------------------------------------------------------------------

SIMPLE_CODE = '''\
"""A simple module."""

def greet(name):
    return f"Hello, {name}!"
'''

COMPLEX_CODE = '''\
"""A complex module."""
import os

class FileProcessor:
    """Processes files with multiple branches."""

    def __init__(self, path):
        self.path = path
        self.results = []

    def process(self, items):
        for item in items:
            if item.startswith("."):
                continue
            try:
                with open(item) as f:
                    data = f.read()
                    if data and len(data) > 0:
                        if "error" in data or "warning" in data:
                            self.results.append({"file": item, "status": "flagged"})
                        else:
                            self.results.append({"file": item, "status": "ok"})
            except FileNotFoundError:
                pass
            except PermissionError:
                pass

    def summary(self):
        return [r for r in self.results if r["status"] == "flagged"]
'''

NON_PYTHON_CODE = "<html><body>Hello</body></html>"


# ---------------------------------------------------------------------------
# ComplexityVisitor tests
# ---------------------------------------------------------------------------

class TestComplexityVisitor:
    def test_simple_function(self) -> None:
        import ast
        tree = ast.parse(SIMPLE_CODE)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        assert visitor.functions == 1
        assert visitor.classes == 0
        assert visitor.complexity >= 1

    def test_complex_code(self) -> None:
        import ast
        tree = ast.parse(COMPLEX_CODE)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        assert visitor.functions >= 3  # __init__, process, summary
        assert visitor.classes == 1
        assert visitor.complexity > 5  # many branches


# ---------------------------------------------------------------------------
# analyze_file tests
# ---------------------------------------------------------------------------

class TestAnalyzeFile:
    def test_valid_python_file(self) -> None:
        result = analyze_file("test.py", SIMPLE_CODE)
        assert result["is_python"] is True
        assert result["file_path"] == "test.py"
        assert result["functions"] == 1
        assert result["loc"] > 0

    def test_complex_python_file(self) -> None:
        result = analyze_file("complex.py", COMPLEX_CODE)
        assert result["is_python"] is True
        assert result["classes"] == 1
        assert result["cyclomatic_complexity"] > 1

    def test_non_python_file(self) -> None:
        result = analyze_file("index.html", NON_PYTHON_CODE)
        assert result["is_python"] is False
        assert result["functions"] == 0
        assert result["classes"] == 0

    def test_empty_file(self) -> None:
        result = analyze_file("empty.py", "")
        assert result["is_python"] is True
        assert result["loc"] == 0


# ---------------------------------------------------------------------------
# compute_repository_metrics tests
# ---------------------------------------------------------------------------

class TestComputeRepositoryMetrics:
    def test_with_python_files(self) -> None:
        files = [
            {"path": "simple.py", "content": SIMPLE_CODE},
            {"path": "complex.py", "content": COMPLEX_CODE},
            {"path": "another.py", "content": "x = 1\ny = 2\n"},
        ]
        result = compute_repository_metrics(files)

        assert "file_metrics" in result
        assert "summary" in result
        assert "top_complex_files" in result
        assert "tech_debt_score" in result

        summary = result["summary"]
        assert summary["total_python_files"] == 3
        assert summary["total_loc"] > 0
        assert "complexity_distribution" in summary

        # All files should have a tier
        for fm in result["file_metrics"]:
            assert fm["tier"] in ("simple", "medium", "complex")

    def test_no_python_files(self) -> None:
        files = [{"path": "index.html", "content": NON_PYTHON_CODE}]
        result = compute_repository_metrics(files)
        assert result["summary"]["total_python_files"] == 0
        assert result["file_metrics"] == []

    def test_empty_file_list(self) -> None:
        result = compute_repository_metrics([])
        assert result["summary"]["total_python_files"] == 0

    def test_single_python_file(self) -> None:
        files = [{"path": "one.py", "content": SIMPLE_CODE}]
        result = compute_repository_metrics(files)
        assert result["summary"]["total_python_files"] == 1
        assert len(result["file_metrics"]) == 1
        # Single file should default to "simple" tier
        assert result["file_metrics"][0]["tier"] == "simple"


# ---------------------------------------------------------------------------
# LangGraph node wrapper test
# ---------------------------------------------------------------------------

class TestRunAnalyticsAgent:
    def test_node_returns_analytics_output(self) -> None:
        state = {
            "files": [
                {"path": "app.py", "content": SIMPLE_CODE},
                {"path": "lib.py", "content": COMPLEX_CODE},
                {"path": "util.py", "content": "def add(a, b):\n    return a + b\n"},
            ]
        }
        result = run_analytics_agent(state)
        assert "analytics_output" in result
        assert result["analytics_output"]["summary"]["total_python_files"] == 3
