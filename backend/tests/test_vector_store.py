"""Tests for the vector store — chunking and ChromaDB operations."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest
from backend.services.vector_store import chunk_code_files


# ---------------------------------------------------------------------------
# chunk_code_files tests (no ChromaDB/embeddings required)
# ---------------------------------------------------------------------------

class TestChunkCodeFiles:
    """Tests for the code chunking logic — pure unit tests."""

    def test_basic_chunking(self) -> None:
        files = [{"path": "main.py", "content": "a" * 2500}]
        chunks = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        # 2500 chars / (1000-200) step = 4 chunks (0-1000, 800-1800, 1600-2500, 2400-2500)
        assert len(chunks) >= 3

    def test_chunk_structure(self) -> None:
        files = [{"path": "app.py", "content": "x = 1\ny = 2\n"}]
        chunks = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert "id" in chunk
        assert "text" in chunk
        assert "metadata" in chunk
        assert chunk["metadata"]["file_path"] == "app.py"
        assert chunk["metadata"]["chunk_index"] == 0

    def test_empty_files_skipped(self) -> None:
        files = [
            {"path": "empty.py", "content": ""},
            {"path": "whitespace.py", "content": "   \n\n  "},
        ]
        chunks = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 0

    def test_multiple_files(self) -> None:
        files = [
            {"path": "a.py", "content": "print('a')\n"},
            {"path": "b.py", "content": "print('b')\n"},
            {"path": "c.py", "content": "print('c')\n"},
        ]
        chunks = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 3
        file_paths = {c["metadata"]["file_path"] for c in chunks}
        assert file_paths == {"a.py", "b.py", "c.py"}

    def test_deterministic_ids(self) -> None:
        """Same input should produce the same chunk IDs."""
        files = [{"path": "stable.py", "content": "data = True\n"}]
        chunks_a = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        chunks_b = chunk_code_files(files, chunk_size=1000, chunk_overlap=200)
        assert chunks_a[0]["id"] == chunks_b[0]["id"]

    def test_overlap_logic(self) -> None:
        """Chunks should overlap by the specified amount."""
        content = "0123456789" * 30  # 300 chars
        files = [{"path": "data.py", "content": content}]
        chunks = chunk_code_files(files, chunk_size=100, chunk_overlap=20)
        # Step = 80, so chunks start at 0, 80, 160, 240
        assert len(chunks) >= 4
        # Check overlap: end of chunk 0 overlaps with start of chunk 1
        assert chunks[0]["text"][-20:] == chunks[1]["text"][:20]
