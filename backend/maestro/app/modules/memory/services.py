"""
Services for the Memory System.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.modules.memory.models import AgentMemory, MemoryEmbedding, MemoryStatus, MemorySource, MemoryType
from app.modules.memory.repositories import MemoryRepository, MemoryEmbeddingRepository
from app.ai.embedding.base import BaseEmbeddingProvider
from app.ai.embedding.google import GeminiEmbeddingProvider

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, db: AsyncSession, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self.db = db
        self.repo = MemoryRepository(db)
        self.embedding_repo = MemoryEmbeddingRepository(db)
        # Default to Gemini, but allow injection for tests/swaps
        self.embedding_provider = embedding_provider or GeminiEmbeddingProvider()

    async def add_memory(
        self,
        organization_id: UUID,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        source: MemorySource = MemorySource.SYSTEM,
        importance: float = 0.5,
        confidence: float = 0.8,
        user_id: Optional[UUID] = None,
        agent_id: Optional[str] = None
    ) -> AgentMemory:
        """
        Extracts embedding, checks for duplicates, and creates or updates a memory.
        """
        # 1. Generate embedding
        vectors = await self.embedding_provider.embed([content])
        if not vectors:
            raise ValueError("Failed to generate embedding for memory.")
        vector = vectors[0]

        # 2. Deduplication check (find very similar memories)
        similar_memories = await self.embedding_repo.vector_search(
            organization_id=organization_id,
            query_vector=vector,
            top_k=1,
            similarity_threshold=0.92  # High threshold for deduplication
        )

        if similar_memories:
            existing_mem, sim = similar_memories[0]
            # If extremely similar, just update confidence/importance and mark accessed
            existing_mem.confidence_score = max(existing_mem.confidence_score, confidence)
            existing_mem.importance_score = max(existing_mem.importance_score, importance)
            await self.repo.record_access(existing_mem, context=f"Deduplication merge (sim: {sim:.2f})")
            await self.repo.update(existing_mem)
            await self.db.commit()
            return existing_mem

        # 3. Create new memory
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

        # 4. Save embedding
        embedding = MemoryEmbedding(
            memory_id=memory.id,
            provider=self.embedding_provider.__class__.__name__,
            model=ai_settings.EMBEDDING_MODEL,
            dimensions=ai_settings.EMBEDDING_DIMENSIONS
        )
        # We must insert the vector via raw SQL or let SQLAlchemy handle it if we configured the TypeDecorator properly.
        # Since we added it via raw SQL in alembic without a model property, we do an explicit UPDATE here.
        embedding = await self.embedding_repo.create(embedding)
        
        # Insert vector via raw sql to bypass SQLAlchemy type limitations
        vector_str = f"[{','.join(map(str, vector))}]"
        await self.db.execute(
            f"UPDATE memory_embeddings SET vector = '{vector_str}' WHERE id = '{embedding.id}'"
        )
        
        await self.db.commit()
        return memory

    async def archive_memory(self, organization_id: UUID, memory_id: UUID) -> bool:
        """Soft deletes / archives a memory."""
        memory = await self.repo.get(organization_id, memory_id)
        if not memory:
            return False
            
        memory.status = MemoryStatus.ARCHIVED
        await self.repo.update(memory)
        await self.db.commit()
        return True

    def _calculate_score(self, memory: AgentMemory, similarity: float) -> float:
        """
        Applies the CTO's weighted ranking formula.
        Score = (w1 × similarity) + (w2 × importance) + (w3 × confidence) + (w4 × recency) + (w5 × access_frequency)
        """
        # Normalize recency (0 to 1 based on days old, where 0 days = 1.0, 30+ days = 0.0)
        days_old = (datetime.now(timezone.utc) - memory.created_at).days
        recency = max(0.0, 1.0 - (days_old / 30.0))
        
        # Normalize access frequency (cap at 10 accesses for max score)
        access_freq = min(1.0, memory.access_count / 10.0)

        score = (
            (ai_settings.MEMORY_SIMILARITY_WEIGHT * similarity) +
            (ai_settings.MEMORY_IMPORTANCE_WEIGHT * memory.importance_score) +
            (ai_settings.MEMORY_CONFIDENCE_WEIGHT * memory.confidence_score) +
            (ai_settings.MEMORY_RECENCY_WEIGHT * recency) +
            (ai_settings.MEMORY_ACCESS_WEIGHT * access_freq)
        )
        return score

    async def search(
        self,
        organization_id: UUID,
        query: str,
        top_k: int = ai_settings.MEMORY_RETRIEVAL_LIMIT,
        context: str = "rag_search"
    ) -> List[AgentMemory]:
        """
        Searches memories, applies weighted ranking, logs access, and returns top K.
        """
        # 1. Embed query
        vectors = await self.embedding_provider.embed([query])
        if not vectors:
            return []
        
        # 2. Vector search (fetch a larger pool to rank)
        pool_size = max(top_k * 3, 30)
        candidates = await self.embedding_repo.vector_search(
            organization_id=organization_id,
            query_vector=vectors[0],
            top_k=pool_size,
            similarity_threshold=0.6  # Base threshold
        )

        if not candidates:
            return []

        # 3. Apply ranking formula
        ranked_candidates = []
        for mem, sim in candidates:
            final_score = self._calculate_score(mem, sim)
            ranked_candidates.append((final_score, mem))
            
        # 4. Sort by final score descending
        ranked_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # 5. Take top K and record access
        top_memories = [mem for score, mem in ranked_candidates[:top_k]]
        
        for mem in top_memories:
            await self.repo.record_access(mem, context=context)
            
        await self.db.commit()
        return top_memories
