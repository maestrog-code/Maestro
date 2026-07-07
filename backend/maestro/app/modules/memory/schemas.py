"""
Pydantic schemas for the Agent Memory system.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.modules.memory.models import MemoryType, MemoryStatus, MemorySource


class MemoryBase(BaseModel):
    content: str
    memory_type: MemoryType = Field(default=MemoryType.FACT)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)


class MemoryCreate(MemoryBase):
    agent_id: Optional[str] = None
    source: MemorySource = Field(default=MemorySource.SYSTEM)


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    status: Optional[MemoryStatus] = None
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MemoryResponse(MemoryBase):
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    agent_id: Optional[str] = None
    status: MemoryStatus
    source: MemorySource
    last_accessed: datetime
    access_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    page: int
    page_size: int


# --- Structured Output Schema for Gemini Extraction ---

class MemoryExtraction(BaseModel):
    """Schema enforced by the LLM for memory extraction."""
    content: str = Field(description="The extracted fact, goal, or preference.")
    memory_type: MemoryType = Field(description="The category of the memory.")
    confidence: float = Field(ge=0.0, le=1.0, description="How confident you are in this memory being accurate (0.0 to 1.0).")
    importance: float = Field(ge=0.0, le=1.0, description="How important this memory is for future reasoning (0.0 to 1.0).")
    reason: str = Field(description="Brief explanation of why this was extracted.")
    conflicts_with: Optional[str] = Field(default=None, description="If this contradicts an existing memory, summarize the conflict.")
    source: MemorySource = Field(default=MemorySource.CONVERSATION, description="Origin of this memory.")


class MemoryExtractionList(BaseModel):
    """Allows extracting multiple memories in one pass."""
    memories: List[MemoryExtraction]
