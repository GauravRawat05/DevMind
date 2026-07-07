"""ChromaDB vector store for RAG semantic search.

Provides persistent vector storage and retrieval using ChromaDB, backed by
the local :mod:`backend.services.embedding_service` for dense embeddings.
Code files are chunked with configurable overlap before being indexed,
enabling fine-grained semantic search across an entire repository.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import chromadb
from chromadb import EmbeddingFunction

from backend.core.config import settings
from backend.services.embedding_service import embedding_service

logger = logging.getLogger("devmind.vector_store")


# ---------------------------------------------------------------------------
# Embedding adapter
# ---------------------------------------------------------------------------

class ChromaEmbeddingFunction(EmbeddingFunction[list[str]]):
    """Adapter that bridges :class:`EmbeddingService` to ChromaDB's
    :class:`EmbeddingFunction` interface.

    ChromaDB expects an ``__call__`` method that accepts a list of strings
    and returns a list of float-lists.  This class simply delegates to the
    application-level :data:`embedding_service` singleton.
    """

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Embed a list of texts using the DevMind embedding service.

        Args:
            input: Texts to embed.

        Returns:
            A list of embedding vectors.
        """
        return embedding_service.embed_documents(input)


# Module-level embedding function instance
_embedding_fn = ChromaEmbeddingFunction()


# ---------------------------------------------------------------------------
# ChromaDB client (lazy singleton)
# ---------------------------------------------------------------------------

_chroma_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    """Return (and cache) a persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        logger.info("Initialising ChromaDB PersistentClient at %s", settings.CHROMADB_PATH)
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
    return _chroma_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_collection(collection_name: str) -> chromadb.Collection:
    """Return a ChromaDB collection, creating it if it does not exist.

    The collection is configured with the application's local embedding
    function so that documents and queries are embedded transparently.

    Args:
        collection_name: The name of the collection.

    Returns:
        A :class:`chromadb.Collection` instance.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=_embedding_fn,
    )
    logger.info(
        "Collection '%s' ready (%d existing documents)",
        collection_name,
        collection.count(),
    )
    return collection


def chunk_code_files(
    files: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """Split source files into overlapping text chunks.

    Each file's content is divided into chunks of *chunk_size* characters
    with *chunk_overlap* characters of overlap between consecutive chunks.
    A deterministic, content-based ID is generated for each chunk so that
    re-indexing the same file produces stable identifiers.

    Args:
        files: A list of dicts with ``path`` and ``content`` keys, as
               returned by :func:`backend.services.github_service.fetch_repository`.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive
                       chunks in the same file.

    Returns:
        A list of dicts, each containing:
        - ``id``: A unique, deterministic chunk identifier.
        - ``text``: The chunk text.
        - ``metadata``: A dict with ``file_path`` and ``chunk_index``.
    """
    chunks: list[dict] = []

    for file_entry in files:
        file_path: str = file_entry["path"]
        content: str = file_entry["content"]

        if not content.strip():
            continue

        step = max(chunk_size - chunk_overlap, 1)
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + chunk_size
            chunk_text = content[start:end]

            # Deterministic ID from file path + chunk index
            raw_id = f"{file_path}::chunk_{chunk_index}"
            chunk_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "file_path": file_path,
                        "chunk_index": chunk_index,
                    },
                }
            )

            chunk_index += 1
            start += step

    logger.info(
        "Chunked %d files into %d text chunks (size=%d, overlap=%d)",
        len(files),
        len(chunks),
        chunk_size,
        chunk_overlap,
    )
    return chunks


def index_repository(collection_name: str, files: list[dict]) -> int:
    """Chunk, embed, and store repository files in ChromaDB.

    This is the primary indexing entry-point.  It chunks the provided
    source files, then upserts them into the named ChromaDB collection in
    batches of 500 to stay within ChromaDB's per-call limits.

    Args:
        collection_name: Target collection name.
        files: Source file dicts (``path``, ``content``).

    Returns:
        The total number of chunks that were indexed.
    """
    chunks = chunk_code_files(files)

    if not chunks:
        logger.warning("No chunks produced — nothing to index.")
        return 0

    collection = get_or_create_collection(collection_name)

    batch_size = 500
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )
        logger.debug(
            "Upserted batch %d–%d (%d chunks)",
            i,
            i + len(batch) - 1,
            len(batch),
        )

    logger.info(
        "Indexed %d chunks into collection '%s'",
        len(chunks),
        collection_name,
    )
    return len(chunks)


def search(
    collection_name: str,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Perform semantic search against a ChromaDB collection.

    Args:
        collection_name: The collection to search.
        query: Natural-language query string.
        n_results: Maximum number of results to return.

    Returns:
        A list of result dicts, each containing ``text``, ``metadata``,
        and ``distance`` (lower is more similar).
    """
    collection = get_or_create_collection(collection_name)

    results: dict[str, Any] = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    output: list[dict] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for text, metadata, distance in zip(documents, metadatas, distances):
        output.append(
            {
                "text": text,
                "metadata": metadata,
                "distance": distance,
            }
        )

    logger.info(
        "Search in '%s' for '%.60s...' returned %d results",
        collection_name,
        query,
        len(output),
    )
    return output
