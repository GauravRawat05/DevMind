"""Local embedding service powered by sentence-transformers.

Provides a lazily-initialised singleton that wraps the ``all-MiniLM-L6-v2``
model for generating dense vector embeddings of code and text, used
throughout the DevMind RAG pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger("devmind.embedding_service")


class EmbeddingService:
    """Thin wrapper around a sentence-transformers model.

    The underlying :class:`SentenceTransformer` is loaded lazily on the
    first call to :meth:`embed_documents` or :meth:`embed_query`, keeping
    import time fast and avoiding unnecessary GPU/CPU allocation when the
    service is not used.
    """

    MODEL_NAME: str = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformers model on first use."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self.MODEL_NAME)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: A list of text strings to embed.

        Returns:
            A list of embedding vectors (each a list of floats).
        """
        model = self._load_model()
        logger.debug("Embedding %d documents", len(texts))
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: The query text to embed.

        Returns:
            The embedding vector as a list of floats.
        """
        model = self._load_model()
        logger.debug("Embedding query: %.80s...", text)
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()


# Module-level singleton — import and reuse throughout the application.
embedding_service = EmbeddingService()
