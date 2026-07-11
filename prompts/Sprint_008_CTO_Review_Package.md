# MAESTRO — Sprint 008 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 008 is on branch `feature/agent-orchestration-engine`.
This document contains every implementation file in full, exactly as committed.

---

## `app/ai/pipeline/executor.py`

```py
import json
import logging
import time
from uuid import UUID
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.ai.agents.registry import registry
from app.ai.providers.factory import get_llm_provider
from app.ai.prompts.builder import PromptBuilder, PromptContext
from app.ai.pipeline.tool_executor import ToolExecutor
from app.ai.schemas import (
    AIMessage, MessageRole, ToolCall,
    StreamEvent, TokenEvent, OrchestrationEvent, TaskUpdateEvent, ToolCallEvent
)
from app.ai.telemetry.logger import telemetry
from app.ai.safety.guards import AISafetyGuards
from app.modules.ai_conversations.models import AIMessageModel, Conversation
from app.modules.users.models import User
from app.modules.organizations.models import Organization

# Import tools for dynamic instantiation
from app.ai.tools.knowledge_tools import SearchKnowledgeBaseTool, GetDocumentTool, ListDocumentsTool
from app.ai.tools.memory_tools import RememberFactTool, ForgetFactTool
from app.ai.tools.orchestration_tools import DelegateTaskTool, UpdateTaskStatusTool
from app.ai.embedding.google import GeminiEmbeddingProvider
from app.modules.knowledge.services import KnowledgeService

logger = logging.getLogger(__name__)


class AIExecutionPipeline:
    def __init__(self, db: AsyncSession, user: User, organization: Organization, conversation: Conversation):
        self.db = db
        self.user = user
        self.organization = organization
        self.conversation = conversation

    async def _resolve_tools(self, tool_names: List[str]) -> List[Any]:
        """Instantiate tools based on names, injecting required context."""
        instances = []
        knowledge_service = KnowledgeService(self.db)

        for name in tool_names:
            if name == "search_knowledge_base":
                instances.append(SearchKnowledgeBaseTool(knowledge_service, self.organization.id, self.user.id))
            elif name == "get_document":
                instances.append(GetDocumentTool(knowledge_service, self.organization.id))
            elif name == "list_documents":
                instances.append(ListDocumentsTool(knowledge_service, self.organization.id))
            elif name == "remember_fact":
                instances.append(RememberFactTool())
            elif name == "forget_fact":
                instances.append(ForgetFactTool())
            elif name == "delegate_task":
                instances.append(DelegateTaskTool())
            elif name == "update_task_status":
                instances.append(UpdateTaskStatusTool())
        return instances

    async def _fetch_implicit_context(self, user_prompt: str) -> List[Dict[str, Any]]:
        """
        Implicit RAG: run a quick search on the user's prompt to inject highly relevant
        context directly into the system prompt, saving a tool call round-trip.
        """
        try:
            knowledge_service = KnowledgeService(self.db)
            search_resp = await knowledge_service.search(
                org_id=self.organization.id,
                user=self.user,
                query=user_prompt,
                top_k=3 # Only top 3 for implicit context
            )
            
            documents = []
            for r in search_resp.results:
                # Basic relevance threshold
                if r.score >= 0.70:
                    documents.append({
                        "title": r.document_title,
                        "content": r.content
                    })
            return documents
        except Exception as e:
            # Don't fail the chat if RAG errors
            logger.exception("Implicit RAG failed: %s", e)
            return []

    async def _fetch_implicit_memory(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Fetch highly relevant long-term memory for implicit injection."""
        try:
            from app.modules.memory.services import MemoryService
            memory_service = MemoryService(self.db, embedding_provider=GeminiEmbeddingProvider())
            search_resp = await memory_service.search(
                organization_id=self.organization.id,
                query=user_prompt,
                top_k=5,
                context="implicit_prompt_injection"
            )
            
            memories = []
            for m in search_resp:
                memories.append({
                    "memory_type": m.memory_type.value,
                    "content": m.content
                })
            return memories
        except Exception as e:
            logger.warning("Implicit memory fetch failed: %s", e)
            return []

    async def execute(
        self,
        user_prompt: str,
        current_depth: int = 0,
        parent_message_id: Optional[UUID] = None,
        target_agent: str = "CEO",
        history_messages: Optional[List[AIMessage]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Executes the AI conversation stream.
        """
        start_time = time.time()
        
        # 1. Select Agent
        agent_id = target_agent or self.conversation.active_agent or "CEO"
        agent = registry.get_agent(agent_id)
        if not agent:
            yield f"Error: Agent '{agent_id}' not found in registry."
            return

        try:
            provider = get_llm_provider(agent.provider)
        except Exception as e:
            yield f"Error: Could not initialize AI provider '{agent.provider}': {e}"
            return

        # 2. Safety Guards
        try:
            AISafetyGuards.check_prompt_injection(user_prompt)
            user_prompt = AISafetyGuards.check_pii_redaction(user_prompt)
        except Exception as e:
            yield f"Safety guard blocked execution: {e}"
            return

        # 3. Implicit Retrieval
        implicit_memories = await self._fetch_implicit_memory(user_prompt)
        implicit_docs = await self._fetch_implicit_context(user_prompt)

        # 4. Build Prompt Context using structured PromptContext
        context = PromptContext(
            user=self.user,
            organization=self.organization,
            documents=implicit_docs,
            memories=implicit_memories
        )
        system_content = PromptBuilder.render(agent.system_prompt_template, context)

        # Inject Summarization at Source if this is a delegated task
        if current_depth > 0:
            system_content += "\n\nCRITICAL DIRECTIVE: You are executing a delegated sub-task for the CEO. You MUST return a concise, highly-structured executive summary of your findings. Do NOT return raw data rows unless explicitly requested."

        messages = [AIMessage(role=MessageRole.SYSTEM, content=system_content)]

        if history_messages is None:
            history_messages = []
            history_models = self.conversation.messages[-10:] # last 10 messages
            for msg_model in history_models:
                tool_calls = None
                if msg_model.tool_calls:
                    tool_calls = [ToolCall(**tc) for tc in msg_model.tool_calls]
                history_messages.append(AIMessage(
                    role=msg_model.role,
                    content=msg_model.content,
                    name=msg_model.name,
                    tool_calls=tool_calls,
                    tool_call_id=msg_model.tool_call_id
                ))
        
        messages.extend(history_messages)
            
        # Add the new user prompt
        messages.append(AIMessage(role=MessageRole.USER, content=user_prompt))

        # Persist User Prompt
        user_msg_model = AIMessageModel(
            conversation_id=self.conversation.id,
            role=MessageRole.USER,
            content=user_prompt,
            parent_message_id=parent_message_id
        )
        self.db.add(user_msg_model)
        await self.db.commit()

        # 6. Tool Setup
        agent_tools = await self._resolve_tools(agent.tools)
        tool_executor = ToolExecutor(tools=agent_tools)
        tool_schemas = tool_executor.get_tool_schemas()

        iteration_count = 0
        max_iterations = ai_settings.MAX_TOOL_CALLS

        while iteration_count < max_iterations:
            iteration_count += 1

            # 7. Stream from Provider
            full_response_text = ""
            tool_calls_to_execute = []

            async for chunk in provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                if isinstance(chunk, str):
                    full_response_text += chunk
                    yield TokenEvent(text=chunk)
                elif isinstance(chunk, ToolCall):
                    tool_calls_to_execute.append(chunk)

            # We exit after the first stream response since full tool calling loop is disabled for Sprint 004
            # UNLESS there are tool calls, in which case we execute them and loop (Sprint 007 upgrade)
            assistant_msg_model = AIMessageModel(
                conversation_id=self.conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response_text,
                parent_message_id=parent_message_id,
                tool_calls=[tc.model_dump() for tc in tool_calls_to_execute] if tool_calls_to_execute else None
            )
            self.db.add(assistant_msg_model)
            await self.db.commit()

            messages.append(AIMessage(
                role=MessageRole.ASSISTANT,
                content=full_response_text,
                tool_calls=tool_calls_to_execute if tool_calls_to_execute else None
            ))

            if not tool_calls_to_execute:
                break

            # Execute Tools
            for tc in tool_calls_to_execute:
                if tc.name == "update_task_status":
                    yield TaskUpdateEvent(
                        step=tc.arguments.get("step", ""),
                        status=tc.arguments.get("status", ""),
                        notes=tc.arguments.get("notes")
                    )
                
                if tc.name == "delegate_task":
                    # Hard Guardrail
                    if current_depth >= 3:
                        tool_result = "Error: Maximum delegation depth (3) exceeded."
                    else:
                        target = tc.arguments.get("target_agent", "CEO")
                        instructions = tc.arguments.get("instructions", "")
                        original_goal = tc.arguments.get("original_goal", "")
                        
                        combined_prompt = f"Original Goal: {original_goal}\n\nTask Instructions:\n{instructions}" if original_goal else instructions

                        yield OrchestrationEvent(
                            target_agent=target,
                            message=f"Delegating sub-task to {target}..."
                        )

                        sub_task_result = ""
                        
                        try:
                            # Recursively call the pipeline without passing raw history
                            async for sub_chunk in self.execute(
                                user_prompt=combined_prompt,
                                current_depth=current_depth + 1,
                                parent_message_id=user_msg_model.id,
                                target_agent=target,
                                history_messages=[] # Force context isolation
                            ):
                                if isinstance(sub_chunk, TokenEvent):
                                    sub_task_result += sub_chunk.text
                                else:
                                    yield sub_chunk
                        except Exception as e:
                            logger.error("Delegated sub-task failed: %s", e)
                            sub_task_result = f"Error: The delegated task to {target} failed unexpectedly. Details: {e}"

                        # Middle-out Truncation
                        if len(sub_task_result) > ai_settings.DELEGATION_MAX_CHARS:
                            half = ai_settings.DELEGATION_MAX_CHARS // 2 - 50
                            sub_task_result = sub_task_result[:half] + "\n\n...[TRUNCATED]...\n\n" + sub_task_result[-half:]

                        tool_result = sub_task_result
                else:
                    if tc.name != "update_task_status":
                        yield ToolCallEvent(tool_name=tc.name, status="started")
                    
                    # Normal tool execution
                    try:
                        tool_result = await tool_executor.execute(
                            db=self.db,
                            tool_name=tc.name,
                            tool_args=tc.arguments,
                            user_id=self.user.id,
                            organization_id=self.organization.id,
                            agent_id=agent.id,
                        )
                        if tc.name != "update_task_status":
                            yield ToolCallEvent(tool_name=tc.name, status="completed")
                    except Exception as e:
                        logger.error("Tool execution failed: %s", e)
                        tool_result = f"Error executing tool {tc.name}: {e}"
                        if tc.name != "update_task_status":
                            yield ToolCallEvent(tool_name=tc.name, status="failed")

                if not isinstance(tool_result, str):
                    tool_result = json.dumps(tool_result, default=str)

                tool_msg_model = AIMessageModel(
                    conversation_id=self.conversation.id,
                    role=MessageRole.TOOL,
                    content=tool_result,
                    tool_call_id=tc.id,
                    name=tc.name,
                    parent_message_id=parent_message_id
                )
                self.db.add(tool_msg_model)
                await self.db.commit()

                messages.append(AIMessage(
                    role=MessageRole.TOOL,
                    content=tool_result,
                    tool_call_id=tc.id,
                    name=tc.name
                ))

            # 8. Telemetry
            latency = (time.time() - start_time) * 1000
            telemetry.log_execution(
                request_id=f"req_{self.conversation.id}",
                organization_id=self.organization.id,
                conversation_id=self.conversation.id,
                agent=agent.id,
                provider=provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
            )
```

