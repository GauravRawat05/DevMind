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
    """Wrapper around a sentence-transformers model.

    Attempts to use the Hugging Face Inference API first to save memory (ideal
    for low-memory hosting platforms like Render's free tier). Falls back to
    loading the model locally using sentence-transformers if the API key is missing
    or the request fails.
    """

    MODEL_NAME: str = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _embed_via_hf_api(self, texts: list[str]) -> list[list[float]] | None:
        """Attempt to generate embeddings via Hugging Face Inference API."""
        import os
        import urllib.request
        import json

        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_key or hf_key.startswith("mock_"):
            return None

        api_url = f"https://api-inference.huggingface.co/models/sentence-transformers/{self.MODEL_NAME}"
        headers = {
            "Authorization": f"Bearer {hf_key}",
            "Content-Type": "application/json",
            "User-Agent": "DevMind/1.0"
        }

        results: list[list[float]] = []
        hf_batch_size = 50  # Smaller sub-batches to prevent API size/rate limit issues

        try:
            for j in range(0, len(texts), hf_batch_size):
                sub_batch = texts[j : j + hf_batch_size]
                payload = {
                    "inputs": sub_batch,
                    "options": {"wait_for_model": True}
                }
                req = urllib.request.Request(
                    api_url,
                    headers=headers,
                    data=json.dumps(payload).encode("utf-8"),
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as res:
                    response_data = json.loads(res.read().decode("utf-8"))
                    if isinstance(response_data, list) and len(response_data) > 0:
                        if isinstance(response_data[0], list):
                            results.extend(response_data)
                        elif isinstance(response_data[0], float):
                            results.append(response_data)
                    else:
                        raise ValueError(f"Unexpected response format: {response_data}")
            return results
        except Exception as e:
            logger.warning("Failed to generate embeddings via Hugging Face API, falling back to local: %s", e)
        return None

    def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformers model locally on first use."""
        if self._model is None:
            logger.info("Loading embedding model locally: %s", self.MODEL_NAME)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        # 1. Try Hugging Face API first to save memory
        api_results = self._embed_via_hf_api(texts)
        if api_results is not None:
            return api_results

        # 2. Fallback to local execution
        model = self._load_model()
        logger.debug("Embedding %d documents locally", len(texts))
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string."""
        # 1. Try Hugging Face API first to save memory
        api_results = self._embed_via_hf_api([text])
        if api_results is not None:
            return api_results[0]

        # 2. Fallback to local execution
        model = self._load_model()
        logger.debug("Embedding query locally: %.80s...", text)
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()


# Module-level singleton — import and reuse throughout the application.
embedding_service = EmbeddingService()
