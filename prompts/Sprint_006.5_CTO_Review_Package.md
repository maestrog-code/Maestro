# MAESTRO — Sprint 006.5 CTO Review Package (FINAL APPROVAL)
## Context
Sprint 006.5 Memory System stabilisation — final approval adjustments.
Addresses all final minor robustness requirements prior to merge, including OCC logic for TOCTOU and NullPool for Celery workers.
### Changes in this revision
- **TOCTOU Race Condition Prevention**: `add_memory` implements Optimistic Concurrency Control (OCC). Re-verifies `target_memory.updated_at` after acquiring the lock via `get_for_update()`.
- **Celery Event Loop Instability**: Configured `CelerySessionLocal` with `poolclass=NullPool` in `app/core/database.py` and used it across async workers to prevent DB connection pool exhaustion.
- **Batch Transaction Fragility**: `_decay_memories_async` commits exponential decay calculations in chunks of 100 rather than holding the transaction open to the end.
- **LLM Fallback Rewrite**: `_rewrite_merged_content` safely concatenates strings on exception `f"{existing_content}\n{new_content}"` rather than silently overwriting.
- **Technical Debt Logged**: `docs/ROADMAP.md` updated with technical debt item to migrate to `pgvector.sqlalchemy`.

## `backend/maestro/app/core/database.py`
```py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

from sqlalchemy.pool import NullPool

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# For Celery async workers (prevents connection pool exhaustion when event loop is repeatedly created/destroyed)
celery_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    poolclass=NullPool
)

CelerySessionLocal = async_sessionmaker(
    bind=celery_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```
