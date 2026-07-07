import json
import time
from uuid import UUID
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.ai.agents.registry import registry
from app.ai.providers.google import GoogleProvider
from app.ai.prompts.builder import PromptBuilder, PromptContext
from app.ai.pipeline.tool_executor import ToolExecutor
from app.ai.schemas import AIMessage, MessageRole, ToolCall
from app.ai.telemetry.logger import telemetry
from app.ai.safety.guards import AISafetyGuards
from app.modules.ai_conversations.models import AIMessageModel, Conversation
from app.modules.users.models import User
from app.modules.organizations.models import Organization

# Import tools for dynamic instantiation
from app.ai.tools.knowledge_tools import SearchKnowledgeBaseTool, GetDocumentTool, ListDocumentsTool
from app.modules.knowledge.services import KnowledgeService


class AIExecutionPipeline:
    def __init__(self, db: AsyncSession, user: User, organization: Organization, conversation: Conversation):
        self.db = db
        self.user = user
        self.organization = organization
        self.conversation = conversation
        # Currently only supporting GoogleProvider for chat
        self.provider = GoogleProvider()

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
            import logging
            logging.getLogger(__name__).warning(f"Implicit RAG failed: {e}")
            return []

    async def _fetch_implicit_memory(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Fetch highly relevant long-term memory for implicit injection."""
        try:
            from app.modules.memory.services import MemoryService
            memory_service = MemoryService(self.db)
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
            import logging
            logging.getLogger(__name__).warning(f"Implicit memory fetch failed: {e}")
            return []

    async def execute(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """
        Executes the AI conversation stream.
        """
        start_time = time.time()
        
        # 1. Select Agent
        agent_id = self.conversation.active_agent or "CEO"
        agent = registry.get_agent(agent_id)
        if not agent:
            yield f"Error: Agent '{agent_id}' not found in registry."
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

        # 5. Load Conversation History (last N messages)
        history_models = self.conversation.messages[-10:] # last 10 messages
        
        messages = [AIMessage(role=MessageRole.SYSTEM, content=system_content)]
        for msg_model in history_models:
            tool_calls = None
            if msg_model.tool_calls:
                tool_calls = [ToolCall(**tc) for tc in msg_model.tool_calls]
            messages.append(AIMessage(
                role=msg_model.role,
                content=msg_model.content,
                name=msg_model.name,
                tool_calls=tool_calls,
                tool_call_id=msg_model.tool_call_id
            ))
            
        # Add the new user prompt
        messages.append(AIMessage(role=MessageRole.USER, content=user_prompt))

        # Persist User Prompt
        user_msg_model = AIMessageModel(
            conversation_id=self.conversation.id,
            role=MessageRole.USER,
            content=user_prompt
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
            async for chunk in self.provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                full_response_text += chunk
                yield chunk

            # We exit after the first stream response since full tool calling loop is disabled for Sprint 004
            assistant_msg_model = AIMessageModel(
                conversation_id=self.conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response_text
            )
            self.db.add(assistant_msg_model)
            await self.db.commit()

            # 8. Telemetry
            latency = (time.time() - start_time) * 1000
            telemetry.log_execution(
                request_id=f"req_{self.conversation.id}",
                organization_id=self.organization.id,
                conversation_id=self.conversation.id,
                agent=agent.id,
                provider=self.provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
            )
            
            break


