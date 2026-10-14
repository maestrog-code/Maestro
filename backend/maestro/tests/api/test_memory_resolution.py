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
