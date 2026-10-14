from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.shared.utils.repository import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self) -> None:
        super().__init__(Conversation)

    async def get_with_messages(self, db: AsyncSession, conversation_id: UUID) -> Optional[Conversation]:
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_for_org(self, db: AsyncSession, organization_id: UUID) -> List[Conversation]:
        result = await db.execute(
            select(Conversation).where(
                Conversation.organization_id == organization_id,
                Conversation.is_deleted == False
            ).order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())


class AIMessageRepository(BaseRepository[AIMessageModel]):
    def __init__(self) -> None:
        super().__init__(AIMessageModel)

    async def list_for_conversation(self, db: AsyncSession, conversation_id: UUID) -> List[AIMessageModel]:
        result = await db.execute(
            select(AIMessageModel).where(
                AIMessageModel.conversation_id == conversation_id,
                AIMessageModel.is_deleted == False
            ).order_by(AIMessageModel.created_at.asc())
        )
        return list(result.scalars().all())


conversation_repository = ConversationRepository()
ai_message_repository = AIMessageRepository()
