"""
Conflict Resolution Service for Memory System (Sprint 006.5)
"""
import enum
import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.memory.models import AgentMemory
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import MessageRole, AIMessage

logger = logging.getLogger(__name__)


class ResolutionDecision(str, enum.Enum):
    MERGE = "MERGE"
    SUPERSEDE = "SUPERSEDE"
    NEW = "NEW"
    IGNORE = "IGNORE"
    UNCERTAIN = "UNCERTAIN"


class ResolutionResponse(BaseModel):
    decision: ResolutionDecision = Field(..., description="The decision of how to handle the candidate memory against the existing memory.")
    reasoning: str = Field(..., description="Brief explanation for the decision.")


def _extract_json(text: str) -> str:
    """
    Extracts the first JSON object from an LLM response.
    Handles cases where the provider prefixes the JSON with prose
    (e.g. "Sure! Here is the JSON: {...}").
    """
    # Try parsing directly if provider natively returned pure JSON
    try:
        json.loads(text.strip())
        return text.strip()
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences first
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.rindex("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.rindex("```", start) if "```" in text[start:] else len(text)
        return text[start:end].strip()

    # Find the first '{' and match to closing '}' while respecting quotes
    brace_start = text.find("{")
    if brace_start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escape = False

    for i, char in enumerate(text[brace_start:], start=brace_start):
        if not escape and char == '"':
            in_string = not in_string
        
        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start:i + 1]
        
        if char == '\\' and not escape:
            escape = True
        else:
            escape = False

    return text[brace_start:].strip()


class ConflictResolutionService:
    """
    Evaluates a candidate memory against existing memories using an LLM.
    `response.content` is guaranteed non-empty by the `LLMResponse` contract in app.ai.schemas.
    """

    def __init__(self, llm_provider: BaseLLMProvider):
        if llm_provider is None:
            raise ValueError("LLM provider required for async conflict resolution.")
        self.llm = llm_provider

    async def resolve(
        self,
        candidate_content: str,
        existing_memory: AgentMemory,
        _retry: bool = True
    ) -> ResolutionDecision:
        """
        Uses the LLM to determine the relationship between the candidate content
        and an existing memory. Retries once on transient failure.
        """
        system_prompt = (
            "You are an AI conflict resolution engine for a long-term memory system. "
            "Your task is to compare a NEW candidate memory against an EXISTING memory and determine their relationship.\n\n"
            "Return ONLY a JSON object — no prose, no markdown fences. Schema:\n"
            '{"decision": "<DECISION>", "reasoning": "<brief reason>"}\n\n'
            "The 'decision' field must be exactly one of:\n"
            "- MERGE: The new memory expresses the same fact (perhaps phrased differently). It does not change the truth.\n"
            "- SUPERSEDE: The new memory directly contradicts or updates the existing memory. Existing is now outdated.\n"
            "- NEW: The new memory is completely distinct despite textual similarities.\n"
            "- IGNORE: The new memory adds nothing; the existing memory covers it completely.\n"
            "- UNCERTAIN: It is unclear how they relate without more context.\n"
        )

        user_prompt = (
            f"EXISTING MEMORY:\n{existing_memory.content}\n\n"
            f"NEW CANDIDATE MEMORY:\n{candidate_content}"
        )

        messages = [
            AIMessage(role=MessageRole.SYSTEM, content=system_prompt),
            AIMessage(role=MessageRole.USER, content=user_prompt)
        ]

        try:
            # LLMResponse.content is required (str) per app.ai.schemas — safe to access directly.
            response = await self.llm.generate(messages=messages, temperature=0.0)

            raw = response.content.strip()
            extracted = _extract_json(raw)

            data = json.loads(extracted)
            result = ResolutionResponse(**data)
            return result.decision

        except Exception as e:
            if _retry:
                logger.warning(
                    f"Conflict resolution failed (will retry once): {e}"
                )
                return await self.resolve(candidate_content, existing_memory, _retry=False)

            logger.exception(f"Conflict resolution failed after retry: {e}")
            # Fallback: treat as uncertain — do not accidentally SUPERSEDE or MERGE.
            return ResolutionDecision.UNCERTAIN
