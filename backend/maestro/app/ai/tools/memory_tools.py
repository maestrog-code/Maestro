"""
Tools for the AI Memory System.
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.ai.embedding.google import GeminiEmbeddingProvider
from app.modules.memory.services import MemoryService
from app.modules.memory.models import MemoryType, MemorySource


class RememberFactInput(BaseModel):
    content: str = Field(..., description="The exact fact, goal, or preference to remember.")
    memory_type: MemoryType = Field(default=MemoryType.FACT, description="The category of this memory.")
    importance: float = Field(default=0.7, ge=0.0, le=1.0, description="Importance of the memory (0.0 to 1.0).")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this memory (0.0 to 1.0).")


class RememberFactOutput(BaseModel):
    success: bool
    memory_id: str
    message: str


class RememberFactTool(BaseTool):
    name = "remember_fact"
    description = "Explicitly save a highly important fact, goal, or user preference into long-term memory immediately."
    input_schema = RememberFactInput
    output_schema = RememberFactOutput

    async def execute(self, db, organization_id: UUID, user_id: UUID, content: str, memory_type: MemoryType, importance: float, confidence: float, **kwargs) -> Any:
        service = MemoryService(db, embedding_provider=GeminiEmbeddingProvider())
        
        try:
            mem = await service.add_memory(
                organization_id=organization_id,
                content=content,
                memory_type=memory_type,
                source=MemorySource.TOOL,
                importance=importance,
                confidence=confidence,
                user_id=user_id,
                agent_id=kwargs.get("agent_id")
            )
            return {
                "success": True,
                "memory_id": str(mem.id),
                "message": f"Successfully remembered {memory_type.value}."
            }
        except Exception as e:
            return {
                "success": False,
                "memory_id": "",
                "message": f"Failed to save memory: {str(e)}"
            }


class ForgetFactInput(BaseModel):
    memory_id: str = Field(..., description="The UUID of the memory to forget/archive.")


class ForgetFactOutput(BaseModel):
    success: bool
    message: str


class ForgetFactTool(BaseTool):
    name = "forget_fact"
    description = "Archives a memory so it will no longer be retrieved."
    input_schema = ForgetFactInput
    output_schema = ForgetFactOutput

    async def execute(self, db, organization_id: UUID, memory_id: str, **kwargs) -> Any:
        service = MemoryService(db)
        try:
            mem_uuid = UUID(memory_id)
            success = await service.archive_memory(organization_id, mem_uuid)
            if success:
                return {"success": True, "message": "Memory archived."}
            else:
                return {"success": False, "message": "Memory not found."}
        except ValueError:
            return {"success": False, "message": "Invalid memory_id format."}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
