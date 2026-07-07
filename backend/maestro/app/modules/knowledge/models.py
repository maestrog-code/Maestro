"""
Knowledge module SQLAlchemy models.

Tables created by migration 003_knowledge_engine:
    - knowledge_documents
    - knowledge_chunks      (text content + metadata; NO embedding column)
    - knowledge_embeddings  (embedding vectors; provider/model metadata)
    - knowledge_tags
"""
import enum

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.models.base import TimestampedModel


# ---------------------------------------------------------------------------
# Python enums
# ---------------------------------------------------------------------------

class DocType(str, enum.Enum):
    file   = "file"
    note   = "note"
    policy = "policy"
    sop    = "sop"


class DocStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    indexed    = "indexed"
    failed     = "failed"


class Visibility(str, enum.Enum):
    org     = "org"      # visible to all org members during retrieval
    private = "private"  # only visible to created_by user


# ---------------------------------------------------------------------------
# SQLAlchemy Enum types
# ---------------------------------------------------------------------------

doc_type_enum   = Enum(DocType,    name="doc_type_enum",   create_type=False)
doc_status_enum = Enum(DocStatus,  name="doc_status_enum", create_type=False)
visibility_enum = Enum(Visibility, name="visibility_enum", create_type=False)


# ---------------------------------------------------------------------------
# KnowledgeDocument
# ---------------------------------------------------------------------------

class KnowledgeDocument(TimestampedModel):
    """
    Represents a single knowledge artifact within an organization.
    Supports files (PDF, DOCX, TXT, Markdown) and inline notes/policies/SOPs.
    """
    __tablename__ = "knowledge_documents"

    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title     = Column(String(500), nullable=False)
    doc_type  = Column(doc_type_enum, nullable=False, default=DocType.note)

    # File-specific (null for inline notes)
    file_name = Column(String(255),  nullable=True)   # original filename
    file_path = Column(String(1000), nullable=True)   # path from StorageProvider.save()
    mime_type = Column(String(100),  nullable=True)

    # Extracted content
    content      = Column(Text,       nullable=True)   # raw extracted text
    content_hash = Column(String(64), nullable=True)   # SHA-256; skip re-index if unchanged

    status     = Column(doc_status_enum, nullable=False, default=DocStatus.pending, index=True)
    visibility = Column(visibility_enum, nullable=False, default=Visibility.org)

    # Relationships
    chunks = relationship("KnowledgeChunk", back_populates="document", lazy="select")
    tags   = relationship("KnowledgeTag",   back_populates="document", lazy="select")


# ---------------------------------------------------------------------------
# KnowledgeChunk
# ---------------------------------------------------------------------------

class KnowledgeChunk(TimestampedModel):
    """
    A single text chunk of a KnowledgeDocument.

    NOTE: This table stores text content and structural metadata only.
    The embedding vector lives in KnowledgeEmbedding (separate table).
    This decouples the embedding model lifecycle from the chunk lifecycle.
    """
    __tablename__ = "knowledge_chunks"

    document_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index = Column(Integer, nullable=False)
    content     = Column(Text,    nullable=False)
    token_count = Column(Integer, nullable=False, default=0)

    # Structural metadata (from HybridChunker)
    page_number = Column(Integer,      nullable=True)   # PDF page number
    section     = Column(String(500),  nullable=True)   # heading path ("Sales > Pipeline")
    heading     = Column(String(255),  nullable=True)   # immediate heading text
    checksum    = Column(String(64),   nullable=False, default="")   # SHA-256 of chunk content
    language    = Column(String(10),   nullable=False, default="en")

    # Provenance metadata (for debugging retrieval quality)
    parser_version = Column(String(20), nullable=True)  # e.g. "hybrid-v1"

    # Relationships
    document   = relationship("KnowledgeDocument", back_populates="chunks")
    embeddings = relationship("KnowledgeEmbedding", back_populates="chunk", lazy="select")


# ---------------------------------------------------------------------------
# KnowledgeEmbedding  ← NEW: separated from KnowledgeChunk
# ---------------------------------------------------------------------------

class KnowledgeEmbedding(TimestampedModel):
    """
    Stores a single embedding vector for a KnowledgeChunk.

    Keeping embeddings in a separate table from chunks means:
      - Switching embedding models creates new rows (old vectors are not overwritten).
      - Each row records which provider and model produced it.
      - Multi-model experiments (e.g., compare text-embedding-004 vs Voyage) are possible.
      - Re-indexing with a new model does not require touching knowledge_chunks at all.

    The actual VECTOR(n) column is managed by the Alembic migration and raw SQL
    in PgVectorStore — the ORM column type is Text as a placeholder because
    SQLAlchemy does not natively support pgvector's VECTOR type yet.
    """
    __tablename__ = "knowledge_embeddings"

    chunk_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Embedding provenance — stored so re-indexing can be targeted per model
    provider   = Column(String(50),  nullable=False)    # "google", "openai"
    model      = Column(String(100), nullable=False)    # "text-embedding-004"
    dimensions = Column(Integer,     nullable=False)    # 768, 1536, etc.

    # `vector` column (VECTOR(n)) is created by migration; ORM does not manage it.
    # All reads/writes go through PgVectorStore raw SQL.

    # Relationships
    chunk = relationship("KnowledgeChunk", back_populates="embeddings")


# ---------------------------------------------------------------------------
# KnowledgeTag
# ---------------------------------------------------------------------------

class KnowledgeTag(TimestampedModel):
    """A user-defined tag associated with a KnowledgeDocument."""
    __tablename__ = "knowledge_tags"

    document_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag = Column(String(100), nullable=False)

    # Relationships
    document = relationship("KnowledgeDocument", back_populates="tags")
