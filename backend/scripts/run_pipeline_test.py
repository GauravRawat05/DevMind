"""Full pipeline integration test for DevMind Phase 2.

Usage:
    python -m backend.scripts.run_pipeline_test [--repo URL] [--query QUESTION]

This script runs the complete agent pipeline against a real (or default)
GitHub repository:
1. Fetches repository files via the GitHub service
2. Indexes them in ChromaDB via the vector store
3. Runs the LangGraph agent graph (all 4 agents in parallel)
4. Prints the results from each agent
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("devmind.pipeline_test")

# Default small public repo for testing
DEFAULT_REPO_URL = "https://github.com/tiangolo/fastapi"
DEFAULT_QUERY = "What is the main purpose of this project?"


def _separator(title: str) -> str:
    """Return a formatted section separator."""
    return f"\n{'=' * 70}\n  {title}\n{'=' * 70}"


async def main(repo_url: str, query: str) -> None:
    """Run the full DevMind analysis pipeline."""
    from backend.services.github_service import fetch_repository
    from backend.services.vector_store import index_repository
    from backend.agents.graph import graph

    overall_start = time.perf_counter()

    # ── Step 1: Fetch repository ──────────────────────────────────────────
    print(_separator("Step 1: Fetching Repository"))
    t0 = time.perf_counter()
    try:
        files = await fetch_repository(repo_url)
    except Exception as exc:
        logger.error("Failed to fetch repository: %s", exc)
        sys.exit(1)
    t1 = time.perf_counter()
    print(f"  [OK] Fetched {len(files)} files in {t1 - t0:.1f}s")
    for f in files[:10]:
        print(f"    - {f['path']}  ({len(f['content'])} chars)")
    if len(files) > 10:
        print(f"    ... and {len(files) - 10} more files")

    # ── Step 2: Index in ChromaDB ─────────────────────────────────────────
    print(_separator("Step 2: Indexing in ChromaDB"))
    collection_name = "pipeline_test"
    t0 = time.perf_counter()
    chunk_count = index_repository(collection_name, files)
    t1 = time.perf_counter()
    print(f"  [OK] Indexed {chunk_count} chunks in {t1 - t0:.1f}s")

    # ── Step 3: Run LangGraph agent pipeline ──────────────────────────────
    print(_separator("Step 3: Running Agent Pipeline"))
    initial_state = {
        "files": files,
        "query": query,
        "collection_name": collection_name,
    }

    t0 = time.perf_counter()
    try:
        result = graph.invoke(initial_state)
    except Exception as exc:
        logger.error("Agent pipeline failed: %s", exc)
        sys.exit(1)
    t1 = time.perf_counter()
    print(f"  [OK] Pipeline completed in {t1 - t0:.1f}s")

    # ── Step 4: Display results ───────────────────────────────────────────
    # Doc Agent output
    print(_separator("Doc Agent Output (README.md)"))
    doc_output = result.get("doc_output", "No output")
    print(doc_output[:2000])
    if len(doc_output) > 2000:
        print(f"\n... (truncated, {len(doc_output)} chars total)")

    # Review Agent output
    print(_separator("Review Agent Output (Code Issues)"))
    review_output = result.get("review_output", [])
    if isinstance(review_output, list):
        print(f"  Found {len(review_output)} issue(s):")
        for issue in review_output[:10]:
            severity = issue.get("severity", "?")
            msg = issue.get("message", "?")
            file = issue.get("file", "?")
            print(f"    [{severity.upper()}] {file}: {msg}")
    else:
        print(f"  Raw output: {review_output}")

    # Q&A Agent output
    print(_separator(f"Q&A Agent Output (Query: {query})"))
    qa_output = result.get("qa_output", "No output")
    print(qa_output[:1500])

    # Analytics Agent output
    print(_separator("Analytics Agent Output (Code Metrics)"))
    analytics_output = result.get("analytics_output", {})
    if isinstance(analytics_output, dict):
        summary = analytics_output.get("summary", {})
        print(f"  Total files analysed: {summary.get('total_files', 0)}")
        print(f"  Python files: {summary.get('total_python_files', 0)}")
        print(f"  Total LOC: {summary.get('total_loc', 0)}")
        print(f"  Avg complexity: {summary.get('avg_complexity', 0)}")
        dist = summary.get("complexity_distribution", {})
        print(f"  Tiers: Simple={dist.get('simple', 0)} | Medium={dist.get('medium', 0)} | Complex={dist.get('complex', 0)}")
        print(f"  Tech debt score: {analytics_output.get('tech_debt_score', 0)}")
        top = analytics_output.get("top_complex_files", [])
        if top:
            print("\n  Top complex files:")
            for f in top[:5]:
                print(f"    - {f.get('file_path', '?')}: complexity={f.get('cyclomatic_complexity', 0)}, tier={f.get('tier', '?')}")
    else:
        print(f"  Raw output: {json.dumps(analytics_output, indent=2)[:1000]}")

    overall_end = time.perf_counter()
    print(_separator("Pipeline Complete"))
    print(f"  Total execution time: {overall_end - overall_start:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevMind Pipeline Integration Test")
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO_URL,
        help=f"GitHub repo URL to analyse (default: {DEFAULT_REPO_URL})",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Question for the Q&A agent (default: '{DEFAULT_QUERY}')",
    )
    args = parser.parse_args()
    asyncio.run(main(args.repo, args.query))
