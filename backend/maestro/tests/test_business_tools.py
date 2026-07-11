import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.modules.users.models import User  # noqa: F401
from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
from app.modules.permissions.models import Role, Permission, RolePermission  # noqa: F401
from app.core.auth.models import RefreshToken, AuditLog  # noqa: F401
from app.modules.ai_conversations.models import Conversation, AIMessageModel  # noqa: F401
from app.modules.business.models import (
    Project, Resource, ProjectAllocation, Invoice, Transaction,
    ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory
)
from app.ai.tools.business_tools import FetchFinancialMetricsTool, CheckResourceAllocationTool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_fetch_financial_metrics_tool():
    org_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        # Create organization
        org = Organization(id=org_id, name="Test Org", slug="test-org")
        session.add(org)

        # Seed Transactions
        transactions = [
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("10000.00"),
                type=TransactionType.INCOME, category=TransactionCategory.REVENUE,
                date=date(2025, 6, 15), description="Milestone payout"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("1500.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.COGS_INFRASTRUCTURE,
                date=date(2025, 6, 10), description="AWS billing"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("2500.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.COGS_CONTRACTORS,
                date=date(2025, 6, 28), description="Contractor billing"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("3000.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.OPEX_RENT,
                date=date(2025, 6, 1), description="Rent"
            ),
        ]
        session.add_all(transactions)
        await session.commit()

    async with TestSessionLocal() as session:
        tool = FetchFinancialMetricsTool(session, org_id)
        
        # Test full range
        res = await tool.execute(start_date=date(2025, 6, 1), end_date=date(2025, 6, 30))
        metrics = res["metrics"]
        
        assert metrics["total_revenue"] == 10000.00
        assert metrics["total_cogs"] == 4000.00  # 1500 + 2500
        assert metrics["total_opex"] == 3000.00  # Rent
        assert metrics["gross_profit"] == 6000.00  # 10000 - 4000
        assert metrics["net_profit"] == 3000.00  # 6000 - 3000
        assert metrics["gross_margin_percentage"] == 60.00  # (6000 / 10000) * 100
        assert metrics["net_margin_percentage"] == 30.00  # (3000 / 10000) * 100
        assert metrics["category_breakdown"]["revenue"] == 10000.00
        assert metrics["category_breakdown"]["cogs_infrastructure"] == 1500.00


@pytest.mark.asyncio
async def test_check_resource_allocation_tool():
    org_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        # Create organization
        org = Organization(id=org_id, name="Test Org", slug="test-org")
        session.add(org)

        # Seed projects
        p1 = Project(
            id=uuid.uuid4(), organization_id=org_id, name="Project A",
            status=ProjectStatus.ACTIVE, budget=Decimal("50000.00"),
            start_date=date(2025, 1, 1)
        )
        session.add(p1)

        # Seed resources
        r1 = Resource(
            id=uuid.uuid4(), organization_id=org_id, name="Alice",
            role="Dev", cost_rate=Decimal("1500.00")
        )
        session.add(r1)

        # Seed allocations
        alloc = ProjectAllocation(
            id=uuid.uuid4(), organization_id=org_id,
            resource_id=r1.id, project_id=p1.id,
            allocation_percentage=80, role="Lead Engineer"
        )
        session.add(alloc)
        await session.commit()

    async with TestSessionLocal() as session:
        tool = CheckResourceAllocationTool(session, org_id)
        res = await tool.execute()
        allocations = res["allocations"]

        assert len(allocations) == 1
        item = allocations[0]
        assert item["resource_name"] == "Alice"
        assert item["resource_role"] == "Dev"
        assert item["project_name"] == "Project A"
        assert item["project_status"] == "active"
        assert item["allocation_percentage"] == 80
        assert item["allocation_role"] == "Lead Engineer"
