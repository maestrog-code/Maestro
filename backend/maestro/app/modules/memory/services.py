"""
Services for the Memory System.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.modules.memory.models import AgentMemory, MemoryEmbedding, MemoryStatus, MemorySource, MemoryType
from app.modules.memory.repositories import MemoryRepository, MemoryEmbeddingRepository
from app.ai.embedding.base import BaseEmbeddingProvider
from app.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, db: AsyncSession, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        """
        embedding_provider is Optional to support decay tasks that never need to embed.
        Any code path that calls add_memory() or search() MUST inject a real provider —
        both methods raise RuntimeError immediately if the provider is missing.
        """
        self.db = db
        self.repo = MemoryRepository(db)
        self.embedding_repo = MemoryEmbeddingRepository(db)
        self.embedding_provider = embedding_provider

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _write_vector(self, embedding_id: UUID, vector: List[float]) -> None:
        """
        Writes a pgvector value using a correctly-formed parameterized SQL cast.

        SQLAlchemy binds :vector before Postgres parses casts, so we use the
        parenthesised form `(:vector)::vector`. The non-parenthesised form
        `:vector::vector` is incorrectly parsed as a parameter named `vector::vector`
        by most drivers and will raise a binding error at runtime.
        """
        vector_str = f"[{','.join(map(str, vector))}]"
        await self.db.execute(
            text("UPDATE memory_embeddings SET vector = (:vector)::vector WHERE id = :id"),
            {"vector": vector_str, "id": embedding_id}
        )
        # Flush explicitly so the UPDATE is visible within the session before commit.
        await self.db.flush()

    async def _create_embedding(self, memory_id: UUID, vector: List[float]) -> MemoryEmbedding:
        """
        Creates a MemoryEmbedding row and writes the vector.

        Prevents duplicate active embeddings by soft-deleting any existing active
        embeddings for this memory before inserting. This is a defensive guard —
        a unique partial index in the schema is the primary enforcement mechanism.
        """
        if len(vector) != ai_settings.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Embedding dimension mismatch: expected {ai_settings.EMBEDDING_DIMENSIONS}, "
                f"but got {len(vector)}."
            )

        # Guard: remove any leftover active embeddings before adding a new one.
        await self.embedding_repo.delete_for_memory(memory_id)

        embedding = MemoryEmbedding(
            memory_id=memory_id,
            provider=self.embedding_provider.__class__.__name__,
            model=ai_settings.EMBEDDING_MODEL,
            dimensions=ai_settings.EMBEDDING_DIMENSIONS
        )
        embedding = await self.embedding_repo.create(embedding)
        await self._write_vector(embedding.id, vector)
        return embedding

    async def _rewrite_merged_content(
        self,
        llm_provider: Optional[BaseLLMProvider],
        existing_content: str,
        new_content: str,
        organization_id: UUID,
        memory_id: UUID,
    ) -> str:
        """
        Asks the LLM to produce one canonical fact from two similar memories.
        Falls back to the newer content when no LLM is available (deterministic path).

        NOTE: Metadata (memory_type, source, agent_id, user_id) is intentionally
        preserved from the existing memory. Only the text content is consolidated.
        This is a deliberate design choice: metadata reflects the original provenance
        of the memory, which should not be overwritten by a newer observation.
        """
        if llm_provider is None:
            logger.info(
                "Merge rewrite: no LLM provider — replacing with newer content. "
                "organization_id=%s memory_id=%s",
                organization_id, memory_id
            )
            return new_content

        from app.ai.schemas import MessageRole, AIMessage
        system_prompt = (
            "You are a memory consolidation assistant. "
            "Two related facts have been identified as duplicates. "
            "Rewrite them as a single, clear, concise canonical memory. "
            "Preserve all unique details from both. Return ONLY the consolidated text — no preamble."
        )
        messages = [
            AIMessage(role=MessageRole.SYSTEM, content=system_prompt),
            AIMessage(role=MessageRole.USER, content=(
                f"MEMORY 1:\n{existing_content}\n\n"
                f"MEMORY 2:\n{new_content}"
            ))
        ]
        try:
            response = await llm_provider.generate(messages=messages, temperature=0.2)
            return response.content.strip()
        except Exception as e:
            logger.exception(
                "LLM merge rewrite failed, falling back to concatenated content. "
                "organization_id=%s memory_id=%s error=%s",
                organization_id, memory_id, e
            )
            return f"{existing_content}\n{new_content}"

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def add_memory(
        self,
        organization_id: UUID,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        source: MemorySource = MemorySource.SYSTEM,
        importance: float = 0.5,
        confidence: float = 0.8,
        user_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        is_async_extraction: bool = False
    ) -> AgentMemory:
        """
        Embeds content, checks for conflicts, then creates or updates a memory.

        is_async_extraction=True  → LLM conflict resolution (intelligent, runs in Celery).
        is_async_extraction=False → deterministic threshold-based resolution (fast, for
                                    explicit API / tool calls).

        Raises:
            RuntimeError: if embedding_provider is missing, or if is_async_extraction=True
                          but no llm_provider was supplied.
        """
        if self.embedding_provider is None:
            raise RuntimeError(
                "MemoryService.add_memory requires an embedding_provider. "
                "Inject one when constructing MemoryService."
            )
        if is_async_extraction and llm_provider is None:
            raise RuntimeError(
                "is_async_extraction=True requires an llm_provider. "
                "Pass the LLM provider to add_memory() when calling from async extraction."
            )

        try:
            # 1. Generate embedding for incoming content
            vectors = await self.embedding_provider.embed([content])
            if not vectors:
                raise ValueError("Embedding provider returned an empty result for the given content.")
            vector = vectors[0]

            # 2. Search for similar existing memories
            similar_memories = await self.embedding_repo.vector_search(
                organization_id=organization_id,
                query_vector=vector,
                top_k=5,
                similarity_threshold=ai_settings.MEMORY_CONFLICT_THRESHOLD
            )

            from app.modules.memory.conflict import ConflictResolutionService, ResolutionDecision
            from app.modules.memory.policy import MemoryPolicy

            decision = ResolutionDecision.NEW
            target_memory = None

            if similar_memories:
                top_mem, top_sim = similar_memories[0]

                if not MemoryPolicy.requires_llm_resolution(is_async_extraction):
                    # Deterministic path — fast, no LLM, used for explicit API calls
                    if top_sim >= ai_settings.MEMORY_MERGE_THRESHOLD:
                        decision = ResolutionDecision.MERGE
                        target_memory = top_mem
                else:
                    # LLM-based resolution — used for async extraction
                    conflict_svc = ConflictResolutionService(llm_provider)
                    decision = await conflict_svc.resolve(content, top_mem)
                    target_memory = top_mem

            # 3. Apply the decision
            if decision in (ResolutionDecision.MERGE, ResolutionDecision.SUPERSEDE) and target_memory:
                original_updated_at = target_memory.updated_at

                # Lock the row to prevent concurrent merge/supersede races
                target_memory = await self.repo.get_for_update(organization_id, target_memory.id)

                # OCC Check: verify memory is still ACTIVE and hasn't been modified
                if (not target_memory or
                    target_memory.status != MemoryStatus.ACTIVE or
                    target_memory.updated_at != original_updated_at):
                    logger.warning(
                        "TOCTOU prevented: Memory %s was modified during LLM resolution. Falling back to NEW.",
                        target_memory.id if target_memory else "None"
                    )
                    # If it was deleted, modified, or missing, fall back to creating a new memory
                    decision = ResolutionDecision.NEW
                    target_memory = None

            if decision == ResolutionDecision.IGNORE:
                logger.info(
                    "Memory ignored during conflict resolution. "
                    "organization_id=%s existing_memory_id=%s",
                    organization_id, target_memory.id if target_memory else None
                )
                return target_memory or similar_memories[0][0]

            elif decision == ResolutionDecision.UNCERTAIN:
                logger.info(
                    "Memory conflict uncertain — creating as new with reduced confidence. "
                    "organization_id=%s",
                    organization_id
                )
                confidence *= ai_settings.MEMORY_UNCERTAIN_CONFIDENCE_PENALTY
                # Fall through to create a new memory

            elif decision == ResolutionDecision.MERGE and target_memory:
                merged_content = await self._rewrite_merged_content(
                    llm_provider,
                    target_memory.content,
                    content,
                    organization_id,
                    target_memory.id,
                )
                target_memory.content = merged_content
                target_memory.confidence_score = max(target_memory.confidence_score, confidence)
                target_memory.importance_score = max(target_memory.importance_score, importance)
                # NOTE: memory_type, source, agent_id, user_id are intentionally
                # preserved from the existing memory. See _rewrite_merged_content docstring.

                # Regenerate embedding — vector must always match current content.
                # _create_embedding calls delete_for_memory first as a guard.
                merged_vectors = await self.embedding_provider.embed([merged_content])
                if merged_vectors:
                    await self._create_embedding(target_memory.id, merged_vectors[0])

                await self.repo.record_access(target_memory, context="Merged with new similar memory")
                await self.repo.update(target_memory)
                await self.db.commit()
                return target_memory

            elif decision == ResolutionDecision.SUPERSEDE and target_memory:
                # Mark old memory superseded; soft-delete its embeddings (they are stale).
                target_memory.status = MemoryStatus.SUPERSEDED
                await self.embedding_repo.delete_for_memory(target_memory.id)
                await self.repo.update(target_memory)
                logger.info(
                    "Memory superseded. organization_id=%s superseded_memory_id=%s",
                    organization_id, target_memory.id
                )
                # Fall through to create a new memory

            # 4. Create new memory + embedding
            memory = AgentMemory(
                organization_id=organization_id,
                user_id=user_id,
                agent_id=agent_id,
                content=content,
                memory_type=memory_type,
                source=source,
                importance_score=importance,
                confidence_score=confidence
            )
            memory = await self.repo.create(memory)
            await self._create_embedding(memory.id, vector)
            await self.db.commit()
            return memory

        except Exception:
            await self.db.rollback()
            raise

    async def archive_memory(self, organization_id: UUID, memory_id: UUID) -> bool:
        """Soft-archives a memory by setting its status to ARCHIVED."""
        try:
            memory = await self.repo.get(organization_id, memory_id)
            if not memory:
                return False

            memory.status = MemoryStatus.ARCHIVED
            await self.repo.update(memory)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            raise

    def _calculate_score(self, memory: AgentMemory, similarity: float) -> float:
        """
        Weighted ranking formula:
          score = (w_sim   × similarity)
                + (w_imp   × importance_score)
                + (w_conf  × confidence_score)
                + (w_rec   × recency)
                + (w_acc   × access_frequency)

        Recency is calculated from `last_accessed` (not `created_at`) so that
        frequently-used memories are not penalised simply because they are old.
        """
        days_since_access = (datetime.now(timezone.utc) - memory.last_accessed).days
        recency = max(0.0, 1.0 - (days_since_access / ai_settings.MEMORY_RECENCY_WINDOW_DAYS))
        access_freq = min(
            1.0,
            memory.access_count / ai_settings.MEMORY_MAX_ACCESS_NORMALIZATION
        )

        return (
            (ai_settings.MEMORY_SIMILARITY_WEIGHT  * similarity)
            + (ai_settings.MEMORY_IMPORTANCE_WEIGHT * memory.importance_score)
            + (ai_settings.MEMORY_CONFIDENCE_WEIGHT * memory.confidence_score)
            + (ai_settings.MEMORY_RECENCY_WEIGHT    * recency)
            + (ai_settings.MEMORY_ACCESS_WEIGHT     * access_freq)
        )

    async def search(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = ai_settings.MEMORY_RETRIEVAL_LIMIT,
        context: str = "rag_search"
    ) -> List[AgentMemory]:
        """
        Embeds the query, fetches a candidate pool via vector search (ACTIVE memories only),
        applies weighted ranking, logs access, and returns the top K results.
        """
        if self.embedding_provider is None:
            raise RuntimeError(
                "MemoryService.search requires an embedding_provider. "
                "Inject one when constructing MemoryService."
            )

        vectors = await self.embedding_provider.embed([query])
        if not vectors:
            return []

        pool_size = max(top_k * 3, ai_settings.MEMORY_SEARCH_POOL_SIZE)
        candidates = await self.embedding_repo.vector_search(
            organization_id=organization_id,
            query_vector=vectors[0],
            top_k=pool_size,
            similarity_threshold=ai_settings.MEMORY_RETRIEVAL_THRESHOLD
        )

        if not candidates:
            return []

        ranked = sorted(
            ((self._calculate_score(mem, sim), mem) for mem, sim in candidates),
            key=lambda x: x[0],
            reverse=True
        )

        top_memories = [mem for _, mem in ranked[:top_k]]

        for mem in top_memories:
            await self.repo.record_access(mem, context=context)

        await self.db.commit()
        return top_memories
