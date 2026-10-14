import asyncio
import logging
import uuid
from datetime import date, datetime
from sqlalchemy import select, and_, delete

from app.workers.celery_app import celery_app
from app.core.database import CelerySessionLocal
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User
from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.modules.business.models import Briefing, BriefingStatus
from app.ai.pipeline.executor import AIExecutionPipeline
from app.ai.schemas import MessageRole

logger = logging.getLogger(__name__)


def run_async_synchronously(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "running event loop" in str(e):
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        raise


@celery_app.task(name="business.generate_daily_briefings")
def generate_daily_briefings() -> dict:
    """
    Beat-scheduled task that iterates through all active organizations
    and spawns a sub-task to generate the daily morning executive briefing.
    """
    return run_async_synchronously(_generate_daily_briefings_async())


async def _generate_daily_briefings_async() -> dict:
    async with CelerySessionLocal() as db:
        # Fetch all non-deleted organizations
        query = select(Organization).where(Organization.is_deleted == False)
        result = await db.execute(query)
        orgs = result.scalars().all()

        logger.info("Found %d organizations to generate briefings for.", len(orgs))
        for org in orgs:
            generate_org_daily_briefing.delay(str(org.id))

        return {"status": "enqueued", "org_count": len(orgs)}


@celery_app.task(
    name="business.generate_org_daily_briefing",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def generate_org_daily_briefing(self, organization_id: str) -> dict:
    """
    Asynchronously runs the multi-agent execution pipeline headlessly
    for a specific organization to generate their morning brief.
    """
    try:
        return run_async_synchronously(_generate_org_daily_briefing_async(organization_id))
    except Exception as exc:
        logger.exception("Failed to generate daily briefing for org %s. Retrying...", organization_id)
        # Record failure trace in the DB before retrying
        run_async_synchronously(_mark_briefing_failed(organization_id, str(exc)))
        raise self.retry(exc=exc, countdown=60)


async def _generate_org_daily_briefing_async(organization_id: str) -> dict:
    org_uuid = uuid.UUID(organization_id)
    today = date.today()

    async with CelerySessionLocal() as db:
        # 1. Fetch organization
        query = select(Organization).where(Organization.id == org_uuid)
        res = await db.execute(query)
        org = res.scalar_one_or_none()
        if not org:
            logger.error("Organization %s not found.", organization_id)
            return {"status": "skipped", "reason": f"organization {organization_id} not found"}

        # 2. Get or create today's Briefing record (processing status)
        query = select(Briefing).where(and_(Briefing.organization_id == org_uuid, Briefing.date == today))
        res = await db.execute(query)
        briefing = res.scalar_one_or_none()
        if not briefing:
            briefing = Briefing(
                id=uuid.uuid4(),
                organization_id=org_uuid,
                date=today,
                status=BriefingStatus.PROCESSING
            )
            db.add(briefing)
        else:
            briefing.status = BriefingStatus.PROCESSING
            briefing.content = None
        await db.commit()
        await db.refresh(briefing)

        try:
            # 3. Locate or create System Conversation (wipe messages on start to avoid context leak)
            from sqlalchemy.orm import selectinload
            query = select(Conversation).options(selectinload(Conversation.messages)).where(
                and_(
                    Conversation.organization_id == org_uuid,
                    Conversation.title == "System Daily Briefing Conversation"
                )
            )
            res = await db.execute(query)
            conversation = res.scalar_one_or_none()
            if not conversation:
                conversation = Conversation(
                    id=uuid.uuid4(),
                    organization_id=org_uuid,
                    title="System Daily Briefing Conversation"
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                conversation.messages = []
            else:
                # Wipe historical messages in this system conversation
                await db.execute(delete(AIMessageModel).where(AIMessageModel.conversation_id == conversation.id))
                await db.commit()

            # 4. Fetch the first active user belonging to the organization
            query = (
                select(User)
                .join(OrganizationMember, User.id == OrganizationMember.user_id)
                .where(
                    and_(
                        OrganizationMember.organization_id == org_uuid,
                        User.is_deleted == False
                    )
                )
                .limit(1)
            )
            res = await db.execute(query)
            user = res.scalar_one_or_none()

            # Fallback: fetch any active user if org member isn't found
            if not user:
                res = await db.execute(select(User).where(User.is_deleted == False).limit(1))
                user = res.scalar_one_or_none()

            # Extreme Fallback: create System Automator user if DB is completely empty
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    email="system@maestro.app",
                    first_name="System",
                    last_name="Automator",
                    is_active=True
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)

            # 5. Build prompt and run the headless AIExecutionPipeline
            prompt = (
                f"Today's date is {today.isoformat()}. You are to compile the daily morning executive summary. "
                "You must review financial performance (revenue, COGS, OPEX, gross and net profit margins) "
                "and inspect active projects and team resource allocations. "
                "Delegate tasks to your CFO (for financial analysis) and COO (for resource allocations). "
                "Provide a polished, concise morning brief in markdown including Gross/Net margins and any overallocation warnings."
            )

            pipeline = AIExecutionPipeline(db, user, org, conversation)
            async for _ in pipeline.execute(prompt):
                pass  # headless execution, simply run generator to completion

            # 6. Retrieve the final response message from the pipeline
            query = (
                select(AIMessageModel)
                .where(
                    and_(
                        AIMessageModel.conversation_id == conversation.id,
                        AIMessageModel.role == MessageRole.ASSISTANT
                    )
                )
                .order_by(AIMessageModel.created_at.desc())
                .limit(1)
            )
            res = await db.execute(query)
            last_message = res.scalar_one_or_none()

            if last_message and last_message.content:
                briefing.content = last_message.content
                briefing.status = BriefingStatus.COMPLETED
            else:
                briefing.status = BriefingStatus.FAILED
                briefing.content = "Error: CEO agent did not produce a summary response."
            
            await db.commit()
            return {"status": "completed", "organization_id": organization_id, "briefing_id": str(briefing.id)}

        except Exception as inner_exc:
            logger.exception("Error executing briefing pipeline for org %s", organization_id)
            briefing.status = BriefingStatus.FAILED
            briefing.content = f"Execution failed:\n{str(inner_exc)}"
            await db.commit()
            raise


async def _mark_briefing_failed(organization_id: str, error_msg: str):
    """Fallback helper to ensure failure is registered on database errors."""
    org_uuid = uuid.UUID(organization_id)
    today = date.today()
    async with CelerySessionLocal() as db:
        query = select(Briefing).where(and_(Briefing.organization_id == org_uuid, Briefing.date == today))
        res = await db.execute(query)
        briefing = res.scalar_one_or_none()
        if briefing:
            briefing.status = BriefingStatus.FAILED
            briefing.content = f"System error:\n{error_msg}"
            await db.commit()
