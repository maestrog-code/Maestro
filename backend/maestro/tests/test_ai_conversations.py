import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.modules.users.models import User
from app.modules.organizations.models import Organization
from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.ai.schemas import MessageRole

@pytest.fixture
def mock_google_provider():
    with patch("app.ai.pipeline.executor.GoogleProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        
        async def mock_stream(*args, **kwargs):
            yield "Hello, "
            yield "I am "
            yield "an AI."

        mock_instance.stream = mock_stream
        yield mock_instance

@pytest.mark.asyncio
async def test_ai_chat_creates_conversation(
    async_client: AsyncClient,
    db: AsyncSession,
    test_user: User,
    test_organization: Organization,
    mock_google_provider,
    auth_headers
):
    response = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/ai/chat",
        json={"message": "Who are you?", "agent": "CEO"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    content = ""
    async for line in response.aiter_lines():
        content += line + "\n"
        
    assert "data: Hello, " in content
    assert "data: I am " in content
    assert "data: an AI." in content
    
    # Verify conversation was created
    result = await db.execute(select(Conversation).where(Conversation.organization_id == test_organization.id))
    convs = result.scalars().all()
    assert len(convs) == 1
    assert convs[0].active_agent == "CEO"

    # Verify messages were saved
    result_msgs = await db.execute(select(AIMessageModel).where(AIMessageModel.conversation_id == convs[0].id))
    messages = result_msgs.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert messages[0].content == "Who are you?"
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == "Hello, I am an AI."
