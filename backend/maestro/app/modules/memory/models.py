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
