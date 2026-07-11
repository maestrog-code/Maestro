import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch
from sqlalchemy import select, and_

from app.models.base import Base
from app.modules.users.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.modules.business.models import Project, Resource, ProjectAllocation, Transaction, Invoice, Briefing, BriefingStatus, TransactionType, TransactionCategory
from app.workers.celery_app import celery_app
from app.workers.business_tasks import generate_daily_briefings
from app.ai.schemas import MessageRole


@pytest.fixture(autouse=True)
def configure_celery_eager():
    old_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = old_eager


@pytest.fixture
def mock_google_provider():
    with patch("app.ai.pipeline.executor.get_llm_provider") as mock_get_provider:
        mock_provider_instance = mock_get_provider.return_value
        
        async def mock_stream(*args, **kwargs):
            yield "## Morning Executive Briefing\n\n"
            yield "**Financial Performance**:\n"
            yield "- Gross Margin: 60.0%\n"
            yield "- Net Margin: 30.0%\n\n"
            yield "**Resource Utilization**:\n"
            yield "- Alice Developer: 80% (Lead Engineer)\n"

        mock_provider_instance.stream = mock_stream
        yield mock_provider_instance


@pytest.mark.asyncio
async def test_generate_daily_briefings_flow(db, mock_google_provider):
    # 1. Seed database with active organization, member, transactions, and allocations
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    
    # Org
    org = Organization(id=org_id, name="Automated Test Company", slug="automated-test-company")
    db.add(org)
    
    # User
    user = User(
        id=uuid.uuid4(),
        email="ceo@maestro.app",
        first_name="CEO",
        last_name="Owner",
        hashed_password="placeholder",
        is_active=True
    )
    db.add(user)
    await db.commit()
    
    # Org Membership
    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        status="active"
    )
    db.add(member)
    
    # Seed transactions
    tx_revenue = Transaction(
        id=uuid.uuid4(), organization_id=org_id, amount=Decimal("10000.00"),
        type=TransactionType.INCOME, category=TransactionCategory.REVENUE, date=date.today() - timedelta(days=1),
        description="Revenue inflow"
    )
    tx_cogs = Transaction(
        id=uuid.uuid4(), organization_id=org_id, amount=Decimal("4000.00"),
        type=TransactionType.EXPENSE, category=TransactionCategory.COGS_INFRASTRUCTURE, date=date.today() - timedelta(days=1),
        description="Infra cost"
    )
    db.add_all([tx_revenue, tx_cogs])
    
    # Seed project & allocation
    proj = Project(
        id=uuid.uuid4(), organization_id=org_id, name="Test Project",
        status="active", budget=Decimal("50000.00"), start_date=date.today() - timedelta(days=30)
    )
    db.add(proj)
    await db.commit()
    
    res = Resource(
        id=uuid.uuid4(), organization_id=org_id, name="Alice Developer",
        role="Engineer", cost_rate=Decimal("1500.00")
    )
    db.add(res)
    await db.commit()
    
    alloc = ProjectAllocation(
        id=uuid.uuid4(), organization_id=org_id, resource_id=res.id, project_id=proj.id,
        allocation_percentage=80, role="Lead Engineer"
    )
    db.add(alloc)
    await db.commit()

    # 2. Trigger the daily briefings Celery task (running synchronously via eager mode)
    task_res = generate_daily_briefings.delay()
    assert task_res.status == "SUCCESS"

    # 3. Verify Briefing record was generated in the DB
    query = select(Briefing).where(and_(Briefing.organization_id == org_id, Briefing.date == date.today()))
    res_query = await db.execute(query)
    briefing = res_query.scalar_one_or_none()
    
    assert briefing is not None
    assert briefing.status == BriefingStatus.COMPLETED
    assert "Morning Executive Briefing" in briefing.content
    assert "Gross Margin: 60.0%" in briefing.content
    assert "Alice Developer: 80%" in briefing.content
    
    # 4. Verify system conversation history has exactly 2 messages
    query_msgs = select(AIMessageModel).join(Conversation).where(
        and_(
            Conversation.organization_id == org_id,
            Conversation.title == "System Daily Briefing Conversation"
        )
    )
    res_msgs = await db.execute(query_msgs)
    messages = res_msgs.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == briefing.content
