"""
Repositories for the Memory System.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.memory.models import (
    AgentMemory,
    MemoryEmbedding,
    MemoryAccessLog,
    MemoryStatus
)


class MemoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, organization_id: UUID, memory_id: UUID) -> Optional[AgentMemory]:
        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.id == memory_id,
                AgentMemory.organization_id == organization_id,
                AgentMemory.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[AgentMemory], int]:
        base_stmt = select(AgentMemory).where(
            AgentMemory.organization_id == organization_id,
            AgentMemory.is_deleted == False
        )
        
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.db.execute(count_stmt)
        total = total.scalar() or 0
        
        stmt = (
            base_stmt
            .order_by(AgentMemory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, memory: AgentMemory) -> AgentMemory:
        self.db.add(memory)
        await self.db.flush()
        return memory

    async def update(self, memory: AgentMemory) -> AgentMemory:
        # Changes are flushed implicitly or explicitly before commit
        return memory

    async def record_access(self, memory: AgentMemory, context: str) -> None:
        """Increments access count and logs the access."""
        memory.access_count += 1
        memory.last_accessed = func.now()
        
        log = MemoryAccessLog(
            memory_id=memory.id,
            organization_id=memory.organization_id,
            context=context
        )
        self.db.add(log)


class MemoryEmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, embedding: MemoryEmbedding) -> MemoryEmbedding:
        self.db.add(embedding)
        await self.db.flush()
        return embedding

    async def delete_for_memory(self, memory_id: UUID) -> None:
        stmt = (
            update(MemoryEmbedding)
            .where(MemoryEmbedding.memory_id == memory_id)
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.execute(stmt)

    async def vector_search(
        self,
        organization_id: UUID,
        query_vector: List[float],
        top_k: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[tuple[AgentMemory, float]]:
        """
        Performs a cosine similarity search joining embeddings to memories.
        Strictly filters by organization_id.
        """
        # Convert vector to string representation for pgvector
        vector_str = f"[{','.join(map(str, query_vector))}]"
        
        # Calculate cosine distance (<=>). Cosine similarity = 1 - cosine_distance.
        distance = MemoryEmbedding.vector.op("<=>")(vector_str)
        similarity = (1 - distance).label("similarity")

        stmt = (
            select(AgentMemory, similarity)
            .join(MemoryEmbedding, AgentMemory.id == MemoryEmbedding.memory_id)
            .where(
                AgentMemory.organization_id == organization_id,
                AgentMemory.is_deleted == False,
                AgentMemory.status == MemoryStatus.ACTIVE,
                MemoryEmbedding.is_deleted == False
            )
            # Filter by threshold (using distance for performance)
            .where(distance <= (1.0 - similarity_threshold))
            # Get closest vectors (smallest distance)
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        return [(mem, sim) for mem, sim in result.all()]
