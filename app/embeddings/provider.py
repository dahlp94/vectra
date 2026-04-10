"""Embedding provider abstraction and MVP OpenAI implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Minimal contract for embedding providers."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: Input texts in caller-defined order.

        Returns:
            Embedding vectors in the same order as ``texts``.
        """


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        """
        Initialize OpenAI embedding client.

        Raises:
            RuntimeError: If the OpenAI SDK is unavailable.
        """
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for OpenAIEmbeddingProvider. "
                "Install it with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a non-empty text batch."""
        if not texts:
            return []

        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as exc:
            raise RuntimeError(f"OpenAI embedding request failed: {exc}") from exc
