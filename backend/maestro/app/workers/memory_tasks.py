"""
Celery tasks for async memory extraction.
"""
import json
import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
from google.genai import types

from app.core.database import SessionLocal
from app.core.ai_settings import ai_settings
from app.modules.memory.schemas import MemoryExtractionList
from app.modules.memory.services import MemoryService
from app.modules.memory.models import MemorySource

logger = logging.getLogger(__name__)


async def _extract_memories_async(conversation_id: UUID, organization_id: UUID, transcript: str):
    """Async inner function to perform the extraction."""
    async with SessionLocal() as db:
        service = MemoryService(db)
        
        # We use Gemini's structured output to ensure we get valid MemoryExtraction objects
        client = genai.Client()
        
        system_instruction = (
            "You are a memory extraction engine. Review the following conversation transcript "
            "and extract any new, important facts, user preferences, decisions, goals, profiles, "
            "warnings, tasks, relationships, or constraints."
            "\nIgnore pleasantries. Focus on long-term context that an AI executive would need "
            "to remember for future interactions."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=MemoryExtractionList.model_json_schema()
        )
        
        response = await client.aio.models.generate_content(
            model=ai_settings.GOOGLE_MODEL,
            contents=[f"Transcript:\n{transcript}"],
            config=config
        )
        
        if not response.text:
            logger.warning(f"No text generated for conversation {conversation_id} extraction.")
            return

        try:
            extraction_data = json.loads(response.text)
            extraction_list = MemoryExtractionList(**extraction_data)
        except Exception as e:
            logger.error(f"Failed to parse memory extraction JSON: {e}")
            return
            
        for ext in extraction_list.memories:
            try:
                # add_memory automatically handles deduplication and status resolution via embedding check
                await service.add_memory(
                    organization_id=organization_id,
                    content=ext.content,
                    memory_type=ext.memory_type,
                    source=MemorySource.CONVERSATION,
                    importance=ext.importance,
                    confidence=ext.confidence
                )
            except Exception as e:
                logger.error(f"Failed to save extracted memory: {e}")
                
        logger.info(f"Extracted and processed {len(extraction_list.memories)} memories.")


@shared_task(bind=True, max_retries=3)
def extract_conversation_memories_task(self, conversation_id_str: str, organization_id_str: str, transcript: str):
    """
    Celery task to extract memories from a completed conversation chunk.
    """
    import asyncio
    
    conversation_id = UUID(conversation_id_str)
    organization_id = UUID(organization_id_str)
    
    try:
        # Run the async extraction inside the synchronous Celery worker
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_extract_memories_async(conversation_id, organization_id, transcript))
        else:
            loop.run_until_complete(_extract_memories_async(conversation_id, organization_id, transcript))
    except Exception as exc:
        logger.error(f"Error in extract_conversation_memories_task: {exc}")
        raise self.retry(exc=exc, countdown=60)
