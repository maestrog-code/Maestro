"""
GeminiEmbeddingProvider — embedding implementation using Google's text-embedding-004.

All configuration comes from ai_settings (AI_ env prefix) so no values are hardcoded.
Processes texts individually because the google-genai SDK's embed_content
accepts a single content per call in its current version.
"""
import os
from typing import List

from google import genai

from app.ai.embedding.base import BaseEmbeddingProvider
from app.core.ai_settings import ai_settings


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider (text-embedding-004)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def model_name(self) -> str:
        return ai_settings.EMBEDDING_MODEL  # "text-embedding-004"

    @property
    def dimensions(self) -> int:
        return ai_settings.EMBEDDING_DIMENSIONS  # 768

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts using Google's text-embedding-004 model.
        Falls back to a zero vector of correct dimensions if an individual
        call fails (rather than failing the entire batch).
        """
        results: List[List[float]] = []
        for text in texts:
            try:
                if self.client is None:
                    results.append([0.0] * self.dimensions)
                    continue
                response = await self.client.aio.models.embed_content(
                    model=self.model_name,
                    contents=text,
                )
                if response.embeddings and len(response.embeddings) > 0:
                    results.append(list(response.embeddings[0].values))
                else:
                    results.append([0.0] * self.dimensions)
            except Exception:
                # Degrade gracefully — the Celery task will retry on failure
                results.append([0.0] * self.dimensions)
        return results


# Module-level singleton — swap for a different provider without touching callers.
default_embedding_provider: BaseEmbeddingProvider = GeminiEmbeddingProvider()
