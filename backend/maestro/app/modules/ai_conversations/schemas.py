from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.ai.schemas import MessageRole, ToolCall


class AIMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    parent_message_id: Optional[UUID] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: Optional[str]
    active_agent: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    temperature: Optional[float]
    created_at: datetime
    updated_at: datetime


class ConversationWithMessagesResponse(ConversationResponse):
    messages: List[AIMessageResponse]


class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = "CEO" # Default agent based on Registry
