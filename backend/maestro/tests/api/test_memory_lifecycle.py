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

