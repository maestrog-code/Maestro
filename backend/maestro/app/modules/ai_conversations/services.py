from uuid import UUID
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_conversations.models import Conversation
from app.modules.ai_conversations.repositories import conversation_repository
from app.ai.pipeline.executor import AIExecutionPipeline
from app.modules.users.models import User
from app.modules.organizations.models import Organization


class AIConversationService:
    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession, organization_id: UUID, conversation_id: Optional[UUID] = None
    ) -> Conversation:
        if conversation_id:
            conv = await conversation_repository.get_with_messages(db, conversation_id)
            if conv:
                return conv
        
        conv = Conversation(organization_id=organization_id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def chat_stream(
        db: AsyncSession, user: User, organization: Organization, conversation: Conversation, prompt: str
    ) -> AsyncGenerator[str, None]:
        pipeline = AIExecutionPipeline(db, user, organization, conversation)
        async for chunk in pipeline.execute(prompt):
            # SSE format
            yield f"data: {chunk}\n\n"
        yield "event: end\ndata: \n\n"
