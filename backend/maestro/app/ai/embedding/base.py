"""
BaseEmbeddingProvider — abstract interface for text embedding generation.

Separated from BaseLLMProvider because:
  - Embedding models have different versioning lifecycles than chat models.
  - You may want Google embeddings with an OpenAI chat model, or vice versa.
  - Re-indexing documents when switching models is a discrete operation that
    needs to know which provider/model generated each embedding (stored in
    knowledge_embeddings.provider and .model).

Sprint 005 implements GeminiEmbeddingProvider only.
Future: OpenAIEmbeddingProvider, VoyageEmbeddingProvider, LocalEmbeddingProvider.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Abstract base for all embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Short identifier string, stored in knowledge_embeddings.provider.
        Example: "google", "openai", "voyage"
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Model identifier string, stored in knowledge_embeddings.model.
        Example: "text-embedding-004", "text-embedding-3-small"
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        Output vector dimensions, stored in knowledge_embeddings.dimensions.
        Example: 768, 1536, 1024
        """
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.

        Implementations should process the list as a single batch where the
        provider API supports it, or fall back to individual calls.

        Args:
            texts: List of non-empty strings to embed.

        Returns:
            List of float vectors, one per input text, in the same order.
            Each vector has length == self.dimensions.
        """
        pass