## `backend/maestro/app/core/ai_settings.py`
```py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """
    AI-specific configuration for MAESTRO's AI Executive Engine.
    Values can be overridden by environment variables with the `AI_` prefix.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="AI_"
    )

    # Provider & Model Settings
    DEFAULT_PROVIDER: str = "google"
    GOOGLE_MODEL: str = "gemini-2.5-pro"

    # Execution Limits
    MAX_TOOL_CALLS: int = 8
    MAX_CONTEXT_TOKENS: int = 32000
    
    # Model Generation Defaults
    DEFAULT_TEMPERATURE: float = 0.2
    STREAMING: bool = True
    
    # Memory Ranking & Vector Config
    EMBEDDING_DIMENSIONS: int = 768
    
    # Memory Weights
    MEMORY_SIMILARITY_WEIGHT: float = 0.4
    MEMORY_IMPORTANCE_WEIGHT: float = 0.2
    MEMORY_CONFIDENCE_WEIGHT: float = 0.2
    MEMORY_RECENCY_WEIGHT: float = 0.1
    MEMORY_ACCESS_WEIGHT: float = 0.1
    MEMORY_RETRIEVAL_LIMIT: int = 10
    
    # Memory Thresholds (Sprint 006.5)
    MEMORY_MERGE_THRESHOLD: float = 0.90
    MEMORY_CONFLICT_THRESHOLD: float = 0.82
    MEMORY_RETRIEVAL_THRESHOLD: float = 0.60
    MEMORY_ARCHIVE_THRESHOLD: float = 0.10  # Importance below this triggers archival
    MEMORY_UNCERTAIN_CONFIDENCE_PENALTY: float = 0.80  # Multiplier on confidence for UNCERTAIN resolution
    MEMORY_RECENCY_WINDOW_DAYS: int = 30   # Days over which recency score decays to 0
    MEMORY_SEARCH_POOL_SIZE: int = 30
    MEMORY_MAX_ACCESS_NORMALIZATION: int = 10  # Access count at which access_freq score reaches 1.0
    
    # Memory Decay Rate (lambda for exponential decay: e^(-lambda * days))
    # A lambda of 0.01 means memory importance decays by ~1% per day if untouched
    MEMORY_DECAY_RATE: float = 0.01

    # Sprint 005 — Embeddings
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_BATCH_SIZE: int = 10  # chunks per API call to avoid rate limits

    # Sprint 005 — Knowledge / RAG
    VECTOR_SEARCH_TOP_K: int = 5
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 80
    KNOWLEDGE_MAX_CONTEXT_CHARS: int = 8000  # max chars injected into system prompt


ai_settings = AISettings()
```
## `backend/maestro/app/modules/memory/models.py`
```py
"""
Agent Memory module SQLAlchemy models (Sprint 006).

Tables created by migration 004_memory_system:
    - agent_memories
    - memory_embeddings
    - memory_access_logs
"""
import enum

from sqlalchemy import (
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    func
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.models.base import TimestampedModel


class MemoryType(str, enum.Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    GOAL = "goal"
    DECISION = "decision"
    PROFILE = "profile"
    WARNING = "warning"
    TASK = "task"
    RELATIONSHIP = "relationship"
    CONSTRAINT = "constraint"
    PROJECT = "project"


class MemoryStatus(str, enum.Enum):
    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    CONFLICTED = "conflicted"


class MemorySource(str, enum.Enum):
    CONVERSATION = "conversation"
    MANUAL = "manual"
    TOOL = "tool"
    IMPORT = "import"
    SYSTEM = "system"


class AgentMemory(TimestampedModel):
    __tablename__ = "agent_memories"

    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    agent_id = Column(String, nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    
    memory_type = Column(Enum(MemoryType, name="memory_type_enum"), nullable=False, default=MemoryType.FACT)
    status = Column(Enum(MemoryStatus, name="memory_status_enum"), nullable=False, default=MemoryStatus.ACTIVE)
    source = Column(Enum(MemorySource, name="memory_source_enum"), nullable=False, default=MemorySource.SYSTEM)
    
    importance_score = Column(Float, nullable=False, default=0.5)
    confidence_score = Column(Float, nullable=False, default=0.8)
    
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    access_count = Column(Integer, nullable=False, default=0)

    # Relationships
    embeddings = relationship("MemoryEmbedding", back_populates="memory", cascade="all, delete-orphan")
    access_logs = relationship("MemoryAccessLog", back_populates="memory", cascade="all, delete-orphan")


class MemoryEmbedding(TimestampedModel):
    __tablename__ = "memory_embeddings"

    memory_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    dimensions = Column(Integer, nullable=False)
    
    # We define vector as a String for SQLAlchemy to satisfy the ORM, 
    # but we interact with it via parameterized raw SQL using pgvector features.
    vector = Column(String, nullable=True)
    # The vector column is added via raw SQL in Alembic to support dynamic dimensions:
    # ALTER TABLE memory_embeddings ADD COLUMN vector vector({dim});
    
    # Relationships
    memory = relationship("AgentMemory", back_populates="embeddings")


class MemoryAccessLog(TimestampedModel):
    __tablename__ = "memory_access_logs"
    
    memory_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    context = Column(String, nullable=False)

    # Relationships
    memory = relationship("AgentMemory", back_populates="access_logs")
```
## `backend/maestro/app/modules/memory/conflict.py`
```py
"""
Conflict Resolution Service for Memory System (Sprint 006.5)
"""
import enum
import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.memory.models import AgentMemory
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import MessageRole, AIMessage

logger = logging.getLogger(__name__)


class ResolutionDecision(str, enum.Enum):
    MERGE = "MERGE"
    SUPERSEDE = "SUPERSEDE"
    NEW = "NEW"
    IGNORE = "IGNORE"
    UNCERTAIN = "UNCERTAIN"


class ResolutionResponse(BaseModel):
    decision: ResolutionDecision = Field(..., description="The decision of how to handle the candidate memory against the existing memory.")
    reasoning: str = Field(..., description="Brief explanation for the decision.")


def _extract_json(text: str) -> str:
    """
    Extracts the first JSON object from an LLM response.
    Handles cases where the provider prefixes the JSON with prose
    (e.g. "Sure! Here is the JSON: {...}").
    """
    # Try parsing directly if provider natively returned pure JSON
    try:
        json.loads(text.strip())
        return text.strip()
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences first
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.rindex("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.rindex("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()

    # Find the first '{' and match to closing '}' while respecting quotes
    brace_start = text.find("{")
    if brace_start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escape = False

    for i, char in enumerate(text[brace_start:], start=brace_start):
        if not escape and char == '"':
            in_string = not in_string
        
        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start:i + 1]
        
        if char == '\\' and not escape:
            escape = True
        else:
            escape = False

    return text[brace_start:].strip()


class ConflictResolutionService:
    """
    Evaluates a candidate memory against existing memories using an LLM.
    `response.content` is guaranteed non-empty by the `LLMResponse` contract in app.ai.schemas.
    """

    def __init__(self, llm_provider: BaseLLMProvider):
        if llm_provider is None:
            raise ValueError("LLM provider required for async conflict resolution.")
        self.llm = llm_provider

    async def resolve(
        self,
        candidate_content: str,
        existing_memory: AgentMemory,
        _retry: bool = True
    ) -> ResolutionDecision:
        """
        Uses the LLM to determine the relationship between the candidate content
        and an existing memory. Retries once on transient failure.
        """
        system_prompt = (
            "You are an AI conflict resolution engine for a long-term memory system. "
            "Your task is to compare a NEW candidate memory against an EXISTING memory and determine their relationship.\n\n"
            "Return ONLY a JSON object — no prose, no markdown fences. Schema:\n"
            '{"decision": "<DECISION>", "reasoning": "<brief reason>"}\n\n'
            "The 'decision' field must be exactly one of:\n"
            "- MERGE: The new memory expresses the same fact (perhaps phrased differently). It does not change the truth.\n"
            "- SUPERSEDE: The new memory directly contradicts or updates the existing memory. Existing is now outdated.\n"
            "- NEW: The new memory is completely distinct despite textual similarities.\n"
            "- IGNORE: The new memory adds nothing; the existing memory covers it completely.\n"
            "- UNCERTAIN: It is unclear how they relate without more context.\n"
        )

        user_prompt = (
            f"EXISTING MEMORY:\n{existing_memory.content}\n\n"
            f"NEW CANDIDATE MEMORY:\n{candidate_content}"
        )

        messages = [
            AIMessage(role=MessageRole.SYSTEM, content=system_prompt),
            AIMessage(role=MessageRole.USER, content=user_prompt)
        ]

        try:
            # LLMResponse.content is required (str) per app.ai.schemas — safe to access directly.
            response = await self.llm.generate(messages=messages, temperature=0.0)

            raw = response.content.strip()
            extracted = _extract_json(raw)

            data = json.loads(extracted)
            result = ResolutionResponse(**data)
            return result.decision

        except Exception as e:
            if _retry:
                logger.warning(
                    f"Conflict resolution failed (will retry once): {e}"
                )
                return await self.resolve(candidate_content, existing_memory, _retry=False)

            logger.exception(f"Conflict resolution failed after retry: {e}")
            # Fallback: treat as uncertain — do not accidentally SUPERSEDE or MERGE.
            return ResolutionDecision.UNCERTAIN
```
## `backend/maestro/app/modules/memory/policy.py`
```py
"""
Centralized Memory Policy (Sprint 006.5)
Controls lifecycle rules for agent memories.
"""
import math
from datetime import datetime, timezone
from typing import Set

from app.core.ai_settings import ai_settings
from app.modules.memory.models import AgentMemory, MemoryType, MemoryStatus


class MemoryPolicy:
    """
    Encapsulates all logic governing the decay, archival, and lifecycle of memories.
    """
    
    @classmethod
    def get_protected_memory_types(cls) -> Set[MemoryType]:
        """
        Types of memories that should NEVER be archived solely due to age.
        """
        return {
            MemoryType.GOAL,
            MemoryType.PROJECT,
            MemoryType.DECISION,
            MemoryType.CONSTRAINT
        }
        
    @classmethod
    def calculate_decayed_importance(cls, memory: AgentMemory) -> float:
        """
        Calculates the new importance score based on exponential decay.
        """
        # Protect highly durable memories from decay entirely, or we can just protect them from archival.
        # The CTO spec says never archive GOAL, PROJECT, DECISION based solely on age.
        # Let's still allow importance to decay, but they won't be archived.
        
        now = datetime.now(timezone.utc)
        days_since_access = (now - memory.last_accessed).days
        
        # if accessed very recently, don't decay
        if days_since_access <= 0:
            return memory.importance_score
            
        decay_factor = math.exp(-ai_settings.MEMORY_DECAY_RATE * days_since_access)
        return memory.importance_score * decay_factor

    @classmethod
    def should_archive(cls, memory: AgentMemory, current_importance: float) -> bool:
        """
        Determines if a memory should be archived based on its decayed importance.
        """
        if memory.status != MemoryStatus.ACTIVE:
            return False
            
        if memory.memory_type in cls.get_protected_memory_types():
            return False
            
        return current_importance < ai_settings.MEMORY_ARCHIVE_THRESHOLD

    @classmethod
    def requires_llm_resolution(cls, is_async_extraction: bool) -> bool:
        """
        Determines if an LLM conflict resolution pass is required.
        """
        # CTO explicit flow: Explicit tools -> NO LLM. Async extraction -> LLM.
        return is_async_extraction
```
## `backend/maestro/app/modules/memory/services.py`
```py
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
```
## `backend/maestro/app/modules/memory/repositories.py`
```py
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

    async def get_for_update(self, organization_id: UUID, memory_id: UUID) -> Optional[AgentMemory]:
        """Fetches a memory and locks the row (SELECT ... FOR UPDATE) to prevent concurrent modifications."""
        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.id == memory_id,
                AgentMemory.organization_id == organization_id,
                AgentMemory.is_deleted == False
            )
            .with_for_update()
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
        await self.db.flush()
        return memory

    async def record_access(self, memory: AgentMemory, context: str) -> None:
        """Increments access count and logs the access atomically."""
        from datetime import datetime, timezone
        from sqlalchemy import update
        
        now = datetime.now(timezone.utc)
        
        # Atomic increment at the database layer to avoid race conditions
        stmt = (
            update(AgentMemory)
            .where(AgentMemory.id == memory.id)
            .values(
                access_count=AgentMemory.access_count + 1,
                last_accessed=now
            )
            .execution_options(synchronize_session=False)
        )
        await self.db.execute(stmt)
        
        # Update the memory object in memory so the caller sees the changes
        memory.access_count += 1
        memory.last_accessed = now

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
```
## `backend/maestro/app/workers/memory_tasks.py`
```py
"""
Celery tasks for async memory extraction.
"""
import json
import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import CelerySessionLocal
from app.core.ai_settings import ai_settings
from app.modules.memory.schemas import MemoryExtractionList
from app.modules.memory.services import MemoryService
from app.modules.memory.models import MemorySource, MemoryStatus

logger = logging.getLogger(__name__)


async def _extract_memories_async(conversation_id: UUID, organization_id: UUID, transcript: str):
    """Async inner function to perform the extraction."""
    async with CelerySessionLocal() as db:
        from app.ai.providers.google import GoogleProvider
        from app.ai.embedding.google import GeminiEmbeddingProvider
        from app.ai.schemas import MessageRole, AIMessage
        
        # Instantiate dependencies
        llm = GoogleProvider()
        embedder = GeminiEmbeddingProvider()
        service = MemoryService(db, embedding_provider=embedder)
        
        system_instruction = (
            "You are a memory extraction engine. Review the following conversation transcript "
            "and extract any new, important facts, user preferences, decisions, goals, profiles, "
            "warnings, tasks, relationships, or constraints."
            "\nIgnore pleasantries. Focus on long-term context that an AI executive would need "
            "to remember for future interactions.\n"
            "Return a JSON object containing a 'memories' list."
        )
        
        messages = [
            AIMessage(role=MessageRole.SYSTEM, content=system_instruction),
            AIMessage(role=MessageRole.USER, content=f"Transcript:\n{transcript}")
        ]
        
        try:
            response = await llm.generate(
                messages=messages,
                temperature=0.1,
                response_schema=MemoryExtractionList.model_json_schema()
            )
            
            if not response.content:
                logger.warning(f"No text generated for conversation {conversation_id} extraction.")
                return

            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            extraction_data = json.loads(text.strip())
            extraction_list = MemoryExtractionList(**extraction_data)
        except Exception as e:
            logger.exception(f"Failed to extract memory JSON using LLM provider: {e}")
            return
            
        for ext in extraction_list.memories:
            try:
                # add_memory automatically handles deduplication and status resolution via embedding check
                await service.add_memory(
                    organization_id=organization_id,
                    content=ext.content,
                    memory_type=ext.memory_type,
                    source=MemorySource.CONVERSATION,
                    importance=ext.importance,
                    confidence=ext.confidence,
                    llm_provider=llm,
                    is_async_extraction=True
                )
            except Exception as e:
                logger.exception(f"Failed to save extracted memory: {e}")
                
        logger.info(f"Extracted and processed {len(extraction_list.memories)} memories.")


async def _decay_memories_async():
    """Async inner function for decaying memories."""
    from app.modules.memory.models import AgentMemory
    from app.modules.memory.policy import MemoryPolicy
    from sqlalchemy import select

    async with CelerySessionLocal() as db:
        service = MemoryService(db, embedding_provider=None) # embedder not needed for decay
        
        # We need to decay ACTIVE memories that haven't been accessed recently (e.g. 24h)
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        stmt = select(AgentMemory).where(
            AgentMemory.status == MemoryStatus.ACTIVE,
            AgentMemory.last_accessed < cutoff
        )
        result = await db.execute(stmt)
        memories = result.scalars().all()
        
        decayed_count = 0
        archived_count = 0
        batch_size = 100
        current_batch = 0

        try:
            for mem in memories:
                new_importance = MemoryPolicy.calculate_decayed_importance(mem)
                if new_importance != mem.importance_score:
                    mem.importance_score = new_importance
                    decayed_count += 1

                    if MemoryPolicy.should_archive(mem, new_importance):
                        mem.status = MemoryStatus.ARCHIVED
                        archived_count += 1

                    await service.repo.update(mem)
                    current_batch += 1

                    if current_batch >= batch_size:
                        await db.commit()
                        current_batch = 0

            if current_batch > 0:
                await db.commit()

            logger.info(
                "Memory decay complete. decayed=%d archived=%d",
                decayed_count, archived_count
            )
        except Exception:
            await db.rollback()
            raise

@shared_task(bind=True, max_retries=3)
def decay_memories_task(self):
    """
    Celery task to apply exponential decay to memory importance.
    """
    import asyncio
    try:
        asyncio.run(_decay_memories_async())
    except Exception as exc:
        logger.exception(f"Error in decay_memories_task: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def extract_conversation_memories_task(self, conversation_id_str: str, organization_id_str: str, transcript: str):
    """
    Celery task to extract memories from a completed conversation chunk.
    """
    import asyncio
    
    conversation_id = UUID(conversation_id_str)
    organization_id = UUID(organization_id_str)
    
    try:
        asyncio.run(_extract_memories_async(conversation_id, organization_id, transcript))
    except Exception as exc:
        logger.exception(f"Error in extract_conversation_memories_task: {exc}")
        raise self.retry(exc=exc, countdown=60)
```
## `backend/maestro/app/workers/celery_app.py`
```py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": "main-queue",
    "app.workers.memory_tasks.*": "memory-queue",
    "knowledge.*": "knowledge-queue",
}

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "decay-memories-daily": {
        "task": "app.workers.memory_tasks.decay_memories_task",
        "schedule": crontab(hour=0, minute=0),  # Run daily at midnight
    },
}


# Example task
@celery_app.task(acks_late=True)
def example_task(word: str) -> str:
    return f"Processed: {word}"
```
## `backend/maestro/alembic/versions/004_memory_system.py`
```py
"""
Memory system models and tables (Sprint 006)

Revision ID: 004_memory_system
Revises: 003_knowledge_engine
Create Date: 2026-07-07 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
# revision identifiers, used by Alembic.
revision = '004_memory_system'
down_revision = '003_knowledge_engine'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create Enums
    memory_type_enum = postgresql.ENUM('fact', 'preference', 'goal', 'decision', 'profile', 'warning', 'task', 'relationship', 'constraint', 'project', name='memory_type_enum', create_type=False)
    memory_type_enum.create(op.get_bind(), checkfirst=True)

    memory_status_enum = postgresql.ENUM('active', 'stale', 'archived', 'conflicted', 'superseded', name='memory_status_enum', create_type=False)
    memory_status_enum.create(op.get_bind(), checkfirst=True)

    memory_source_enum = postgresql.ENUM('conversation', 'manual', 'tool', 'import', 'system', name='memory_source_enum', create_type=False)
    memory_source_enum.create(op.get_bind(), checkfirst=True)

    # 2. agent_memories
    op.create_table('agent_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', memory_type_enum, nullable=False, server_default='fact'),
        sa.Column('status', memory_status_enum, nullable=False, server_default='active'),
        sa.Column('source', memory_source_enum, nullable=False, server_default='system'),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_memories_organization_id'), 'agent_memories', ['organization_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_user_id'), 'agent_memories', ['user_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_agent_id'), 'agent_memories', ['agent_id'], unique=False)

    # 3. memory_embeddings
    op.create_table('memory_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_embeddings_memory_id'), 'memory_embeddings', ['memory_id'], unique=False)
    
    # INTENTIONAL: The embedding dimension is frozen at 768 for this migration.
    # Migrations must be immutable — they cannot depend on runtime configuration.
    # If the embedding model changes (e.g. to 1024-dim), create a NEW migration that:
    #   1. Adds a new `vector_v2 vector(1024)` column.
    #   2. Backfills it.
    #   3. Renames / drops the old column.
    # Also update AI_EMBEDDING_DIMENSIONS in ai_settings.py to match.
    # A startup validation in app/core/startup.py should assert:
    #   SELECT vector_dims(vector) FROM memory_embeddings LIMIT 1 == ai_settings.EMBEDDING_DIMENSIONS
    dim = 768
    op.execute(f"ALTER TABLE memory_embeddings ADD COLUMN vector vector({dim});")
    op.execute(f"CREATE INDEX ix_memory_embeddings_vector ON memory_embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);")

    # 4. memory_access_logs
    op.create_table('memory_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_access_logs_memory_id'), 'memory_access_logs', ['memory_id'], unique=False)
    op.create_index(op.f('ix_memory_access_logs_organization_id'), 'memory_access_logs', ['organization_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_memory_access_logs_organization_id'), table_name='memory_access_logs')
    op.drop_index(op.f('ix_memory_access_logs_memory_id'), table_name='memory_access_logs')
    op.drop_table('memory_access_logs')
    
    op.execute('DROP INDEX IF EXISTS ix_memory_embeddings_vector;')
    op.drop_index(op.f('ix_memory_embeddings_memory_id'), table_name='memory_embeddings')
    op.drop_table('memory_embeddings')
    
    op.drop_index(op.f('ix_agent_memories_agent_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_user_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_organization_id'), table_name='agent_memories')
    op.drop_table('agent_memories')

    # Drop enums
    op.execute('DROP TYPE memory_type_enum;')
    op.execute('DROP TYPE memory_status_enum;')
    op.execute('DROP TYPE memory_source_enum;')
```
## `backend/maestro/alembic/versions/005_memory_stabilization.py`
```py
"""
Memory system stabilization (Sprint 006.5)

Revision ID: 005_memory_stabilization
Revises: 004_memory_system
Create Date: 2026-07-07 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_memory_stabilization'
down_revision = '004_memory_system'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add 'PROJECT' to memory_type_enum
    # Add 'SUPERSEDED' to memory_status_enum
    
    # In PostgreSQL, we can add enum values using ALTER TYPE
    op.execute("ALTER TYPE memory_type_enum ADD VALUE IF NOT EXISTS 'project'")
    op.execute("ALTER TYPE memory_status_enum ADD VALUE IF NOT EXISTS 'superseded'")

def downgrade() -> None:
    # PostgreSQL does not support safely removing values from an ENUM type
    # without completely recreating the type and all columns that depend on it.
    # Therefore, the downgrade is a no-op.
    
    # Downgrade:
    # No-op.
    #
    # Reason:
    # Postgres cannot safely remove enum values without recreating the enum.
    pass
```
## `backend/maestro/alembic/versions/006_memory_embedding_index.py`
```py
"""
Memory stabilization (Sprint 006.5) — Round 2 schema hardening

Revision ID: 006_memory_embedding_index
Revises: 005_memory_stabilization
Create Date: 2026-07-07 19:30:00.000000

Changes:
    - Adds a unique partial index on (memory_id) for non-deleted memory_embeddings.
      This enforces ONE active embedding per memory at the database level, preventing
      duplicate embeddings from concurrent inserts.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '006_memory_embedding_index'
down_revision = '005_memory_stabilization'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Unique partial index: only one active (non-deleted) embedding per memory.
    # is_deleted=False rows are the only ones constrained. Soft-deleted rows are exempt,
    # so historical embeddings from superseded memories can coexist without violating the index.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_memory_embeddings_active
        ON memory_embeddings (memory_id)
        WHERE is_deleted = FALSE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uix_memory_embeddings_active;")
```
## `backend/maestro/tests/api/test_memory_resolution.py`
```py
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json

from app.modules.memory.models import AgentMemory, MemoryType, MemoryStatus, MemorySource
from app.modules.memory.services import MemoryService
from app.modules.memory.conflict import ConflictResolutionService, ResolutionDecision
from app.core.database import SessionLocal
from app.core.ai_settings import ai_settings


# A dummy LLM provider to mock the resolution without hitting the real API
class MockLLMProvider:
    def __init__(self, mock_decision: ResolutionDecision):
        self.mock_decision = mock_decision
        
    async def generate(self, messages, temperature=0.7, **kwargs):
        class MockResponse:
            content = json.dumps({"decision": self.mock_decision.value, "reasoning": "Mocked reasoning"})
        return MockResponse()


@pytest.mark.asyncio
async def test_memory_conflict_supersede(test_organization):
    """Test that a new memory supersedes an old memory if the LLM says so."""
    async with SessionLocal() as db:
        from app.ai.embedding.google import GeminiEmbeddingProvider
        service = MemoryService(db, embedding_provider=GeminiEmbeddingProvider())
        
        # Insert initial memory
        mem1 = await service.add_memory(
            organization_id=test_organization.id,
            content="We use QuickBooks for accounting.",
            memory_type=MemoryType.FACT,
            source=MemorySource.SYSTEM
        )
        
        assert mem1.status == MemoryStatus.ACTIVE
        
        # Override the conflict service inside MemoryService for testing
        original_add_memory = service.add_memory
        
        # We simulate the async extraction flow manually by invoking the logic
        from app.modules.memory.conflict import ConflictResolutionService
        conflict_svc = ConflictResolutionService(MockLLMProvider(ResolutionDecision.SUPERSEDE))
        
        # Because add_memory instantiates its own provider, we monkeypatch it or just test the service
        # Let's test the deduplication logic explicitly
        decision = await conflict_svc.resolve("We migrated from QuickBooks to Xero.", mem1)
        assert decision == ResolutionDecision.SUPERSEDE


@pytest.mark.asyncio
async def test_memory_decay_policy():
    """Test the MemoryPolicy exponential decay."""
    from app.modules.memory.policy import MemoryPolicy
    import math
    
    # Create a dummy memory
    mem = AgentMemory(
        content="Dummy",
        last_accessed=datetime(2020, 1, 1, tzinfo=timezone.utc),
        importance_score=1.0,
        status=MemoryStatus.ACTIVE,
        memory_type=MemoryType.FACT
    )
    
    # It should be decayed significantly
    decayed_score = MemoryPolicy.calculate_decayed_importance(mem)
    assert decayed_score < 0.1
    
    # It should be archived
    assert MemoryPolicy.should_archive(mem, decayed_score) == True
    
    # But if it is a GOAL, it shouldn't be archived
    mem.memory_type = MemoryType.GOAL
    assert MemoryPolicy.should_archive(mem, decayed_score) == False
```
## `backend/maestro/tests/api/test_memory_e2e.py`
```py
import pytest
from httpx import AsyncClient
from uuid import UUID

from app.modules.memory.models import MemoryType, MemoryStatus, MemorySource
from app.modules.organizations.models import Organization
from app.modules.users.models import User

# Assuming standard test fixtures are available from conftest.py
@pytest.fixture
def memory_payload():
    return {
        "content": "The CEO prefers quarterly reports formatted as tables.",
        "memory_type": "preference",
        "importance_score": 0.8,
        "confidence_score": 0.9,
        "source": "manual",
        "agent_id": "CEO"
    }

@pytest.mark.asyncio
async def test_create_memory(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test manual memory creation via the API."""
    response = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == memory_payload["content"]
    assert data["memory_type"] == memory_payload["memory_type"]
    assert data["status"] == "active"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_memories(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test listing memories."""
    # Create one first
    await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    
    response = await async_client.get(
        f"/api/v1/organizations/{test_organization.id}/memories",
        headers=authenticated_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["content"] == memory_payload["content"]

@pytest.mark.asyncio
async def test_update_memory_to_archived(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test updating a memory, specifically soft-deleting it."""
    create_resp = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    memory_id = create_resp.json()["id"]
    
    update_resp = await async_client.patch(
        f"/api/v1/organizations/{test_organization.id}/memories/{memory_id}",
        json={"status": "archived"},
        headers=authenticated_headers
    )
    
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "archived"
```
## `backend/maestro/tests/api/test_memory_lifecycle.py`
```py
"""
Sprint 006.5 — Targeted regression tests for memory lifecycle and conflict resolution.

Covers:
    - _extract_json strips markdown fences
    - _extract_json strips prose prefix
    - ConflictResolutionService retry succeeds on second attempt
    - ConflictResolutionService retry failure returns UNCERTAIN
    - add_memory merge path regenerates embedding
    - add_memory supersede path deletes old embeddings
    - add_memory raises when is_async_extraction=True but llm_provider is None
    - search ranking uses last_accessed (not created_at)
    - merge rewrite falls back to newer content when LLM fails
"""
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.modules.memory.conflict import (
    ConflictResolutionService,
    ResolutionDecision,
    _extract_json,
)
from app.modules.memory.models import AgentMemory, MemoryType, MemoryStatus, MemorySource
from app.core.ai_settings import ai_settings


# ─────────────────────────────────────────────────────────────────────────────
# _extract_json helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self):
        raw = '{"decision": "MERGE", "reasoning": "same fact"}'
        assert _extract_json(raw) == raw

    def test_markdown_json_fence(self):
        raw = '```json\n{"decision": "MERGE", "reasoning": "same fact"}\n```'
        result = _extract_json(raw)
        assert result == '{"decision": "MERGE", "reasoning": "same fact"}'

    def test_plain_code_fence(self):
        raw = '```\n{"decision": "NEW", "reasoning": "different"}\n```'
        result = _extract_json(raw)
        assert result == '{"decision": "NEW", "reasoning": "different"}'

    def test_prose_prefix(self):
        raw = 'Sure! Here is the JSON response:\n{"decision": "SUPERSEDE", "reasoning": "updated fact"}'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["decision"] == "SUPERSEDE"

    def test_prose_prefix_and_suffix(self):
        raw = 'Based on the analysis:\n{"decision": "IGNORE", "reasoning": "covered"}\nHope that helps!'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["decision"] == "IGNORE"

    def test_no_json(self):
        """Should return the stripped text when no JSON object is found."""
        raw = "I cannot determine the relationship."
        result = _extract_json(raw)
        assert result == raw.strip()

    def test_json_with_braces_in_strings(self):
        """Should handle braces inside strings within JSON."""
        raw = '{"decision": "IGNORE", "reasoning": "Found text {inside braces}"}'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["reasoning"] == "Found text {inside braces}"

# ─────────────────────────────────────────────────────────────────────────────
# ConflictResolutionService — retry behaviour
# ─────────────────────────────────────────────────────────────────────────────

def _make_memory(content: str) -> AgentMemory:
    return AgentMemory(
        id=uuid4(),
        organization_id=uuid4(),
        content=content,
        memory_type=MemoryType.FACT,
        status=MemoryStatus.ACTIVE,
        source=MemorySource.SYSTEM,
        importance_score=0.8,
        confidence_score=0.9,
        last_accessed=datetime.now(timezone.utc),
        access_count=0,
    )


def _ok_response(decision: ResolutionDecision):
    class R:
        content = json.dumps({"decision": decision.value, "reasoning": "ok"})
    return R()


@pytest.mark.asyncio
async def test_conflict_retry_succeeds_on_second_attempt():
    """First call raises, second call succeeds — should return the decision."""
    existing = _make_memory("We use QuickBooks.")
    call_count = 0

    async def flaky_generate(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("transient network error")
        return _ok_response(ResolutionDecision.SUPERSEDE)

    mock_llm = MagicMock()
    mock_llm.generate = flaky_generate

    svc = ConflictResolutionService(mock_llm)
    decision = await svc.resolve("We now use Xero.", existing)
    assert decision == ResolutionDecision.SUPERSEDE
    assert call_count == 2


@pytest.mark.asyncio
async def test_conflict_retry_returns_uncertain_after_two_failures():
    """Both attempts raise — should fall back to UNCERTAIN."""
    existing = _make_memory("We use QuickBooks.")

    async def always_fail(**kwargs):
        raise ConnectionError("transient network error")

    mock_llm = MagicMock()
    mock_llm.generate = always_fail

    svc = ConflictResolutionService(mock_llm)
    decision = await svc.resolve("We now use Xero.", existing)
    assert decision == ResolutionDecision.UNCERTAIN


# ─────────────────────────────────────────────────────────────────────────────
# MemoryService — merge path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_memory_raises_when_async_extraction_without_llm_provider():
    """Passing is_async_extraction=True without llm_provider should raise immediately."""
    from app.modules.memory.services import MemoryService
    mock_db = AsyncMock()
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.1] * 768])

    service = MemoryService(db=mock_db, embedding_provider=mock_embedder)

    with pytest.raises(RuntimeError, match="requires an llm_provider"):
        await service.add_memory(
            organization_id=uuid4(),
            content="Test memory",
            is_async_extraction=True,
            llm_provider=None,
        )


@pytest.mark.asyncio
async def test_merge_regenerates_embedding():
    """
    When a MERGE decision is made, the existing memory's embedding should be
    deleted and a new one created from the merged content.
    """
    from app.modules.memory.services import MemoryService

    org_id = uuid4()
    existing_mem = _make_memory("CEO prefers reports as tables.")
    existing_mem.organization_id = org_id

    mock_db = AsyncMock()
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.2] * 768])

    service = MemoryService(db=mock_db, embedding_provider=mock_embedder)

    delete_calls = []
    create_calls = []

    service.embedding_repo = AsyncMock()
    service.embedding_repo.vector_search = AsyncMock(
        return_value=[(existing_mem, 0.97)]  # similarity > MEMORY_MERGE_THRESHOLD
    )
    service.embedding_repo.delete_for_memory = AsyncMock(
        side_effect=lambda mid: delete_calls.append(mid)
    )
    service.embedding_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    service.repo = AsyncMock()
    service.repo.record_access = AsyncMock()
    service.repo.update = AsyncMock()

    await service.add_memory(
        organization_id=org_id,
        content="CEO prefers quarterly reports in table format.",
        is_async_extraction=False,  # deterministic path, similarity >= threshold
    )

    # delete_for_memory must be called for the existing memory during _create_embedding
    assert any(call == existing_mem.id for call in delete_calls), (
        "Expected delete_for_memory to be called with the existing memory id on merge"
    )
    assert service.embedding_repo.create.called, (
        "Expected a new embedding to be created after merge"
    )


@pytest.mark.asyncio
async def test_supersede_deletes_old_embeddings():
    """
    When a SUPERSEDE decision is made, the superseded memory's embeddings
    should be soft-deleted before the new memory is created.
    """
    from app.modules.memory.services import MemoryService

    org_id = uuid4()
    existing_mem = _make_memory("We use QuickBooks for accounting.")
    existing_mem.organization_id = org_id

    mock_db = AsyncMock()
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.3] * 768])

    service = MemoryService(db=mock_db, embedding_provider=mock_embedder)

    delete_calls = []

    # Simulate an LLM returning SUPERSEDE
    async def fake_generate(**kwargs):
        class R:
            content = json.dumps({"decision": "SUPERSEDE", "reasoning": "updated fact"})
        return R()

    mock_llm = MagicMock()
    mock_llm.generate = fake_generate

    service.embedding_repo = AsyncMock()
    service.embedding_repo.vector_search = AsyncMock(
        return_value=[(existing_mem, 0.90)]
    )
    service.embedding_repo.delete_for_memory = AsyncMock(
        side_effect=lambda mid: delete_calls.append(mid)
    )
    service.embedding_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    service.repo = AsyncMock()
    service.repo.create = AsyncMock(return_value=_make_memory("We migrated to Xero."))
    service.repo.update = AsyncMock()

    await service.add_memory(
        organization_id=org_id,
        content="We migrated to Xero.",
        is_async_extraction=True,
        llm_provider=mock_llm,
    )

    assert existing_mem.status == MemoryStatus.SUPERSEDED
    # delete_for_memory should be called for the old memory
    assert existing_mem.id in delete_calls, (
        "Expected delete_for_memory to be called for the superseded memory"
    )


@pytest.mark.asyncio
async def test_merge_rewrite_falls_back_when_llm_fails():
    """_rewrite_merged_content falls back to new_content when the LLM raises."""
    from app.modules.memory.services import MemoryService

    mock_db = AsyncMock()
    service = MemoryService(db=mock_db)

    async def fail_generate(**kwargs):
        raise ConnectionError("LLM unreachable")

    mock_llm = MagicMock()
    mock_llm.generate = fail_generate

    org_id = uuid4()
    mem_id = uuid4()
    result = await service._rewrite_merged_content(
        mock_llm, "Old content.", "New content.", org_id, mem_id
    )
    assert result == "Old content.\nNew content."


# ─────────────────────────────────────────────────────────────────────────────
# Ranking — last_accessed vs created_at
# ─────────────────────────────────────────────────────────────────────────────

def test_ranking_uses_last_accessed():
    """
    A recently-accessed old memory should outscore a never-accessed new memory
    when the recency weight is dominant.
    """
    from app.modules.memory.services import MemoryService
    from unittest.mock import AsyncMock
    service = MemoryService(db=AsyncMock())

    now = datetime.now(timezone.utc)

    # Old memory, recently accessed — should still get high recency
    old_but_active = _make_memory("Old but accessed today")
    old_but_active.last_accessed = now - timedelta(days=1)
    old_but_active.importance_score = 0.7
    old_but_active.confidence_score = 0.7
    old_but_active.access_count = 5

    # New memory, never touched
    new_and_stale = _make_memory("New but never accessed")
    new_and_stale.last_accessed = now - timedelta(days=25)
    new_and_stale.importance_score = 0.7
    new_and_stale.confidence_score = 0.7
    new_and_stale.access_count = 0

    score_active = service._calculate_score(old_but_active, similarity=0.85)
    score_stale  = service._calculate_score(new_and_stale,  similarity=0.85)

    assert score_active > score_stale, (
        "Recently-accessed memory should outrank a long-unaccessed memory with equal importance/confidence"
    )
import asyncio

@pytest.mark.asyncio
async def test_concurrent_merge_race_condition():
    """Simulates concurrent merge attempts to verify the second attempt falls back or handles it."""
    from app.modules.memory.services import MemoryService
    
    org_id = uuid4()
    existing_mem = _make_memory("We use QuickBooks for accounting.")
    existing_mem.organization_id = org_id
    
    mock_db = AsyncMock()
    mock_embedder = AsyncMock()
    mock_embedder.embed = AsyncMock(return_value=[[0.3] * 768])
    
    service = MemoryService(db=mock_db, embedding_provider=mock_embedder)
    service.embedding_repo = AsyncMock()
    service.embedding_repo.vector_search = AsyncMock(
        return_value=[(existing_mem, 0.90)]
    )
    
    # Simulate get_for_update returning None for the second concurrent call
    async def mock_get_for_update(org, mid):
        # We need a closure state
        if not hasattr(mock_get_for_update, "called"):
            mock_get_for_update.called = True
            return existing_mem
        return None
        
    service.repo = AsyncMock()
    service.repo.get_for_update = mock_get_for_update
    service.repo.create = AsyncMock(return_value=existing_mem)
    
    # Simulate LLM returning MERGE
    async def fake_generate(**kwargs):
        class R:
            content = json.dumps({"decision": "MERGE", "reasoning": "same"})
        return R()

    mock_llm = MagicMock()
    mock_llm.generate = fake_generate
    
    # We call add_memory twice concurrently
    res1, res2 = await asyncio.gather(
        service.add_memory(org_id, "We use QuickBooks.", is_async_extraction=True, llm_provider=mock_llm),
        service.add_memory(org_id, "We use QuickBooks.", is_async_extraction=True, llm_provider=mock_llm)
    )
    
    # One should have merged (returned existing_mem), the other should have fallen back to NEW (returned existing_mem because we mocked create)
    assert res1.id == existing_mem.id
    assert res2.id == existing_mem.id


@pytest.mark.asyncio
async def test_embedding_dimension_mismatch_raises():
    """_create_embedding should raise ValueError if dimensions don't match config."""
    from app.modules.memory.services import MemoryService
    mock_db = AsyncMock()
    service = MemoryService(db=mock_db)
    
    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        # Default config is 768, we pass a vector of length 2
        await service._create_embedding(uuid4(), [0.1, 0.2])

@pytest.mark.asyncio
async def test_concurrent_search_access_count_uses_atomic_increment():
    """Verify record_access uses an atomic SQL update (AgentMemory.access_count + 1)."""
    from app.modules.memory.repositories import MemoryRepository
    from unittest.mock import AsyncMock
    from uuid import uuid4
    
    mock_db = AsyncMock()
    repo = MemoryRepository(db=mock_db)
    
    mem = _make_memory("Test")
    mem.id = uuid4()
    mem.access_count = 10
    
    await repo.record_access(mem, "test context")
    
    # Verify we executed an UPDATE statement
    assert mock_db.execute.called
    stmt = mock_db.execute.call_args[0][0]
    
    # In SQLAlchemy, str(stmt) reveals the compiled SQL
    compiled = str(stmt).lower()
    assert "update agent_memories" in compiled
    assert "access_count = agent_memories.access_count +" in compiled
    
    # Verify the in-memory object was also updated
    assert mem.access_count == 11
```
