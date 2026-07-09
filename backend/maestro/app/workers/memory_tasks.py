"""
Celery tasks for async memory extraction.
"""
import json
import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import CelerySessionLocal
from app.core.ai_settings import ai_settings
from app.modules.memory.schemas import MemoryExtractionList
from app.modules.memory.services import MemoryService
from app.modules.memory.models import MemorySource, MemoryStatus

logger = logging.getLogger(__name__)


async def _extract_memories_async(conversation_id: UUID, organization_id: UUID, transcript: str):
    """Async inner function to perform the extraction."""
    async with CelerySessionLocal() as db:
        from app.ai.providers.google import GoogleProvider
        from app.ai.embedding.google import GeminiEmbeddingProvider
        from app.ai.schemas import MessageRole, AIMessage

        # Instantiate dependencies
        llm = GoogleProvider()
        embedder = GeminiEmbeddingProvider()
        service = MemoryService(db, embedding_provider=embedder)

        system_instruction = (
            "You are a memory extraction engine. Review the following conversation transcript "
            "and extract any new, important facts, user preferences, decisions, goals, profiles, "
            "warnings, tasks, relationships, or constraints."
            "\nIgnore pleasantries. Focus on long-term context that an AI executive would need "
            "to remember for future interactions.\n"
            "Return a JSON object containing a 'memories' list."
        )

        messages = [
            AIMessage(role=MessageRole.SYSTEM, content=system_instruction),
            AIMessage(role=MessageRole.USER, content=f"Transcript:\n{transcript}")
        ]

        try:
            response = await llm.generate(
                messages=messages,
                temperature=0.1,
                response_schema=MemoryExtractionList.model_json_schema()
            )

            if not response.content:
                logger.warning(f"No text generated for conversation {conversation_id} extraction.")
                return

            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]

            extraction_data = json.loads(text.strip())
            extraction_list = MemoryExtractionList(**extraction_data)
        except Exception as e:
            logger.exception(f"Failed to extract memory JSON using LLM provider: {e}")
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
                    confidence=ext.confidence,
                    llm_provider=llm,
                    is_async_extraction=True
                )
            except Exception as e:
                logger.exception(f"Failed to save extracted memory: {e}")

        logger.info(f"Extracted and processed {len(extraction_list.memories)} memories.")


async def _decay_memories_async():
    """Async inner function for decaying memories."""
    from app.modules.memory.models import AgentMemory
    from app.modules.memory.policy import MemoryPolicy
    from sqlalchemy import select

    async with CelerySessionLocal() as db:
        service = MemoryService(db, embedding_provider=None) # embedder not needed for decay

        # We need to decay ACTIVE memories that haven't been accessed recently (e.g. 24h)
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        stmt = select(AgentMemory).where(
            AgentMemory.status == MemoryStatus.ACTIVE,
            AgentMemory.last_accessed < cutoff
        )
        result = await db.execute(stmt)
        memories = result.scalars().all()

        decayed_count = 0
        archived_count = 0
        batch_size = 100
        current_batch = 0

        try:
            for mem in memories:
                new_importance = MemoryPolicy.calculate_decayed_importance(mem)
                if new_importance != mem.importance_score:
                    mem.importance_score = new_importance
                    decayed_count += 1

                    if MemoryPolicy.should_archive(mem, new_importance):
                        mem.status = MemoryStatus.ARCHIVED
                        archived_count += 1

                    await service.repo.update(mem)
                    current_batch += 1

                    if current_batch >= batch_size:
                        await db.commit()
                        current_batch = 0

            if current_batch > 0:
                await db.commit()

            logger.info(
                "Memory decay complete. decayed=%d archived=%d",
                decayed_count, archived_count
            )
        except Exception:
            await db.rollback()
            raise

@shared_task(bind=True, max_retries=3)
def decay_memories_task(self):
    """
    Celery task to apply exponential decay to memory importance.
    """
    import asyncio
    try:
        asyncio.run(_decay_memories_async())
    except Exception as exc:
        logger.exception(f"Error in decay_memories_task: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def extract_conversation_memories_task(self, conversation_id_str: str, organization_id_str: str, transcript: str):
    """
    Celery task to extract memories from a completed conversation chunk.
    """
    import asyncio

    conversation_id = UUID(conversation_id_str)
    organization_id = UUID(organization_id_str)

    try:
        asyncio.run(_extract_memories_async(conversation_id, organization_id, transcript))
    except Exception as exc:
        logger.exception(f"Error in extract_conversation_memories_task: {exc}")
        raise self.retry(exc=exc, countdown=60)
