import uuid
from typing import Optional, List
from sqlalchemy import String, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel
from app.ai.schemas import MessageRole

class Conversation(TimestampedModel):
    __tablename__ = "ai_conversations"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata required by CTO
    active_agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    messages: Mapped[List["AIMessageModel"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessageModel.created_at"
    )

class AIMessageModel(TimestampedModel):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_conversations.id"), index=True)
    
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole, name="message_role_enum"))
    content: Mapped[str] = mapped_column(Text, default="")
    
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True) # store list of ToolCall dicts as JSON
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
