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
