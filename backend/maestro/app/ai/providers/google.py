import os
import json
from typing import AsyncGenerator, Dict, List, Optional
from google import genai
from google.genai import types

from app.core.ai_settings import ai_settings
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import AIMessage, LLMResponse, MessageRole, ToolCall


class GoogleProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        # Initializing the client with the api_key or automatically picking up GEMINI_API_KEY from environment
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY must be provided or set in the environment.")
        self.client = genai.Client(api_key=key)
        self.model_name = ai_settings.GOOGLE_MODEL

    def _convert_messages(self, messages: List[AIMessage]) -> tuple[Optional[str], List[types.Content]]:
        """
        Extracts system instruction and converts the rest to Google GenAI Content types.
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Assuming only one system message, or combine them
                if system_instruction is None:
                    system_instruction = msg.content
                else:
                    system_instruction += "\n\n" + msg.content
            elif msg.role == MessageRole.USER:
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(msg.content)])
                )
            elif msg.role == MessageRole.ASSISTANT:
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(msg.content))
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append(
                            types.Part.from_function_call(
                                name=tc.name,
                                args=tc.arguments
                            )
                        )
                contents.append(types.Content(role="model", parts=parts))
            elif msg.role == MessageRole.TOOL:
                if msg.name is None:
                    raise ValueError("Tool name is required for tool messages.")
                try:
                    # Attempt to parse json content to pass structured data back to Gemini
                    parsed_response = json.loads(msg.content)
                except json.JSONDecodeError:
                    parsed_response = {"result": msg.content}

                contents.append(
                    types.Content(
                        role="user", # Google handles tool responses by sending a 'user' role with function_response part, or a 'function' role. In `google-genai`, function responses are usually part of a user or function role content. Wait, `types.Part.from_function_response` is typically used.
                        parts=[
                            types.Part.from_function_response(
                                name=msg.name,
                                response=parsed_response
                            )
                        ]
                    )
                )

        return system_instruction, contents

    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[types.Tool]]:
        """
        Converts generic tool schemas (JSON Schema) into Google GenAI Tool types.
        Assuming `tools` is a list of dicts formatted somewhat close to the standard JSON Schema function declaration.
        """
        if not tools:
            return None
        
        google_tools = []
        for t in tools:
            func_decl = types.FunctionDeclaration(
                name=t.get("name", ""),
                description=t.get("description", ""),
                parameters=t.get("parameters", {})
            )
            google_tools.append(types.Tool(function_declarations=[func_decl]))
        return google_tools

    async def generate(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        system_instruction, contents = self._convert_messages(messages)
        google_tools = self._convert_tools(tools)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
            tools=google_tools,
            **kwargs
        )

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config
        )

        # Parse response
        text_content = ""
        tool_calls = []

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        text_content += part.text
                    elif part.function_call:
                        tool_calls.append(
                            ToolCall(
                                id=part.function_call.name, # Usually google doesn't provide a unique call ID, using name
                                name=part.function_call.name,
                                arguments=dict(part.function_call.args) if part.function_call.args else {}
                            )
                        )
        
        return LLMResponse(
            content=text_content,
            tool_calls=tool_calls if tool_calls else None,
            input_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            output_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None
        )

    async def stream(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[Any, None]:
        system_instruction, contents = self._convert_messages(messages)
        google_tools = self._convert_tools(tools)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
            tools=google_tools,
            **kwargs
        )

        async for chunk in await self.client.aio.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config
        ):
            if chunk.text:
                yield chunk.text
            elif chunk.function_call:
                yield ToolCall(
                    id=chunk.function_call.name,
                    name=chunk.function_call.name,
                    arguments=dict(chunk.function_call.args) if chunk.function_call.args else {}
                )

    async def embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using Google's text-embedding-004 model.
        Processes texts individually (the google-genai SDK embed_content call
        accepts a single content at a time in the current version).

        Returns a list of float vectors, one per input text.
        """
        results = []
        for text in texts:
            response = await self.client.aio.models.embed_content(
                model=ai_settings.EMBEDDING_MODEL,
                contents=text,
            )
            # google-genai SDK returns EmbedContentResponse with .embeddings list
            if response.embeddings and len(response.embeddings) > 0:
                results.append(list(response.embeddings[0].values))
            else:
                # Fallback: zero vector of correct dimensions
                results.append([0.0] * ai_settings.EMBEDDING_DIMENSIONS)
        return results

