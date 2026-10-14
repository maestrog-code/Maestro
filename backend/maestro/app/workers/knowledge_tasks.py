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