---

## `app/ai/schemas.py`

```py
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
```

---

## `app/modules/ai_conversations/services.py`

```py
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
            # SSE format leveraging Pydantic models
            yield f"event: {chunk.event_type}\ndata: {chunk.model_dump_json()}\n\n"
        yield "event: end\ndata: {}\n\n"
```

---

## `app/ai/agents/registry.py`

```py
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.ai_settings import ai_settings


class AgentDefinition(BaseModel):
    id: str
    name: str
    version: str
    system_prompt_template: str
    tools: List[str]  # List of tool names
    provider: str
    temperature: float
    max_tokens: int
    enabled: bool


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentDefinition]:
        return [agent for agent in self._agents.values() if agent.enabled]


registry = AgentRegistry()

# Import definitions to register them
from app.ai.agents.definitions import ceo, cfo
```

---

## `app/core/ai_settings.py`

```py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """
    AI-specific configuration for MAESTRO's AI Executive Engine.
    Values can be overridden by environment variables with the `AI_` prefix.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="AI_"
    )

    # Provider & Model Settings
    DEFAULT_PROVIDER: str = "google"
    GOOGLE_MODEL: str = "gemini-2.5-pro"

    # Execution Limits
    MAX_TOOL_CALLS: int = 8
    MAX_CONTEXT_TOKENS: int = 32000

    # Model Generation Defaults
    DEFAULT_TEMPERATURE: float = 0.2
    STREAMING: bool = True

    # Memory Ranking & Vector Config
    EMBEDDING_DIMENSIONS: int = 768

    # Memory Weights
    MEMORY_SIMILARITY_WEIGHT: float = 0.4
    MEMORY_IMPORTANCE_WEIGHT: float = 0.2
    MEMORY_CONFIDENCE_WEIGHT: float = 0.2
    MEMORY_RECENCY_WEIGHT: float = 0.1
    MEMORY_ACCESS_WEIGHT: float = 0.1
    MEMORY_RETRIEVAL_LIMIT: int = 10

    # Memory Thresholds (Sprint 006.5)
    MEMORY_MERGE_THRESHOLD: float = 0.90
    MEMORY_CONFLICT_THRESHOLD: float = 0.82
    MEMORY_RETRIEVAL_THRESHOLD: float = 0.60
    MEMORY_ARCHIVE_THRESHOLD: float = 0.10  # Importance below this triggers archival
    MEMORY_UNCERTAIN_CONFIDENCE_PENALTY: float = 0.80  # Multiplier on confidence for UNCERTAIN resolution
    MEMORY_RECENCY_WINDOW_DAYS: int = 30   # Days over which recency score decays to 0
    MEMORY_SEARCH_POOL_SIZE: int = 30
    MEMORY_MAX_ACCESS_NORMALIZATION: int = 10  # Access count at which access_freq score reaches 1.0

    # Memory Decay Rate (lambda for exponential decay: e^(-lambda * days))
    # A lambda of 0.01 means memory importance decays by ~1% per day if untouched
    MEMORY_DECAY_RATE: float = 0.01

    # Sprint 005 — Embeddings
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_BATCH_SIZE: int = 10  # chunks per API call to avoid rate limits

    # Sprint 005 — Knowledge / RAG
    VECTOR_SEARCH_TOP_K: int = 5
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 80
    KNOWLEDGE_MAX_CONTEXT_CHARS: int = 8000  # max chars injected into system prompt

    # Sprint 007 — Orchestration
    DELEGATION_MAX_CHARS: int = 4000

ai_settings = AISettings()
```

