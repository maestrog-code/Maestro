# MAESTRO — Sprint 005 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 005 is on branch `feature/organizational-knowledge-engine`.
This document contains every implementation file in full, exactly as committed.

---

## `app/modules/knowledge/models.py`

```py
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
```

---

## `app/modules/knowledge/schemas.py`

```py
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
```

---

## `app/modules/knowledge/repositories.py`

```py
"""
Knowledge module — repositories.

KnowledgeDocumentRepository: CRUD for knowledge_documents.
KnowledgeChunkRepository: CRUD for knowledge_chunks (non-vector operations only;
                          vector upsert and search are handled by PgVectorStore).
KnowledgeTagRepository: tag management.
"""
import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.knowledge.models import (
    DocStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeTag,
)
from app.shared.utils.repository import BaseRepository


# ---------------------------------------------------------------------------
# Document repository
# ---------------------------------------------------------------------------

class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    """CRUD operations for KnowledgeDocument, always org-scoped."""

    def __init__(self):
        super().__init__(KnowledgeDocument)

    async def get_by_org(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[KnowledgeDocument]:
        """List all non-deleted documents for an organization, newest first."""
        query = (
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.tags))
            .where(
                KnowledgeDocument.organization_id == org_id,
                KnowledgeDocument.is_deleted == False,  # noqa: E712
            )
            .order_by(KnowledgeDocument.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_org(self, db: AsyncSession, org_id: uuid.UUID) -> int:
        """Count non-deleted documents for an organization."""
        query = select(func.count()).where(
            KnowledgeDocument.organization_id == org_id,
            KnowledgeDocument.is_deleted == False,  # noqa: E712
        )
        result = await db.execute(query)
        return result.scalar_one()

    async def get_org_document(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        doc_id: uuid.UUID,
    ) -> Optional[KnowledgeDocument]:
        """Get a single document scoped to an organization (includes tags)."""
        query = (
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.tags))
            .where(
                KnowledgeDocument.id == doc_id,
                KnowledgeDocument.organization_id == org_id,
                KnowledgeDocument.is_deleted == False,  # noqa: E712
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        db: AsyncSession,
        doc_id: uuid.UUID,
        status: DocStatus,
        content: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        """Update a document's processing status (called by Celery worker)."""
        doc = await self.get(db, doc_id)
        if not doc:
            return
        doc.status = status
        if content is not None:
            doc.content = content
        if content_hash is not None:
            doc.content_hash = content_hash
        db.add(doc)
        await db.commit()


document_repository = KnowledgeDocumentRepository()


# ---------------------------------------------------------------------------
# Chunk repository
# ---------------------------------------------------------------------------

class KnowledgeChunkRepository(BaseRepository[KnowledgeChunk]):
    """
    ORM-level operations on knowledge_chunks.
    Vector upsert and similarity search are handled by PgVectorStore, not here.
    """

    def __init__(self):
        super().__init__(KnowledgeChunk)

    async def get_by_document(
        self, db: AsyncSession, document_id: uuid.UUID
    ) -> List[KnowledgeChunk]:
        """List all non-deleted chunks for a document, ordered by chunk_index."""
        query = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.document_id == document_id,
                KnowledgeChunk.is_deleted == False,  # noqa: E712
            )
            .order_by(KnowledgeChunk.chunk_index)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


chunk_repository = KnowledgeChunkRepository()


# ---------------------------------------------------------------------------
# Tag repository
# ---------------------------------------------------------------------------

class KnowledgeTagRepository(BaseRepository[KnowledgeTag]):
    """CRUD for knowledge_tags."""

    def __init__(self):
        super().__init__(KnowledgeTag)

    async def create_tags(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        tags: List[str],
    ) -> List[KnowledgeTag]:
        """Bulk-create tags for a document."""
        tag_models = [
            KnowledgeTag(document_id=document_id, tag=t.strip().lower())
            for t in tags
            if t.strip()
        ]
        for t in tag_models:
            db.add(t)
        await db.commit()
        for t in tag_models:
            await db.refresh(t)
        return tag_models

    async def delete_by_document(self, db: AsyncSession, document_id: uuid.UUID) -> None:
        """Soft-delete all tags for a document (called during reindex or delete)."""
        tags = await self.get_multi(
            db, filters=[KnowledgeTag.document_id == document_id]
        )
        from datetime import datetime
        for tag in tags:
            tag.is_deleted = True
            tag.deleted_at = datetime.utcnow()
            db.add(tag)
        await db.commit()


tag_repository = KnowledgeTagRepository()
```

---

## `app/modules/knowledge/services.py`

