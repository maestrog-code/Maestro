from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import OrganizationPermissionService
from app.modules.ai_conversations.schemas import ChatRequest
from app.modules.ai_conversations.services import AIConversationService
from app.ai.agents.registry import registry

router = APIRouter(prefix="/organizations/{organization_id}/ai", tags=["AI Conversations"])

@router.post("/chat", response_class=StreamingResponse)
async def chat_with_ai(
    organization_id: UUID,
    request: ChatRequest,
    conversation_id: Optional[UUID] = Query(None, description="Optional ID of existing conversation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends a message to the AI agent and returns an SSE stream.
    If conversation_id is not provided in query params, a new conversation is created.
    """
    # 1. Authorization
    # The member will be verified and the organization returned
    organization = await OrganizationPermissionService.require_member(
        db, organization_id, current_user.id
    )

    # 2. Get or Create Conversation
    conversation = await AIConversationService.get_or_create_conversation(
        db, organization_id, conversation_id
    )

    # Update active agent if requested
    if request.agent:
        agent_def = registry.get_agent(request.agent)
        if agent_def:
            conversation.active_agent = request.agent
            db.add(conversation)
            await db.commit()

    # 3. Return Streaming Response
    return StreamingResponse(
        AIConversationService.chat_stream(db, current_user, organization, conversation, request.message),
        media_type="text/event-stream"
    )