---

## `app/ai/agents/definitions/ceo.py`

```py
from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

ceo_agent = AgentDefinition(
    id="CEO",
    name="Chief Executive Officer",
    version="1.0",
    system_prompt_template="ceo_system",
    tools=[
        "search_knowledge_base",
        "get_document",
        "list_documents",
        "remember_fact",
        "forget_fact",
        "delegate_task",
        "update_task_status"
    ],
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(ceo_agent)
```

---

## `app/ai/prompts/templates/ceo_system.md`

```text
You are the Chief Executive Officer (CEO) of {{company_name}}.
Your role is to orchestrate resources, plan strategically, and communicate clearly.

## Context
**Organization Name:** {{organization_name}}
**Current User:** {{user_first_name}} {{user_last_name}}

## Objectives
- Drive high-level strategic alignment
- Make clear, decisive choices based on available data
- Delegate operational tasks to specialized tools or agents

## Guidelines
- Be concise and authoritative but supportive.
- Do not make assumptions about data you haven't fetched. Use tools to verify metrics.
- For multi-step or highly complex tasks, use the `update_task_status` tool to maintain a scratchpad of your plan and current progress.
- Delegate specialized domain analysis directly to sub-agents (e.g., CFO for finance, COO for operations).
- Keep responses professional and focused on business outcomes.
- Cite your sources when using organizational knowledge.

## Past Memory
The following historical context, facts, and preferences are highly relevant to the current conversation:
{{memory_context}}

## Internal Knowledge
The following internal documents and knowledge base articles may be relevant to the user's request:
{{knowledge_context}}
```