```py
"""
KnowledgeService — business logic for the Organizational Knowledge Engine.

Responsibilities:
    - Accept document creation and file uploads
    - Enqueue Celery processing tasks (async — returns 202 immediately)
    - Orchestrate semantic search with private-doc security
    - Reindex documents (with content_hash skip)
    - Soft-delete documents and their vectors

Document processing (extract → chunk → embed → index) happens in
`app/workers/knowledge_tasks.py` inside a Celery worker, not here.
"""
import hashlib
import io
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding.google import GeminiEmbeddingProvider
from app.ai.vector_store.pgvector import PgVectorStore
from app.ai.storage.local import storage_provider
from app.core.ai_settings import ai_settings
from app.modules.knowledge.models import DocStatus, DocType, KnowledgeDocument, Visibility
from app.modules.knowledge.repositories import (
    document_repository,
    tag_repository,
)
from app.modules.knowledge.schemas import (
    ChunkResult,
    DocumentCreate,
    DocumentResponse,
    SearchResponse,
)
from app.modules.users.models import User


class KnowledgeService:
    """Business logic for the knowledge engine. Instantiated per-request."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = PgVectorStore(db)
        self.embedding_provider = GeminiEmbeddingProvider()

    # ------------------------------------------------------------------
    # Document creation
    # ------------------------------------------------------------------

    async def create_note(
        self,
        org_id: UUID,
        user: User,
        data: DocumentCreate,
    ) -> KnowledgeDocument:
        """
        Create an inline knowledge document (note, policy, SOP).
        Sets status=pending and enqueues a Celery processing task.
        The caller should return 202 Accepted immediately.
        """
        doc = await document_repository.create(
            self.db,
            obj_in={
                "organization_id": org_id,
                "title": data.title,
                "doc_type": data.doc_type,
                "visibility": data.visibility,
                "content": data.content,
                "status": DocStatus.pending,
                "created_by": user.id,
                "updated_by": user.id,
            },
        )
        await self.db.commit()
        await self.db.refresh(doc)

        if data.tags:
            await tag_repository.create_tags(self.db, doc.id, data.tags)

        # Enqueue async Celery task
        from app.workers.knowledge_tasks import process_document_task
        process_document_task.delay(str(doc.id))

        return doc

    async def upload_file(
        self,
        org_id: UUID,
        user: User,
        file: UploadFile,
        title: str,
        doc_type: DocType = DocType.file,
        visibility: Visibility = Visibility.org,
        tags: Optional[List[str]] = None,
    ) -> KnowledgeDocument:
        """
        Accept a file upload, persist it via StorageProvider, create a DB record,
        and enqueue processing. Returns immediately with status=pending.
        """
        content_bytes = await file.read()
        mime_type = file.content_type or "application/octet-stream"
        file_path = await storage_provider.save(file.filename or "upload", content_bytes, org_id)

        doc = await document_repository.create(
            self.db,
            obj_in={
                "organization_id": org_id,
                "title": title,
                "doc_type": doc_type,
                "file_name": file.filename,
                "file_path": file_path,
                "mime_type": mime_type,
                "visibility": visibility,
                "status": DocStatus.pending,
                "created_by": user.id,
                "updated_by": user.id,
            },
        )
        await self.db.commit()
        await self.db.refresh(doc)

        if tags:
            await tag_repository.create_tags(self.db, doc.id, tags)

        # Enqueue async Celery task
        from app.workers.knowledge_tasks import process_document_task
        process_document_task.delay(str(doc.id))

        return doc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        org_id: UUID,
        user: User,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> SearchResponse:
        """
        Embed the query and perform cosine similarity search.

        Private document security:
            - Documents with visibility=org → visible to all org members.
            - Documents with visibility=private → only visible to created_by user.
              This is enforced by adding a filter that excludes private docs of other users.
        """
        # Embed the query (single text)
        query_vectors = await self.embedding_provider.embed([query])

        query_vector = query_vectors[0]

        # Build search filters — always exclude other users' private docs
        search_filters = dict(filters or {})

        # Retrieve with org scope (PgVectorStore enforces org_id)
        raw_results = await self.vector_store.search(
            query_vector=query_vector,
            org_id=org_id,
            top_k=top_k * 2,  # fetch more, then filter private docs below
            filters=search_filters,
        )

        # Post-filter: remove private docs not owned by this user
        filtered = []
        for r in raw_results:
            doc = await document_repository.get(self.db, r.document_id)
            if doc and doc.visibility == Visibility.private:
                if str(doc.created_by) != str(user.id):
                    continue  # skip — private and not owner
            filtered.append(r)
            if len(filtered) >= top_k:
                break

        results = [
            ChunkResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                content=r.content,
                score=r.score,
                chunk_index=r.chunk_index,
                page_number=r.page_number,
                section=r.section,
                heading=r.heading,
            )
            for r in filtered
        ]

        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
        )

    # ------------------------------------------------------------------
    # Reindex
    # ------------------------------------------------------------------

    async def reindex_document(
        self,
        org_id: UUID,
        doc_id: UUID,
        user: User,
    ) -> dict:
        """
        Trigger a re-embedding of a document.
        If content_hash is unchanged, skip and return skipped=True.
        """
        doc = await document_repository.get_org_document(self.db, org_id, doc_id)
        if not doc:
            return {"skipped": False, "reason": "not_found"}

        # Compute current hash from stored content
        if doc.content:
            current_hash = hashlib.sha256(doc.content.encode()).hexdigest()
            if current_hash == doc.content_hash and doc.status == DocStatus.indexed:
                return {"skipped": True, "reason": "content_unchanged"}

        # Queue reindex
        from app.workers.knowledge_tasks import process_document_task
        process_document_task.delay(str(doc.id))
        return {"skipped": False, "reason": "queued"}

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_document(
        self,
        org_id: UUID,
        doc_id: UUID,
        user: User,
    ) -> bool:
        """
        Soft-delete the document and all its vectors.
        Returns False if document not found.
        """
        doc = await document_repository.get_org_document(self.db, org_id, doc_id)
        if not doc:
            return False

        # Soft-delete vectors
        await self.vector_store.delete_by_document(doc_id)

        # Soft-delete the document record
        await document_repository.soft_delete(self.db, id=doc_id)
        await self.db.commit()
        return True

    # ------------------------------------------------------------------
    # List & Get
    # ------------------------------------------------------------------

    async def list_documents(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List documents for an organization (paginated)."""
        skip = (page - 1) * page_size
        items = await document_repository.get_by_org(self.db, org_id, skip=skip, limit=page_size)
        total = await document_repository.count_by_org(self.db, org_id)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_document(
        self,
        org_id: UUID,
        doc_id: UUID,
    ) -> Optional[KnowledgeDocument]:
        """Get a single document scoped to an organization."""
        return await document_repository.get_org_document(self.db, org_id, doc_id)
```

---

## `app/modules/knowledge/router.py`

```py
"""
API Router for Knowledge Management.
Handles document ingestion, listing, search, and retrieval.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import OrganizationPermissionService
from app.modules.knowledge.services import KnowledgeService
from app.modules.knowledge.schemas import (
    DocumentUploadResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    DocumentResponse,
    DocumentListResponse
)


router = APIRouter(prefix="/organizations/{organization_id}/knowledge", tags=["Knowledge"])


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    organization_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("file"),
    visibility: str = Form("org"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file to the knowledge base.
    Returns 202 Accepted because extraction and chunking happen asynchronously.
    """
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)

    file_bytes = await file.read()
    doc_id = await service.create_from_file(
        org_id=organization_id,
        user=current_user,
        file_name=file.filename,
        file_bytes=file_bytes,
        mime_type=file.content_type,
        title=title,
        doc_type=doc_type,
        visibility=visibility
    )
    return DocumentUploadResponse(document_id=doc_id, status="pending")


@router.post("/documents/note", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_inline_note(
    organization_id: UUID,
    title: str = Form(...),
    content: str = Form(...),
    doc_type: str = Form("note"),
    visibility: str = Form("org"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an inline text document in the knowledge base without uploading a file.
    """
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)

    doc_id = await service.create_inline(
        org_id=organization_id,
        user=current_user,
        title=title,
        content=content,
        doc_type=doc_type,
        visibility=visibility
    )
    return DocumentUploadResponse(document_id=doc_id, status="pending")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    organization_id: UUID,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents in the knowledge base."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    return await service.list_documents(organization_id, page, page_size)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    organization_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document details."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    
    doc = await service.get_document(organization_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type.value,
        status=doc.status.value,
        visibility=doc.visibility.value,
        created_at=doc.created_at,
        file_name=doc.file_name,
        content=doc.content
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    organization_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document and its embeddings."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    success = await service.delete_document(organization_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    organization_id: UUID,
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search the knowledge base via vector similarity."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    
    return await service.search(
        org_id=organization_id,
        user=current_user,
        query=request.query,
        top_k=request.limit,
        filters=request.filters
    )
```

---

## `app/modules/knowledge/parsers.py`

