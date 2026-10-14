from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class AIMessage(BaseModel):
    role: MessageRole
    content: str
    name: Optional[str] = None  # Used for tool names when role is "tool"
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None  # Used when role is "tool"


class LLMResponse(BaseModel):
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: Optional[str] = None


# --- SSE Event Schemas ---

class StreamEvent(BaseModel):
    """Base class for all SSE events yielded by the pipeline."""
    event_type: str = Field(exclude=True) # Used for 'event: <type>' but excluded from JSON data

class TokenEvent(StreamEvent):
    event_type: str = Field(default="token", exclude=True)
    text: str

class OrchestrationEvent(StreamEvent):
    event_type: str = Field(default="orchestration", exclude=True)
    target_agent: str
    message: str

class TaskUpdateEvent(StreamEvent):
    event_type: str = Field(default="task_update", exclude=True)
    step: str
    status: str
    notes: Optional[str] = None

class ToolCallEvent(StreamEvent):
    event_type: str = Field(default="tool_call", exclude=True)
    tool_name: str
    status: str # e.g. "started", "completed"
