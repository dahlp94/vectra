"""Embedding service that batches provider calls for ingestion use."""

from __future__ import annotations

from app.embeddings.provider import EmbeddingProvider


class EmbeddingService:
    """Batching wrapper around an ``EmbeddingProvider``."""

    def __init__(self, provider: EmbeddingProvider, batch_size: int = 64) -> None:
        """
        Initialize embedding service.

        Args:
            provider: Provider implementation used to generate embeddings.
            batch_size: Maximum texts per provider call.
        """
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._provider = provider
        self._batch_size = batch_size

    @staticmethod
    def _filter_valid_texts(texts: list[str]) -> list[str]:
        """
        Keep non-empty texts only, preserving order.

        Empty values and whitespace-only strings are dropped to avoid unnecessary
        embedding calls and provider-side validation errors.
        """
        filtered: list[str] = []
        for text in texts:
            normalized = text.strip()
            if normalized:
                filtered.append(normalized)
        return filtered

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for valid texts in batches.

        Args:
            texts: Raw text inputs.

        Returns:
            Embeddings for valid inputs only, in the same order as those valid inputs.

        Raises:
            RuntimeError: If the provider fails while embedding a batch.
        """
        valid_texts = self._filter_valid_texts(texts)
        if not valid_texts:
            return []

        all_embeddings: list[list[float]] = []
        for start in range(0, len(valid_texts), self._batch_size):
            batch = valid_texts[start : start + self._batch_size]
            try:
                batch_embeddings = self._provider.embed_texts(batch)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to generate embeddings for batch starting at index {start}: {exc}"
                ) from exc

            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    "Embedding provider returned mismatched result length "
                    f"(expected {len(batch)}, got {len(batch_embeddings)})"
                )

            all_embeddings.extend(batch_embeddings)

        return all_embeddings