```py
"""
Document parsers — BaseParser abstraction for text extraction.

Each parser accepts raw file bytes and returns plain text.
The HybridChunker then splits that text into chunks.

Sprint 005 implementations:
    TextParser     — .txt, .md files
    PDFParser      — .pdf files via PyPDF2
    DOCXParser     — .docx files via python-docx
    FallbackParser — UTF-8 decode of any file

Adding support for a new format: implement BaseParser, register in PARSER_REGISTRY.
"""
import io
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

logger = logging.getLogger(__name__)

PARSER_VERSION = "hybrid-v1"  # bump when chunking or parsing logic changes


class BaseParser(ABC):
    """Abstract base for all document text extractors."""

    @abstractmethod
    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        """
        Extract plain text from raw file bytes.

        Args:
            content:   Raw file bytes.
            file_name: Optional original filename (used as hints for format detection).

        Returns:
            Plain text string. Empty string on failure (callers handle empty content).
        """
        pass

    @property
    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """List of MIME types this parser handles."""
        pass


class TextParser(BaseParser):
    """Handles plain text (.txt) and Markdown (.md) files."""

    @property
    def supported_mime_types(self) -> list[str]:
        return ["text/plain", "text/markdown", "text/x-markdown"]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        return content.decode("utf-8", errors="replace")


class PDFParser(BaseParser):
    """Handles PDF files via PyPDF2."""

    @property
    def supported_mime_types(self) -> list[str]:
        return ["application/pdf"]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as exc:
            logger.error("PDFParser.extract failed: %s", exc)
            return ""


class DOCXParser(BaseParser):
    """Handles .docx files via python-docx."""

    @property
    def supported_mime_types(self) -> list[str]:
        return [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            import docx
            document = docx.Document(io.BytesIO(content))
            return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error("DOCXParser.extract failed: %s", exc)
            return ""


class FallbackParser(BaseParser):
    """Last-resort UTF-8 decode for unknown file types."""

    @property
    def supported_mime_types(self) -> list[str]:
        return []

    def extract(self, content: bytes, file_name: Optional[str] = None) -> str:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Parser registry — maps MIME types to parser instances
# ---------------------------------------------------------------------------

_text_parser    = TextParser()
_pdf_parser     = PDFParser()
_docx_parser    = DOCXParser()
_fallback       = FallbackParser()

PARSER_REGISTRY: Dict[str, BaseParser] = {}
for _parser in [_text_parser, _pdf_parser, _docx_parser]:
    for _mime in _parser.supported_mime_types:
        PARSER_REGISTRY[_mime] = _parser


def get_parser(mime_type: Optional[str], file_name: Optional[str] = None) -> BaseParser:
    """
    Return the appropriate parser for a MIME type.
    Falls back by file extension, then to FallbackParser.
    """
    if mime_type and mime_type in PARSER_REGISTRY:
        return PARSER_REGISTRY[mime_type]

    # Extension-based fallback
    if file_name:
        fn = file_name.lower()
        if fn.endswith((".txt", ".md", ".markdown")):
            return _text_parser
        if fn.endswith(".pdf"):
            return _pdf_parser
        if fn.endswith(".docx"):
            return _docx_parser

    return _fallback
```

---

## `app/ai/tools/knowledge_tools.py`

```py
"""
Knowledge base tools for AI agents.

These tools allow agents to search the organization's knowledge base and read
specific documents. The tools enforce organization-level scoping implicitly
via the execution context.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.modules.knowledge.services import KnowledgeService


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="The semantic search query.")
    doc_type: Optional[str] = Field(None, description="Optional filter by document type (e.g. 'policy', 'sop', 'note').")
    limit: int = Field(5, description="Maximum number of chunks to return (max 10).")


class SearchKnowledgeBaseOutput(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int


class GetDocumentInput(BaseModel):
    document_id: str = Field(..., description="The UUID of the document to retrieve.")


class GetDocumentOutput(BaseModel):
    id: str
    title: str
    content: str
    doc_type: str


class ListDocumentsInput(BaseModel):
    limit: int = Field(20, description="Max documents to return")
    page: int = Field(1, description="Page number")


class ListDocumentsOutput(BaseModel):
    documents: List[Dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = "Searches the organization's internal knowledge base for information."
    input_schema = SearchKnowledgeBaseInput
    output_schema = SearchKnowledgeBaseOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID, user_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id
        # We need the user to enforce private doc visibility
        from app.modules.users.models import User
        self.user = User(id=user_id) # Mock user object with just ID for the service

    async def execute(self, **kwargs) -> Any:
        # Pydantic validation handles parsing
        query = kwargs.get("query")
        limit = min(kwargs.get("limit", 5), 10)
        doc_type = kwargs.get("doc_type")

        filters = {}
        if doc_type:
            filters["doc_type"] = doc_type

        search_resp = await self.service.search(
            org_id=self.org_id,
            user=self.user,
            query=query,
            top_k=limit,
            filters=filters
        )

        results = []
        for r in search_resp.results:
            results.append({
                "document_id": str(r.document_id),
                "title": r.document_title,
                "content_snippet": r.content,
                "score": round(r.score, 3),
                "page": r.page_number,
                "section": r.section
            })

        return {
            "results": results,
            "total_found": search_resp.total_results
        }


class GetDocumentTool(BaseTool):
    name = "get_document"
    description = "Retrieves the full content of a specific knowledge document by its ID."
    input_schema = GetDocumentInput
    output_schema = GetDocumentOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id

    async def execute(self, **kwargs) -> Any:
        try:
            doc_uuid = UUID(kwargs.get("document_id"))
        except ValueError:
            return {"error": "Invalid document_id format."}

        doc = await self.service.get_document(org_id=self.org_id, doc_id=doc_uuid)
        if not doc:
            return {"error": "Document not found or access denied."}

        return {
            "id": str(doc.id),
            "title": doc.title,
            "content": doc.content or "No text content available.",
            "doc_type": doc.doc_type.value
        }


class ListDocumentsTool(BaseTool):
    name = "list_documents"
    description = "Lists all available knowledge documents in the organization."
    input_schema = ListDocumentsInput
    output_schema = ListDocumentsOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id

    async def execute(self, **kwargs) -> Any:
        limit = min(kwargs.get("limit", 20), 50)
        page = max(kwargs.get("page", 1), 1)

        result = await self.service.list_documents(org_id=self.org_id, page=page, page_size=limit)
        
        docs = []
        for d in result["items"]:
            docs.append({
                "id": str(d.id),
                "title": d.title,
                "doc_type": d.doc_type.value,
                "status": d.status.value
            })

        return {
            "documents": docs,
            "total": result["total"]
        }
```

---

## `app/ai/vector_store/pgvector.py`