---

## `app/ai/tools/orchestration_tools.py`

```py
import logging
from typing import Any
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.ai.agents.registry import registry

logger = logging.getLogger(__name__)

class DelegateTaskInput(BaseModel):
    target_agent: str = Field(
        ...,
        description="The role name of the specialized agent to delegate to (e.g., 'CFO', 'COO', 'CTO')."
    )
    instructions: str = Field(
        ...,
        description="Detailed instructions and context for the sub-task. Be as explicit as possible."
    )
    original_goal: str = Field(
        ...,
        description="The original overall goal or user request that prompted this delegation, to provide full context."
    )


class DelegateTaskOutput(BaseModel):
    result: str

class DelegateTaskTool(BaseTool):
    """
    Allows a Supervisor agent (like the CEO) to delegate a sub-task to a specialized agent.
    """
    name: str = "delegate_task"
    description: str = (
        "Delegate a sub-task to a specialized agent. Use this when you need domain-specific "
        "analysis (e.g., financial from the CFO) to answer the user's request."
    )
    input_schema = DelegateTaskInput
    output_schema = DelegateTaskOutput

    async def execute(self, target_agent: str, instructions: str, **kwargs) -> Any:
        """
        The actual execution of this tool is intercepted by the AIExecutionPipeline
        to handle recursion, context building, and database persistence.
        This method serves as a fallback or placeholder if invoked directly outside the pipeline.
        """
        if not registry.get_agent(target_agent):
            return f"Error: Agent '{target_agent}' not found in the registry."

        logger.warning("delegate_task was executed without pipeline interception.")
        return "Sub-task delegated successfully."

class UpdateTaskStatusInput(BaseModel):
    step: str = Field(..., description="The name or description of the current planning step.")
    status: str = Field(..., description="The status of the step (e.g., 'IN_PROGRESS', 'COMPLETED', 'PENDING', 'FAILED').")
    notes: str = Field(..., description="Internal scratchpad notes, findings, or next actions.")

class UpdateTaskStatusOutput(BaseModel):
    result: str

class UpdateTaskStatusTool(BaseTool):
    """
    Allows an agent to maintain a scratchpad or state tracking for multi-step tasks.
    """
    name: str = "update_task_status"
    description: str = (
        "Maintain a scratchpad of your current plan and progress. Use this to explicitly track "
        "what steps you have completed, what you are currently doing, and what comes next."
    )
    input_schema = UpdateTaskStatusInput
    output_schema = UpdateTaskStatusOutput

    async def execute(self, step: str, status: str, notes: str, **kwargs) -> Any:
        # Just returning it so the LLM has it in the context window
        return f"Task State Updated.\nStep: {step}\nStatus: {status}\nNotes: {notes}"
```

---

## `app/modules/ai_conversations/models.py`

```py
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

    # Added in Sprint 007 for sub-agent orchestration
    parent_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=True, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    # Self-referential relationships for the adjacency list
    parent: Mapped[Optional["AIMessageModel"]] = relationship(
        "AIMessageModel", remote_side="AIMessageModel.id", backref="children"
    )
```

---

## `alembic/versions/007_add_parent_message_id.py`

```py
"""add parent_message_id

Revision ID: 007
Revises: 006
Create Date: 2026-07-09 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ai_messages', sa.Column('parent_message_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_ai_messages_parent_message_id'), 'ai_messages', ['parent_message_id'], unique=False)
    op.create_foreign_key('fk_ai_messages_parent_message_id', 'ai_messages', 'ai_messages', ['parent_message_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_ai_messages_parent_message_id', 'ai_messages', type_='foreignkey')
    op.drop_index(op.f('ix_ai_messages_parent_message_id'), table_name='ai_messages')
    op.drop_column('ai_messages', 'parent_message_id')
    # ### end Alembic commands ###
```

---

