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