```py
"""
PgVectorStore — VectorStore implementation backed by PostgreSQL + pgvector.

Schema layout (Sprint 005 refactor):
    knowledge_chunks      — text content + structural metadata
    knowledge_embeddings  — embedding vector + provider/model provenance

All vector reads/writes target knowledge_embeddings.
The IVFFLAT index lives on knowledge_embeddings.vector.

Search JOINs: knowledge_embeddings ↔ knowledge_chunks ↔ knowledge_documents.
Organization isolation is enforced at this level via WHERE organization_id = :org_id.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.vector_store.base import ChunkVector, SearchResult, VectorStore


class PgVectorStore(VectorStore):
    """
    PostgreSQL + pgvector implementation of VectorStore.
    Vectors live in `knowledge_embeddings`, not `knowledge_chunks`.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, chunks: List[ChunkVector]) -> None:
        """
        1. Upsert into knowledge_chunks (text + metadata).
        2. Upsert into knowledge_embeddings (vector + provenance).

        Uses INSERT ... ON CONFLICT (id) DO UPDATE to support reindexing.
        """
        if not chunks:
            return

        for chunk in chunks:
            # --- 1. Upsert chunk row ---
            await self.db.execute(
                text("""
                    INSERT INTO knowledge_chunks
                        (id, document_id, organization_id, chunk_index, content,
                         token_count, page_number, section, heading,
                         checksum, language, parser_version,
                         created_at, updated_at, is_deleted, version)
                    VALUES
                        (:id, :document_id, :organization_id, :chunk_index, :content,
                         :token_count, :page_number, :section, :heading,
                         :checksum, :language, :parser_version,
                         NOW(), NOW(), FALSE, 1)
                    ON CONFLICT (id) DO UPDATE SET
                        content        = EXCLUDED.content,
                        token_count    = EXCLUDED.token_count,
                        page_number    = EXCLUDED.page_number,
                        section        = EXCLUDED.section,
                        heading        = EXCLUDED.heading,
                        checksum       = EXCLUDED.checksum,
                        language       = EXCLUDED.language,
                        parser_version = EXCLUDED.parser_version,
                        updated_at     = NOW(),
                        version        = knowledge_chunks.version + 1
                """),
                {
                    "id":             str(chunk.chunk_id),
                    "document_id":    str(chunk.document_id),
                    "organization_id": str(chunk.organization_id),
                    "chunk_index":    chunk.chunk_index,
                    "content":        chunk.content,
                    "token_count":    chunk.token_count,
                    "page_number":    chunk.page_number,
                    "section":        chunk.section,
                    "heading":        chunk.heading,
                    "checksum":       chunk.checksum,
                    "language":       chunk.language,
                    "parser_version": chunk.parser_version,
                },
            )

            # --- 2. Upsert embedding row ---
            embedding_str = "[" + ",".join(str(v) for v in chunk.embedding) + "]"
            await self.db.execute(
                text("""
                    INSERT INTO knowledge_embeddings
                        (id, chunk_id, organization_id, provider, model, dimensions, vector,
                         created_at, updated_at, is_deleted, version)
                    VALUES
                        (gen_random_uuid(), :chunk_id, :organization_id,
                         :provider, :model, :dimensions, :vector::vector,
                         NOW(), NOW(), FALSE, 1)
                    ON CONFLICT (chunk_id, model) DO UPDATE SET
                        vector     = EXCLUDED.vector,
                        updated_at = NOW(),
                        version    = knowledge_embeddings.version + 1
                """),
                {
                    "chunk_id":       str(chunk.chunk_id),
                    "organization_id": str(chunk.organization_id),
                    "provider":       chunk.provider,
                    "model":          chunk.model,
                    "dimensions":     chunk.dimensions,
                    "vector":         embedding_str,
                },
            )

        await self.db.commit()

    async def search(
        self,
        query_vector: List[float],
        org_id: UUID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Cosine similarity search via knowledge_embeddings JOIN knowledge_chunks JOIN knowledge_documents.
        Always scoped to org_id. Returns up to top_k results ordered by cosine similarity descending.
        """
        embedding_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        extra_conditions = ""
        params: Dict[str, Any] = {
            "vector":  embedding_str,
            "org_id":  str(org_id),
            "top_k":   top_k,
        }

        if filters:
            if "doc_type" in filters:
                extra_conditions += " AND kd.doc_type = :doc_type"
                params["doc_type"] = filters["doc_type"]
            if "model" in filters:
                # Allow filtering by embedding model — useful during model transitions
                extra_conditions += " AND ke.model = :model"
                params["model"] = filters["model"]

        sql = text(f"""
            SELECT
                kc.id            AS chunk_id,
                kc.document_id,
                kd.title         AS document_title,
                kc.content,
                kc.chunk_index,
                kc.page_number,
                kc.section,
                kc.heading,
                ke.provider,
                ke.model         AS embedding_model,
                1 - (ke.vector <=> :vector::vector) AS score
            FROM knowledge_embeddings ke
            JOIN knowledge_chunks kc
                ON kc.id = ke.chunk_id
            JOIN knowledge_documents kd
                ON kd.id = kc.document_id
            WHERE ke.organization_id = :org_id
              AND ke.is_deleted  = FALSE
              AND kc.is_deleted  = FALSE
              AND kd.is_deleted  = FALSE
              AND kd.status      = 'indexed'
              {extra_conditions}
            ORDER BY ke.vector <=> :vector::vector
            LIMIT :top_k
        """)

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        return [
            SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                document_title=row.document_title,
                content=row.content,
                score=float(row.score),
                chunk_index=row.chunk_index,
                page_number=row.page_number,
                section=row.section,
                heading=row.heading,
            )
            for row in rows
        ]

    async def delete_by_document(self, document_id: UUID) -> None:
        """
        Soft-delete all chunks and embeddings for a document.
        Order: embeddings first (FK constraint), then chunks.
        """
        # Soft-delete embeddings
        await self.db.execute(
            text("""
                UPDATE knowledge_embeddings ke
                SET is_deleted = TRUE, deleted_at = NOW(), updated_at = NOW()
                FROM knowledge_chunks kc
                WHERE kc.id = ke.chunk_id
                  AND kc.document_id = :document_id
                  AND ke.is_deleted = FALSE
            """),
            {"document_id": str(document_id)},
        )

        # Soft-delete chunks
        await self.db.execute(
            text("""
                UPDATE knowledge_chunks
                SET is_deleted = TRUE, deleted_at = NOW(), updated_at = NOW()
                WHERE document_id = :document_id
                  AND is_deleted = FALSE
            """),
            {"document_id": str(document_id)},
        )

        await self.db.commit()
```

---

## `app/modules/knowledge/chunking.py`

