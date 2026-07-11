import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import uuid

from app.main import app
from app.models.base import Base
from app.dependencies.database import get_db
from app.modules.users.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from app.core.security.jwt import create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
)

from app.core import database as db_core
db_core.CelerySessionLocal = TestSessionLocal
db_core.AsyncSessionLocal = TestSessionLocal



@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        from app.modules.users.models import User  # noqa: F401
        from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
        from app.modules.permissions.models import Role, Permission, RolePermission  # noqa: F401
        from app.core.auth.models import RefreshToken, AuditLog  # noqa: F401
        from app.modules.ai_conversations.models import Conversation, AIMessageModel  # noqa: F401
        from app.modules.business.models import Project, Resource, ProjectAllocation, Invoice, Transaction, Briefing  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture()
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def async_client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_user(db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test_user@maestro.app",
        first_name="Test",
        last_name="User",
        hashed_password="hashed_placeholder",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_organization(db: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Organization",
        slug="test-organization"
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture()
async def authenticated_headers(test_user: User, test_organization: Organization, db: AsyncSession):
    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        user_id=test_user.id,
        role_id=None,
        status="active"
    )
    db.add(member)
    await db.commit()

    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def auth_headers(authenticated_headers):
    return authenticated_headers
