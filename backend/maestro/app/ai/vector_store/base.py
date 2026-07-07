"""
VectorStore — abstract interface for vector similarity search.

Mirrors the BaseLLMProvider pattern from Sprint 004.
Sprint 005 implements PgVectorStore only.
Future sprints can add PineconeStore, QdrantStore without changing callers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class ChunkVector:
    """
    A single embedding record ready to be upserted into the vector store.
    Fields map to both knowledge_chunks and knowledge_embeddings tables.
    """
    chunk_id: UUID
    document_id: UUID
    organization_id: UUID
    content: str
    embedding: List[float]
    token_count: int
    chunk_index: int
    # Embedding provenance (stored in knowledge_embeddings)
    provider: str = "google"
    model: str = "text-embedding-004"
    dimensions: int = 768
    # Structural metadata (stored in knowledge_chunks)
    page_number: Optional[int] = None
    section: Optional[str] = None
    heading: Optional[str] = None
    checksum: str = ""
    language: str = "en"
    parser_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)



@dataclass
class SearchResult:
    """A single result returned from a vector similarity search."""
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    score: float              # cosine similarity, 0.0–1.0 (higher = more similar)
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    heading: Optional[str] = None


class VectorStore(ABC):
    """Abstract base class for all vector store backends."""

    @abstractmethod
    async def upsert(self, chunks: List[ChunkVector]) -> None:
        """
        Insert or update a batch of chunk embeddings.

        Args:
            chunks: List of ChunkVector records to upsert.
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        org_id: UUID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Perform approximate nearest-neighbour search scoped to an organization.

        Args:
            query_vector: The embedded query vector (same dimensions as stored embeddings).
            org_id:       Organization UUID — search is always org-scoped.
            top_k:        Maximum number of results to return.
            filters:      Optional metadata filters (e.g. doc_type, visibility).

        Returns:
            List of SearchResult ordered by descending similarity score.
        """
        pass

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None:
        """
        Delete all chunk vectors associated with a given document.
        Called when a document is deleted or before a full reindex.

        Args:
            document_id: The document whose chunks should be removed.
        """
        pass
