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
