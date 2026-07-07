import json
import time
from uuid import UUID
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.ai.agents.registry import registry
from app.ai.providers.google import GoogleProvider
from app.ai.prompts.builder import PromptBuilder
from app.ai.pipeline.tool_executor import ToolExecutor
from app.ai.schemas import AIMessage, MessageRole, ToolCall
from app.ai.telemetry.logger import telemetry
from app.ai.safety.guards import AISafetyGuards
from app.modules.ai_conversations.models import AIMessageModel, Conversation
from app.modules.users.models import User
from app.modules.organizations.models import Organization


class AIExecutionPipeline:
    def __init__(self, db: AsyncSession, user: User, organization: Organization, conversation: Conversation):
        self.db = db
        self.user = user
        self.organization = organization
        self.conversation = conversation
        # Currently only supporting GoogleProvider
        self.provider = GoogleProvider()

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

        # 3. Build Prompt Context
        context = {
            "company_name": self.organization.name,
            "organization_name": self.organization.name,
            "user_first_name": self.user.first_name,
            "user_last_name": self.user.last_name,
        }
        system_content = PromptBuilder.render(agent.system_prompt_template, context)

        # 4. Load Conversation History (last N messages)
        # Simplified: We just fetch existing messages and format them
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

        # 5. Tool Setup
        # For Sprint 004, we assume tools are registered in a global place or imported.
        # Stubbing empty tools for now since actual business tools will be added later.
        tool_executor = ToolExecutor(tools=[])
        tool_schemas = tool_executor.get_tool_schemas()

        iteration_count = 0
        max_iterations = ai_settings.MAX_TOOL_CALLS

        while iteration_count < max_iterations:
            iteration_count += 1
            
            # 6. Stream from Provider
            full_response_text = ""
            async for chunk in self.provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                full_response_text += chunk
                yield chunk

            # We also need the full non-streamed response to check for tool calls.
            # In many SDKs (like Google's new genai SDK), tool calls might not stream.
            # For robustness in this implementation, we will use generate() if we suspect tool calls,
            # but since we are yielding stream chunks above, we assume no tool calls during streaming.
            # Let's call generate() to handle potential tool calls if needed, OR just rely on generate()
            # for the entire loop and yield fake chunks. 
            # To actually stream and handle tools, the provider interface gets complex.
            # For Sprint 004, we'll do a simple fallback: if the stream ends, we fetch the final structured LLMResponse.
            
            # Since we streamed, let's pretend there are no tool calls for this iteration 
            # unless we implement a custom stream parser.
            # For now, we will break after one stream iteration.
            
            assistant_msg_model = AIMessageModel(
                conversation_id=self.conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response_text
            )
            self.db.add(assistant_msg_model)
            await self.db.commit()

            # 7. Telemetry
            latency = (time.time() - start_time) * 1000
            telemetry.log_execution(
                request_id=f"req_{self.conversation.id}",
                organization_id=self.organization.id,
                conversation_id=self.conversation.id,
                agent=agent.id,
                provider=self.provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0, # metrics require generate() instead of stream() in many SDKs
                output_tokens=0,
            )
            
            break # Exit loop as we don't have tool calling logic in the stream path yet

