"""AST-based code metrics and complexity analysis agent.

Walks Python ASTs to compute per-file metrics (LOC, function/class counts,
cyclomatic complexity), clusters files into complexity tiers using K-Means,
and exposes a LangGraph-compatible node function.
"""
from __future__ import annotations

import ast
import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("devmind.analytics_agent")


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------

class ComplexityVisitor(ast.NodeVisitor):
    """Walk an AST and accumulate complexity indicators."""

    def __init__(self) -> None:
        self.functions: int = 0
        self.classes: int = 0
        self.complexity: int = 1  # baseline path

    # --- countable constructs ------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions += 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions += 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes += 1
        self.generic_visit(node)

    # --- branching / decision nodes ------------------------------------------

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each And/Or adds one decision point per extra operand
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------

def analyze_file(file_path: str, content: str) -> dict[str, Any]:
    """Analyse a single file and return metric dict.

    For non-Python or syntactically invalid files the function still returns
    basic LOC-only metrics rather than raising.
    """
    loc = len(content.splitlines())

    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError:
        logger.debug("SyntaxError parsing %s — returning LOC-only metrics", file_path)
        return {
            "file_path": file_path,
            "loc": loc,
            "functions": 0,
            "classes": 0,
            "cyclomatic_complexity": 0,
            "is_python": False,
        }

    visitor = ComplexityVisitor()
    visitor.visit(tree)

    return {
        "file_path": file_path,
        "loc": loc,
        "functions": visitor.functions,
        "classes": visitor.classes,
        "cyclomatic_complexity": visitor.complexity,
        "is_python": True,
    }


# ---------------------------------------------------------------------------
# Repository-level aggregation & clustering
# ---------------------------------------------------------------------------

_TIER_NAMES = ("simple", "medium", "complex")


def _classify_tiers(
    df: pd.DataFrame,
    features: list[str],
) -> pd.DataFrame:
    """Cluster files into complexity tiers using K-Means."""
    n_clusters = min(3, len(df))
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df[features].values.astype(np.float64))

    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(scaled)

    # Map cluster IDs → tier names by ascending centroid complexity
    centroid_complexity = km.cluster_centers_[:, features.index("cyclomatic_complexity")]
    ordered_ids = np.argsort(centroid_complexity)
    label_map: dict[int, str] = {}
    for rank, cluster_id in enumerate(ordered_ids):
        label_map[int(cluster_id)] = _TIER_NAMES[min(rank, len(_TIER_NAMES) - 1)]

    df = df.copy()
    df["tier"] = [label_map[int(l)] for l in labels]
    return df


def compute_repository_metrics(files: list[dict[str, str]]) -> dict[str, Any]:
    """Compute aggregate metrics for a repository's files.

    Parameters
    ----------
    files:
        List of ``{"path": str, "content": str}`` dicts as returned by the
        GitHub fetch service.

    Returns
    -------
    dict
        Structured result with per-file metrics, summary stats, top complex
        files, and a tech-debt score.
    """
    python_files = [f for f in files if f.get("path", "").endswith(".py")]

    if not python_files:
        logger.info("No Python files found in repository")
        return {
            "file_metrics": [],
            "summary": {
                "total_files": len(files),
                "total_python_files": 0,
                "total_loc": 0,
                "avg_complexity": 0.0,
                "complexity_distribution": {"simple": 0, "medium": 0, "complex": 0},
            },
            "top_complex_files": [],
            "tech_debt_score": 0.0,
        }

    # Analyse every Python file
    metrics = [analyze_file(f["path"], f["content"]) for f in python_files]
    df = pd.DataFrame(metrics)

    feature_cols = ["loc", "functions", "classes", "cyclomatic_complexity"]

    if len(df) >= 2:
        df = _classify_tiers(df, feature_cols)
    else:
        # Single file — default to "simple"
        df["tier"] = "simple"

    # Summary statistics
    total_loc = int(df["loc"].sum())
    avg_complexity = float(df["cyclomatic_complexity"].mean())
    tier_counts = df["tier"].value_counts().to_dict()
    complexity_distribution = {t: tier_counts.get(t, 0) for t in _TIER_NAMES}

    # Top 5 most complex files
    top_complex = (
        df.nlargest(5, "cyclomatic_complexity")
        .to_dict(orient="records")
    )

    # Tech-debt score (0–100): penalise high average complexity & outlier ratio
    outlier_ratio = complexity_distribution.get("complex", 0) / len(df)
    raw_score = min(avg_complexity * 3.0 + outlier_ratio * 50.0, 100.0)
    tech_debt_score = round(raw_score, 2)

    logger.info(
        "Repository analysis complete — %d Python files, avg complexity %.1f, debt score %.1f",
        len(df),
        avg_complexity,
        tech_debt_score,
    )

    return {
        "file_metrics": df.to_dict(orient="records"),
        "summary": {
            "total_files": len(files),
            "total_python_files": len(df),
            "total_loc": total_loc,
            "avg_complexity": round(avg_complexity, 2),
            "complexity_distribution": complexity_distribution,
        },
        "top_complex_files": top_complex,
        "tech_debt_score": tech_debt_score,
    }


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def run_analytics_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — compute repository-level code analytics."""
    files: list[dict[str, str]] = state.get("files", [])
    logger.info("Analytics agent received %d files", len(files))
    result = compute_repository_metrics(files)
    return {"analytics_output": result}
