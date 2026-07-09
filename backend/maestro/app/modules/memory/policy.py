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
