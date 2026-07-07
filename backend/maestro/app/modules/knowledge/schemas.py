"""
Knowledge module — Pydantic request and response schemas.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.models import DocStatus, DocType, Visibility


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    """Create an inline knowledge document (note, policy, SOP — no file upload)."""
    title: str = Field(..., min_length=1, max_length=500)
    doc_type: DocType = DocType.note
    visibility: Visibility = Visibility.org
    content: str = Field(..., min_length=1, description="Raw text content of the document")
    tags: List[str] = Field(default_factory=list, description="Optional list of tag strings")


class SearchRequest(BaseModel):
    """Semantic search request body."""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[dict] = Field(
        default=None,
        description="Optional metadata filters: doc_type, visibility"
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tag: str


class DocumentResponse(BaseModel):
    """Full document response including indexing status."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    doc_type: DocType
    file_name: Optional[str]
    mime_type: Optional[str]
    status: DocStatus
    visibility: Visibility
    content_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class ChunkResult(BaseModel):
    """A single result from a semantic search."""
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    score: float = Field(..., description="Cosine similarity score, 0.0–1.0")
    chunk_index: int
    page_number: Optional[int]
    section: Optional[str]
    heading: Optional[str]


class SearchResponse(BaseModel):
    """Response from a semantic search request."""
    query: str
    results: List[ChunkResult]
    total_results: int


class ReindexResponse(BaseModel):
    """Acknowledgement that a reindex job has been queued."""
    document_id: UUID
    message: str
    skipped: bool = Field(
        default=False,
        description="True if reindex was skipped because content_hash is unchanged"
    )
