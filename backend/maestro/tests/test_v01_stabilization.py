import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.agents.definitions.ceo import ceo_agent
from app.ai.agents.definitions.cfo import cfo_agent
from app.ai.pipeline.executor import AIExecutionPipeline
from app.ai.schemas import ToolCall
from app.ai.tools.orchestration_tools import DelegateTaskTool
from app.modules.ai_conversations.models import Conversation
from app.modules.organizations.models import Organization
from app.modules.users.models import User


def _model_pair():
    user = User(
        id=uuid4(),
        email="owner@example.com",
        hashed_password="hashed",
        first_name="Ada",
        last_name="Lovelace",
    )
    org = Organization(id=uuid4(), name="Maestro Test", slug="maestro-test")
    conversation = Conversation(
        id=uuid4(),
        organization_id=org.id,
        active_agent="CEO",
        messages=[],
    )
    return user, org, conversation


def test_ceo_is_only_agent_with_delegation_tool():
    assert "delegate_task" in ceo_agent.tools
    assert "delegate_task" not in cfo_agent.tools


def test_delegate_task_tool_schema_uses_base_tool_contract():
    schema = DelegateTaskTool().get_json_schema()

    assert schema["name"] == "delegate_task"
    assert "target_agent" in schema["parameters"]["properties"]
    assert "instructions" in schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_pipeline_fetches_memory_with_embedding_provider(monkeypatch):
    user, org, conversation = _model_pair()
    pipeline = AIExecutionPipeline(AsyncMock(), user, org, conversation)
    captured = {}

    class FakeMemory:
        memory_type = SimpleNamespace(value="fact")
        content = "CEO prefers concise weekly updates."

    class FakeMemoryService:
        def __init__(self, db, embedding_provider=None):
            captured["embedding_provider"] = embedding_provider

        async def search(self, **kwargs):
            captured["search_kwargs"] = kwargs
            return [FakeMemory()]

    monkeypatch.setattr("app.modules.memory.services.MemoryService", FakeMemoryService)

    memories = await pipeline._fetch_implicit_memory("What should I know?")

    assert captured["embedding_provider"] is not None
    assert captured["search_kwargs"]["organization_id"] == org.id
    assert memories == [{"memory_type": "fact", "content": "CEO prefers concise weekly updates."}]


@pytest.mark.asyncio
async def test_pipeline_forwards_tool_calls_to_executor(monkeypatch):
    user, org, conversation = _model_pair()
    fake_db = AsyncMock()
    pipeline = AIExecutionPipeline(fake_db, user, org, conversation)
    captured = {}

    class FakeProvider:
        calls = 0

        async def stream(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                yield ToolCall(
                    id="call_1",
                    name="list_documents",
                    arguments={"limit": 3, "page": 1},
                )
            else:
                yield "done"

    async def fake_fetch_memory(prompt):
        return []

    async def fake_fetch_context(prompt):
        return []

    async def fake_tool_execute(self, **kwargs):
        captured.update(kwargs)
        return {"documents": [], "total": 0}

    monkeypatch.setattr("app.ai.pipeline.executor.get_llm_provider", lambda provider: FakeProvider())
    monkeypatch.setattr(AIExecutionPipeline, "_fetch_implicit_memory", fake_fetch_memory)
    monkeypatch.setattr(AIExecutionPipeline, "_fetch_implicit_context", fake_fetch_context)
    monkeypatch.setattr("app.ai.pipeline.executor.ToolExecutor.execute", fake_tool_execute)

    chunks = []
    async for chunk in pipeline.execute("List my docs"):
        chunks.append(chunk)

    assert chunks == ["done"]
    assert captured["db"] is fake_db
    assert captured["tool_name"] == "list_documents"
    assert captured["tool_args"] == {"limit": 3, "page": 1}
    assert captured["user_id"] == user.id
    assert captured["organization_id"] == org.id
    assert captured["agent_id"] == "CEO"

    tool_message = fake_db.add.call_args_list[-1].args[0]
    assert json.loads(tool_message.content) == {"documents": [], "total": 0}


@pytest.mark.asyncio
async def test_pipeline_reports_provider_initialization_error(monkeypatch):
    user, org, conversation = _model_pair()
    pipeline = AIExecutionPipeline(AsyncMock(), user, org, conversation)

    def fail_provider(provider):
        raise ValueError("GEMINI_API_KEY must be provided")

    monkeypatch.setattr("app.ai.pipeline.executor.get_llm_provider", fail_provider)

    chunks = []
    async for chunk in pipeline.execute("Hello"):
        chunks.append(chunk)

    assert chunks == [
        "Error: Could not initialize AI provider 'google': GEMINI_API_KEY must be provided"
    ]