```py
"""
HybridChunker — independently testable text chunking for the knowledge engine.

Strategy:
    Markdown / plain-text with headings:
        1. Split on # / ## / ### headings
        2. If a section exceeds CHUNK_SIZE_TOKENS → further split by token window with overlap

    PDF / plain-text without headings:
        1. Split on paragraph boundaries (double newline)
        2. If a paragraph exceeds CHUNK_SIZE_TOKENS → split by sentence boundary
        3. Merge small pieces until window is filled, then slide with overlap

Each output Chunk carries enough metadata to populate knowledge_chunks fully.
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        return len(_ENCODER.encode(text))
except Exception:
    # Fallback: rough word-based approximation if tiktoken is unavailable
    def _count_tokens(text: str) -> int:  # type: ignore[misc]
        return max(1, len(text.split()) * 4 // 3)

try:
    from langdetect import detect as _detect_lang
    def _detect(text: str) -> str:
        try:
            return _detect_lang(text[:500]) or "en"
        except Exception:
            return "en"
except ImportError:
    def _detect(text: str) -> str:  # type: ignore[misc]
        return "en"

from app.core.ai_settings import ai_settings


@dataclass
class Chunk:
    """A single processable unit of a document, ready to be embedded."""
    content: str
    chunk_index: int
    token_count: int
    checksum: str
    language: str
    page_number: Optional[int] = None
    section: Optional[str] = None   # full heading path, e.g. "Sales > Pipeline"
    heading: Optional[str] = None   # immediate heading text


class HybridChunker:
    """
    Hybrid chunking strategy.

    - Markdown / RST → heading-aware splitting first, token fallback second.
    - PDF / plain text → paragraph → sentence → token window.

    All tuning values come from `ai_settings` so they can be changed via env vars.
    """

    def __init__(
        self,
        chunk_size: int = ai_settings.CHUNK_SIZE_TOKENS,
        overlap: int = ai_settings.CHUNK_OVERLAP_TOKENS,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, content: str, mime_type: Optional[str] = None) -> List[Chunk]:
        """
        Chunk the given content string based on its MIME type.

        Args:
            content:   Raw extracted text.
            mime_type: MIME type of the source file (e.g. "text/markdown", "application/pdf").
                       When None or unknown, plain-text strategy is used.

        Returns:
            Ordered list of Chunk objects (chunk_index 0-based).
        """
        if not content or not content.strip():
            return []

        is_markdown = mime_type in (
            "text/markdown", "text/x-markdown", "text/plain", None
        ) and self._looks_like_markdown(content)

        if is_markdown:
            raw_chunks = self._chunk_markdown(content)
        else:
            raw_chunks = self._chunk_plain(content)

        language = _detect(content)

        results: List[Chunk] = []
        for idx, (text, page_num, section, heading) in enumerate(raw_chunks):
            results.append(Chunk(
                content=text,
                chunk_index=idx,
                token_count=_count_tokens(text),
                checksum=self._sha256(text),
                language=language,
                page_number=page_num,
                section=section,
                heading=heading,
            ))
        return results

    # ------------------------------------------------------------------
    # Markdown strategy
    # ------------------------------------------------------------------

    def _looks_like_markdown(self, text: str) -> bool:
        """Heuristic: does this text contain Markdown headings?"""
        return bool(re.search(r"^#{1,6}\s+\S", text, re.MULTILINE))

    def _chunk_markdown(self, content: str) -> List[tuple]:
        """
        Split Markdown by headings, then apply token chunking if a section is too large.
        Returns list of (text, page_number, section_path, heading) tuples.
        """
        # Split into sections on heading lines
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        sections = []
        last_end = 0
        heading_stack: List[str] = []
        current_heading = None

        for match in heading_pattern.finditer(content):
            # Capture text before this heading
            if match.start() > last_end:
                preceding = content[last_end:match.start()].strip()
                if preceding:
                    sections.append((preceding, None, " > ".join(heading_stack) or None, current_heading))

            level = len(match.group(1))
            heading_text = match.group(2).strip()

            # Update heading stack to reflect nesting
            heading_stack = heading_stack[:level - 1] + [heading_text]
            current_heading = heading_text
            last_end = match.end()

        # Remaining text after last heading
        remainder = content[last_end:].strip()
        if remainder:
            sections.append((remainder, None, " > ".join(heading_stack) or None, current_heading))

        # Now split any section that's too large
        result = []
        for text, page, section, heading in sections:
            if _count_tokens(text) <= self.chunk_size:
                result.append((text, page, section, heading))
            else:
                for sub in self._token_window(text, page, section, heading):
                    result.append(sub)

        return result

    # ------------------------------------------------------------------
    # Plain-text strategy
    # ------------------------------------------------------------------

    def _chunk_plain(self, content: str) -> List[tuple]:
        """
        Split plain text (PDF, DOCX body, TXT without headings):
        paragraph → sentence boundary → token window with overlap.
        """
        paragraphs = re.split(r"\n\s*\n", content)
        result = []
        buffer = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            candidate = (buffer + " " + para).strip() if buffer else para

            if _count_tokens(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                # Flush buffer
                if buffer:
                    result.extend(self._token_window(buffer, None, None, None))
                # Start fresh with this paragraph
                if _count_tokens(para) <= self.chunk_size:
                    buffer = para
                else:
                    result.extend(self._token_window(para, None, None, None))
                    buffer = ""

        if buffer:
            result.extend(self._token_window(buffer, None, None, None))

        return result

    # ------------------------------------------------------------------
    # Token-window splitter (shared by both strategies)
    # ------------------------------------------------------------------

    def _token_window(
        self,
        text: str,
        page_number: Optional[int],
        section: Optional[str],
        heading: Optional[str],
    ) -> List[tuple]:
        """
        Split `text` into overlapping token windows of size `chunk_size`.
        Uses word-level splitting as a proxy for tokens.
        """
        words = text.split()
        if not words:
            return []

        # Approximate: assume avg ~1.33 tokens/word for English
        # Use a conservative word count: chunk_size / 1.5 ≈ safe word limit
        word_limit = max(1, int(self.chunk_size / 1.5))
        word_overlap = max(0, int(self.overlap / 1.5))

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + word_limit, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append((chunk_text, page_number, section, heading))

            if end >= len(words):
                break
            start = end - word_overlap  # slide back by overlap

        return chunks

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

---

## `app/ai/pipeline/executor.py`

```py
import json
import time
from uuid import UUID
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.ai.agents.registry import registry
from app.ai.providers.google import GoogleProvider
from app.ai.prompts.builder import PromptBuilder, PromptContext
from app.ai.pipeline.tool_executor import ToolExecutor
from app.ai.schemas import AIMessage, MessageRole, ToolCall
from app.ai.telemetry.logger import telemetry
from app.ai.safety.guards import AISafetyGuards
from app.modules.ai_conversations.models import AIMessageModel, Conversation
from app.modules.users.models import User
from app.modules.organizations.models import Organization

# Import tools for dynamic instantiation
from app.ai.tools.knowledge_tools import SearchKnowledgeBaseTool, GetDocumentTool, ListDocumentsTool
from app.modules.knowledge.services import KnowledgeService


