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
from app.ai.schemas import AIMessage, MessageRole, ToolCall
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
        self.provider = None

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
            import logging
            logging.getLogger(__name__).warning(f"Implicit RAG failed: {e}")
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
        target_agent: Optional[str] = None,
        history_messages: Optional[List[AIMessage]] = None
    ) -> AsyncGenerator[str, None]:
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
            self.provider = get_llm_provider(agent.provider)
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

            async for chunk in self.provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                if isinstance(chunk, str):
                    full_response_text += chunk
                    yield chunk
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
                if tc.name == "delegate_task":
                    # Hard Guardrail
                    if current_depth >= 3:
                        tool_result = "Error: Maximum delegation depth (3) exceeded."
                    else:
                        target = tc.arguments.get("target_agent", "CEO")
                        instructions = tc.arguments.get("instructions", "")
                        original_goal = tc.arguments.get("original_goal", "")
                        
                        combined_prompt = f"Original Goal: {original_goal}\n\nTask Instructions:\n{instructions}" if original_goal else instructions

                        yield f"\n\n*[Delegating sub-task to {target}...]*\n"

                        sub_task_result = ""
                        
                        try:
                            # Recursively call the pipeline without passing raw history
                            async for sub_chunk in self.execute(
                                user_prompt=combined_prompt,
                                current_depth=current_depth + 1,
                                parent_message_id=user_msg_model.id,
                                target_agent=target
                            ):
                                # We don't yield sub-chunks to the main stream to keep UI clean,
                                # or we could. Let's just accumulate the sub_task_result.
                                sub_task_result += sub_chunk
                        except Exception as e:
                            logger.error("Delegated sub-task failed: %s", e)
                            sub_task_result = f"Error: The delegated task to {target} failed unexpectedly. Details: {e}"

                        # Middle-out Truncation
                        if len(sub_task_result) > 4000:
                            half = 1950
                            sub_task_result = sub_task_result[:half] + "\n\n...[TRUNCATED for brevity]...\n\n" + sub_task_result[-half:]

                        tool_result = sub_task_result
                else:
                    # Normal tool execution
                    tool_result = await tool_executor.execute(
                        db=self.db,
                        tool_name=tc.name,
                        tool_args=tc.arguments,
                        user_id=self.user.id,
                        organization_id=self.organization.id,
                        agent_id=agent.id,
                    )

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
                provider=self.provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
            )
