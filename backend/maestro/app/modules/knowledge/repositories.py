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