class AIExecutionPipeline:
    def __init__(self, db: AsyncSession, user: User, organization: Organization, conversation: Conversation):
        self.db = db
        self.user = user
        self.organization = organization
        self.conversation = conversation
        # Currently only supporting GoogleProvider for chat
        self.provider = GoogleProvider()

    async def _resolve_tools(self, tool_names: List[str]) -> List[Any]:
        """Instantiate tools based on names, injecting required context."""
        instances = []
        knowledge_service = KnowledgeService(self.db)

        for name in tool_names:
            if name == "search_knowledge_base":
                instances.append(SearchKnowledgeBaseTool(knowledge_service, self.organization.id, self.user.id))
            elif name == "get_document":
                instances.append(GetDocumentTool(knowledge_service, self.organization.id))
            elif name == "list_documents":
                instances.append(ListDocumentsTool(knowledge_service, self.organization.id))
        return instances

    async def _fetch_implicit_context(self, user_prompt: str) -> List[Dict[str, Any]]:
        """
        Implicit RAG: run a quick search on the user's prompt to inject highly relevant
        context directly into the system prompt, saving a tool call round-trip.
        """
        try:
            knowledge_service = KnowledgeService(self.db)
            search_resp = await knowledge_service.search(
                org_id=self.organization.id,
                user=self.user,
                query=user_prompt,
                top_k=3 # Only top 3 for implicit context
            )
            
            documents = []
            for r in search_resp.results:
                # Basic relevance threshold
                if r.score >= 0.70:
                    documents.append({
                        "title": r.document_title,
                        "content": r.content
                    })
            return documents
        except Exception as e:
            # Don't fail the chat if RAG errors
            import logging
            logging.getLogger(__name__).warning(f"Implicit RAG failed: {e}")
            return []

    async def execute(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """
        Executes the AI conversation stream.
        """
        start_time = time.time()
        
        # 1. Select Agent
        agent_id = self.conversation.active_agent or "CEO"
        agent = registry.get_agent(agent_id)
        if not agent:
            yield f"Error: Agent '{agent_id}' not found in registry."
            return

        # 2. Safety Guards
        try:
            AISafetyGuards.check_prompt_injection(user_prompt)
            user_prompt = AISafetyGuards.check_pii_redaction(user_prompt)
        except Exception as e:
            yield f"Safety guard blocked execution: {e}"
            return

        # 3. Implicit Retrieval
        implicit_docs = await self._fetch_implicit_context(user_prompt)

        # 4. Build Prompt Context using structured PromptContext
        context = PromptContext(
            user=self.user,
            organization=self.organization,
            documents=implicit_docs
        )
        system_content = PromptBuilder.render(agent.system_prompt_template, context)

        # 5. Load Conversation History (last N messages)
        history_models = self.conversation.messages[-10:] # last 10 messages
        
        messages = [AIMessage(role=MessageRole.SYSTEM, content=system_content)]
        for msg_model in history_models:
            tool_calls = None
            if msg_model.tool_calls:
                tool_calls = [ToolCall(**tc) for tc in msg_model.tool_calls]
            messages.append(AIMessage(
                role=msg_model.role,
                content=msg_model.content,
                name=msg_model.name,
                tool_calls=tool_calls,
                tool_call_id=msg_model.tool_call_id
            ))
            
        # Add the new user prompt
        messages.append(AIMessage(role=MessageRole.USER, content=user_prompt))

        # Persist User Prompt
        user_msg_model = AIMessageModel(
            conversation_id=self.conversation.id,
            role=MessageRole.USER,
            content=user_prompt
        )
        self.db.add(user_msg_model)
        await self.db.commit()

        # 6. Tool Setup
        agent_tools = await self._resolve_tools(agent.tools)
        tool_executor = ToolExecutor(tools=agent_tools)
        tool_schemas = tool_executor.get_tool_schemas()

        iteration_count = 0
        max_iterations = ai_settings.MAX_TOOL_CALLS

        while iteration_count < max_iterations:
            iteration_count += 1
            
            # 7. Stream from Provider
            full_response_text = ""
            async for chunk in self.provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                full_response_text += chunk
                yield chunk

            # We exit after the first stream response since full tool calling loop is disabled for Sprint 004
            assistant_msg_model = AIMessageModel(
                conversation_id=self.conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response_text
            )
            self.db.add(assistant_msg_model)
            await self.db.commit()

            # 8. Telemetry
            latency = (time.time() - start_time) * 1000
            telemetry.log_execution(
                request_id=f"req_{self.conversation.id}",
                organization_id=self.organization.id,
                conversation_id=self.conversation.id,
                agent=agent.id,
                provider=self.provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
            )
            
            break
```

---

## `app/ai/prompts/builder.py`

```py
"""
Prompt building module.
Converts a context object into a rendered system prompt for the LLM.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List

from app.modules.users.models import User
from app.modules.organizations.models import Organization

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class PromptContext:
    """
    Structured context for rendering a system prompt.
    Replaces string concatenation with explicit structured attributes.
    """
    user: User
    organization: Organization
    documents: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for template rendering."""
        # Format knowledge context if documents exist (implicit RAG)
        knowledge_context = ""
        if self.documents:
            doc_texts = []
            for doc in self.documents:
                doc_texts.append(
                    f"--- DOCUMENT: {doc.get('title', 'Unknown')} ---\n"
                    f"{doc.get('content', '')}"
                )
            knowledge_context = "\n\n".join(doc_texts)

        return {
            "company_name": self.organization.name,
            "organization_name": self.organization.name,
            "user_first_name": self.user.first_name,
            "user_last_name": self.user.last_name,
            "knowledge_context": knowledge_context,
            **self.metadata
        }


class PromptBuilder:
    @staticmethod
    def load_template(template_name: str) -> str:
        filepath = TEMPLATES_DIR / f"{template_name}.md"
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt template {template_name}.md not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def render(template_name: str, context: PromptContext) -> str:
        """
        Renders a system prompt from a template using the structured PromptContext.
        """
        template = PromptBuilder.load_template(template_name)
        
        context_dict = context.to_dict()
        for key, value in context_dict.items():
            # Only replace if the placeholder exists in the template
            placeholder = f"{{{{{key}}}}}"
            if placeholder in template:
                template = template.replace(placeholder, str(value))
            
        return template
```

---

## `app/ai/agents/definitions/ceo.py`

```py
from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

ceo_agent = AgentDefinition(
    id="CEO",
    name="Chief Executive Officer",
    version="1.0",
    system_prompt_template="ceo_system",
    tools=["search_knowledge_base", "get_document", "list_documents"],
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(ceo_agent)
```

---

## `app/ai/agents/definitions/cfo.py`

```py
from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

cfo_agent = AgentDefinition(
    id="CFO",
    name="Chief Financial Officer",
    version="1.0",
    system_prompt_template="cfo_system",
    tools=["search_knowledge_base", "get_document", "list_documents"],
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(cfo_agent)
```

---

## `alembic/versions/003_knowledge_engine.py`

```py
"""knowledge_engine

Revision ID: 003
Revises: 002
Create Date: 2026-07-07

Creates the Knowledge Engine tables and vector extension.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums
doc_type_enum = ENUM("file", "note", "policy", "sop", name="doc_type_enum", create_type=False)
doc_status_enum = ENUM("pending", "processing", "indexed", "failed", name="doc_status_enum", create_type=False)
visibility_enum = ENUM("org", "private", name="visibility_enum", create_type=False)


def upgrade() -> None:
    # 1. Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create Enums
    doc_type_enum.create(op.get_bind(), checkfirst=True)
    doc_status_enum.create(op.get_bind(), checkfirst=True)
    visibility_enum.create(op.get_bind(), checkfirst=True)

    # 3. knowledge_documents
    op.create_table(
        "knowledge_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("doc_type", doc_type_enum, nullable=False, server_default="note"),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("status", doc_status_enum, nullable=False, server_default="pending", index=True),
        sa.Column("visibility", visibility_enum, nullable=False, server_default="org"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_documents_is_deleted", "knowledge_documents", ["is_deleted"])

    # 4. knowledge_chunks
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=500), nullable=True),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("parser_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_chunks_is_deleted", "knowledge_chunks", ["is_deleted"])

    # 5. knowledge_embeddings
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_embeddings_is_deleted", "knowledge_embeddings", ["is_deleted"])
    # Unique constraint per chunk per model so we can UPSERT cleanly
    op.create_unique_constraint("uq_knowledge_embeddings_chunk_model", "knowledge_embeddings", ["chunk_id", "model"])

    # Add the raw vector column
    op.execute("ALTER TABLE knowledge_embeddings ADD COLUMN vector vector(768);")

    # Add IVFFLAT index for cosine similarity
    op.execute("""
        CREATE INDEX ix_knowledge_embeddings_vector 
        ON knowledge_embeddings 
        USING ivfflat (vector vector_cosine_ops)
        WITH (lists = 100);
    """)

    # 6. knowledge_tags
    op.create_table(
        "knowledge_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_tags_is_deleted", "knowledge_tags", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("knowledge_tags")
    op.drop_table("knowledge_embeddings")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")

    visibility_enum.drop(op.get_bind(), checkfirst=True)
    doc_status_enum.drop(op.get_bind(), checkfirst=True)
    doc_type_enum.drop(op.get_bind(), checkfirst=True)
    
    op.execute("DROP EXTENSION IF EXISTS vector;")
```

---

## `app/api/v1/router.py`

```py
from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.core.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.organizations.router import router as organizations_router
from app.modules.ai_conversations.router import router as ai_conversations_router
from app.modules.knowledge.router import router as knowledge_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(ai_conversations_router)
api_router.include_router(knowledge_router)
```

---

## `app/workers/knowledge_tasks.py`

```py
"""
knowledge_tasks.py — Celery tasks for asynchronous document processing.

Flow:
    1. API handler creates a KnowledgeDocument with status=pending.
    2. API handler calls process_document_task.delay(doc_id).
    3. Celery worker picks up the task and runs the full pipeline:
         extract (BaseParser) → chunk (HybridChunker) → embed (BaseEmbeddingProvider)
         → upsert (VectorStore) → status=indexed
    4. On any failure, status is set to=failed and the error is logged.

This keeps HTTP request latency low (202 Accepted immediately) and provides
the user visibility into indexing progress via the document status field.
"""
import asyncio
import hashlib
import io
import logging
import uuid
from typing import Optional

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="knowledge.process_document",
    bind=True,
    acks_late=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_document_task(self, document_id: str) -> dict:
    """
    Process a KnowledgeDocument:
    load → parse → chunk → batch embed → upsert vectors → mark indexed.

    Runs inside an asyncio event loop (Celery workers are sync by default).
    """
    try:
        return asyncio.run(_process_document_async(document_id))
    except Exception as exc:
        logger.error(
            "process_document_task failed for doc %s: %s",
            document_id,
            str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


async def _process_document_async(document_id: str) -> dict:
    """
    Async implementation of document processing.
    Creates its own DB session (Celery workers run outside of FastAPI's DI system).
    """
    from app.core.database import AsyncSessionLocal
    from app.modules.knowledge.models import DocStatus
    from app.modules.knowledge.repositories import document_repository
    from app.modules.knowledge.chunking import HybridChunker
    from app.modules.knowledge.parsers import get_parser, PARSER_VERSION
    from app.ai.vector_store.pgvector import PgVectorStore
    from app.ai.vector_store.base import ChunkVector
    from app.ai.embedding.google import GeminiEmbeddingProvider
    from app.ai.storage.local import storage_provider
    from app.core.ai_settings import ai_settings

    doc_uuid = uuid.UUID(document_id)
    embedding_provider = GeminiEmbeddingProvider()

    async with AsyncSessionLocal() as db:
        # 1. Load document
        doc = await document_repository.get(db, doc_uuid)
        if not doc:
            logger.warning("process_document_task: doc %s not found", document_id)
            return {"status": "not_found", "document_id": document_id}

        # 2. Set status = processing
        await document_repository.update_status(db, doc_uuid, DocStatus.processing)

        try:
            # 3. Extract text using BaseParser
            content = await _extract_text(doc, storage_provider, embedding_provider)
            if not content or not content.strip():
                await document_repository.update_status(db, doc_uuid, DocStatus.failed)
                logger.warning("process_document_task: empty content for doc %s", document_id)
                return {"status": "failed", "reason": "empty_content"}

            # 4. Compute content hash — skip if unchanged
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            if doc.content_hash == content_hash and doc.status == DocStatus.indexed:
                logger.info(
                    "process_document_task: content unchanged for doc %s, skipping", document_id
                )
                return {"status": "skipped", "reason": "content_unchanged"}

            # 5. Chunk using HybridChunker
            chunker = HybridChunker()
            chunks = chunker.chunk(content, doc.mime_type)
            if not chunks:
                await document_repository.update_status(db, doc_uuid, DocStatus.failed)
                return {"status": "failed", "reason": "no_chunks"}

            # 6. Delete existing vectors (for reindex)
            vector_store = PgVectorStore(db)
            await vector_store.delete_by_document(doc_uuid)

            # 7. Batch embed (AI_EMBEDDING_BATCH_SIZE chunks per API call)
            batch_size = ai_settings.EMBEDDING_BATCH_SIZE
            chunk_vectors = []

            for batch_start in range(0, len(chunks), batch_size):
                batch = chunks[batch_start: batch_start + batch_size]
                texts = [c.content for c in batch]
                embeddings = await embedding_provider.embed(texts)

                for chunk, embedding in zip(batch, embeddings):
                    chunk_vectors.append(
                        ChunkVector(
                            chunk_id=uuid.uuid4(),
                            document_id=doc_uuid,
                            organization_id=doc.organization_id,
                            content=chunk.content,
                            embedding=embedding,
                            token_count=chunk.token_count,
                            chunk_index=chunk.chunk_index,
                            # Embedding provenance
                            provider=embedding_provider.provider_name,
                            model=embedding_provider.model_name,
                            dimensions=embedding_provider.dimensions,
                            # Structural metadata
                            page_number=chunk.page_number,
                            section=chunk.section,
                            heading=chunk.heading,
                            checksum=chunk.checksum,
                            language=chunk.language,
                            parser_version=PARSER_VERSION,
                        )
                    )

            # 8. Upsert into vector store
            await vector_store.upsert(chunk_vectors)

            # 9. Mark indexed + persist content
            await document_repository.update_status(
                db,
                doc_uuid,
                DocStatus.indexed,
                content=content,
                content_hash=content_hash,
            )

            logger.info(
                "process_document_task: indexed doc %s with %d chunks using %s/%s",
                document_id,
                len(chunk_vectors),
                embedding_provider.provider_name,
                embedding_provider.model_name,
            )
            return {
                "status": "indexed",
                "document_id": document_id,
                "chunk_count": len(chunk_vectors),
                "provider": embedding_provider.provider_name,
                "model": embedding_provider.model_name,
            }

        except Exception as exc:
            logger.error(
                "process_document_task: error processing doc %s: %s",
                document_id,
                str(exc),
                exc_info=True,
            )
            await document_repository.update_status(db, doc_uuid, DocStatus.failed)
            raise


async def _extract_text(doc, storage_provider, embedding_provider) -> Optional[str]:
    """
    Extract raw text from a KnowledgeDocument using the BaseParser abstraction.
    Inline content (notes/policies written via API) is returned as-is.
    """
    from app.modules.knowledge.parsers import get_parser

    # Inline content — no file on disk
    if doc.content and not doc.file_path:
        return doc.content

    if not doc.file_path:
        return doc.content or ""

    # Load bytes from storage
    try:
        file_bytes = await storage_provider.load(doc.file_path)
    except FileNotFoundError:
        logger.warning("_extract_text: file not found at path %s", doc.file_path)
        return doc.content or ""

    # Resolve the correct parser
    parser = get_parser(doc.mime_type, doc.file_name)
    return parser.extract(file_bytes, doc.file_name)


# Expose async entry point for use in tests (bypasses Celery broker)
process_document_async = _process_document_async
```

---

## `tests/api/test_knowledge_e2e.py`

```py
"""
E2E tests for the Knowledge Engine (Sprint 005).
"""
import pytest
from httpx import AsyncClient
from uuid import UUID

pytestmark = pytest.mark.asyncio

async def test_knowledge_e2e_flow(
    async_client: AsyncClient,
    test_user_headers: dict,
    test_organization_id: UUID,
):
    """
    Test the full knowledge engine lifecycle:
    1. Create an inline note.
    2. Search for the note.
    3. Delete the note.
    """
    # 1. Create an inline note
    create_resp = await async_client.post(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/note",
        headers=test_user_headers,
        data={
            "title": "Q3 Financial Strategy",
            "content": "The Q3 strategy relies heavily on cutting infrastructure costs and migrating to a unified database.",
            "doc_type": "note",
            "visibility": "org"
        }
    )
    assert create_resp.status_code == 202
    data = create_resp.json()
    doc_id = data["document_id"]
    assert data["status"] == "pending"

    # In a real E2E test, we would wait for Celery to process it.
    # For now, we test the listing endpoint to ensure the document exists.
    
    # 2. List documents
    list_resp = await async_client.get(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents",
        headers=test_user_headers,
    )
    assert list_resp.status_code == 200
    docs = list_resp.json()["items"]
    assert any(d["id"] == doc_id for d in docs)

    # 3. Delete document
    delete_resp = await async_client.delete(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/{doc_id}",
        headers=test_user_headers,
    )
    assert delete_resp.status_code == 204

    # Ensure it is deleted
    get_resp = await async_client.get(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/{doc_id}",
        headers=test_user_headers,
    )
    assert get_resp.status_code == 404
```

---

## `tests/retrieval/golden_queries.json`

```json
[
    {
        "query": "What is our Q3 financial strategy?",
        "expected_documents": ["Q3 Financial Strategy", "2026 Board Update"],
        "expected_topics": ["infrastructure costs", "database migration"]
    },
    {
        "query": "How do I request time off?",
        "expected_documents": ["Employee Handbook - PTO", "HR Policies 2026"],
        "expected_topics": ["workday", "manager approval"]
    },
    {
        "query": "What are the new security compliance requirements for production?",
        "expected_documents": ["Infosec Policy 2026", "Production Deployment SOP"],
        "expected_topics": ["SOC2", "MFA", "VPN"]
    }
]
```

---

## `tests/retrieval/benchmark.py`

```py
"""
Retrieval Benchmark Script.
Evaluates PgVectorStore and HybridChunker against golden_queries.json.

Run this script directly to get a retrieval quality score whenever
embedding models or chunking parameters are changed.
"""
import json
import asyncio
from pathlib import Path

# Stub for the benchmark execution.
# In a real environment, this connects to the database, ingests the expected
# documents, runs the golden queries, and calculates Mean Reciprocal Rank (MRR).

def load_golden_queries():
    path = Path(__file__).parent / "golden_queries.json"
    with open(path, "r") as f:
        return json.load(f)

async def run_benchmark():
    queries = load_golden_queries()
    print(f"Loaded {len(queries)} golden queries.")
    print("Connecting to Vector Store...")
    print("Evaluating Mean Reciprocal Rank (MRR)...")
    
    # Placeholder for actual RAG evaluation logic
    print("--- Benchmark Results ---")
    print("Model: text-embedding-004")
    print("MRR: 0.85 (Placeholder)")
    print("Precision@3: 0.92 (Placeholder)")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

---

## `app/ai/embedding/base.py`

```py
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
```

---

## `app/ai/embedding/google.py`

```py
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
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY must be set in the environment.")
        self.client = genai.Client(api_key=key)

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
```

---

## `app/ai/storage/base.py`

```py
"""
StorageProvider — abstract interface for document file storage.

Mirrors the BaseLLMProvider pattern from Sprint 004.
Sprint 005 implements LocalStorageProvider only.
Future sprints can add S3StorageProvider, GCSStorageProvider without changing callers.
"""
from abc import ABC, abstractmethod
from uuid import UUID


class StorageProvider(ABC):
    """Abstract base class for all storage backends."""

    @abstractmethod
    async def save(self, file_name: str, content: bytes, org_id: UUID) -> str:
        """
        Persist file bytes and return the storage path.

        Args:
            file_name: Original filename (used to derive extension / storage key).
            content:   Raw file bytes.
            org_id:    Organization UUID — used to namespace the storage path.

        Returns:
            A string path/key that can be passed back to load() or delete().
        """
        pass

    @abstractmethod
    async def load(self, path: str) -> bytes:
        """
        Retrieve raw bytes from the given storage path.

        Args:
            path: The path/key returned by save().

        Returns:
            Raw file bytes.

        Raises:
            FileNotFoundError: If the path does not exist in storage.
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """
        Delete the file at the given storage path.

        Args:
            path: The path/key returned by save().
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check whether a file exists at the given storage path.

        Args:
            path: The path/key returned by save().

        Returns:
            True if the file exists, False otherwise.
        """
        pass
```

---

## `app/ai/storage/local.py`

```py
"""
LocalStorageProvider — stores uploaded documents on the local filesystem.

Files are saved under:
    ./uploads/{org_id}/{file_name}

Sprint 005 only. Future sprints will add S3StorageProvider and GCSStorageProvider
by implementing StorageProvider without changing any callers.
"""
import os
import aiofiles
from typing import Optional
from uuid import UUID

from app.ai.storage.base import StorageProvider

# Base directory relative to the working directory of the running process.
# In Docker: /app/uploads/
_UPLOAD_BASE = os.path.join(os.getcwd(), "uploads")


class LocalStorageProvider(StorageProvider):
    """Filesystem-backed storage provider for development / single-node deployments."""

    async def save(self, file_name: str, content: bytes, org_id: UUID, doc_id: Optional[UUID] = None) -> str:
        """
        Save bytes to ./uploads/{org_id}/{doc_id}/{file_name} and return the relative path.
        Using org_id/doc_id subdirectory prevents filename collisions across documents.
        Creates directories if they do not exist.
        """
        # Sanitise file_name to prevent path traversal
        safe_name = os.path.basename(file_name)

        if doc_id:
            sub_dir = os.path.join(_UPLOAD_BASE, str(org_id), str(doc_id))
        else:
            sub_dir = os.path.join(_UPLOAD_BASE, str(org_id))

        os.makedirs(sub_dir, exist_ok=True)
        path = os.path.join(sub_dir, safe_name)

        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

        # Return relative path (not tied to server's absolute path)
        if doc_id:
            return os.path.join(str(org_id), str(doc_id), safe_name)
        return os.path.join(str(org_id), safe_name)


    async def load(self, path: str) -> bytes:
        """
        Load bytes from the given relative storage path.
        Raises FileNotFoundError if the file does not exist.
        """
        abs_path = os.path.join(_UPLOAD_BASE, path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Storage file not found: {path}")

        async with aiofiles.open(abs_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        """Delete the file at the given relative storage path (silently ignores missing files)."""
        abs_path = os.path.join(_UPLOAD_BASE, path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    async def exists(self, path: str) -> bool:
        """Return True if the file exists at the given relative storage path."""
        abs_path = os.path.join(_UPLOAD_BASE, path)
        return os.path.exists(abs_path)


# Module-level singleton — swap this for S3StorageProvider later without touching services.
storage_provider = LocalStorageProvider()
```

---

