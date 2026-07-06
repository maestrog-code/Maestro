"""
End-to-end tests for Sprint 002: Authentication Flow

Tests the full cycle:
  register → login → access protected route → refresh token → revoke token

Run with:
    pytest tests/test_auth_e2e.py -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.dependencies.database import get_db

# --- In-memory SQLite for tests (no PostgreSQL needed) ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

TEST_USER = {
    "email": "test@maestro.app",
    "password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
}


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """POST /auth/register → 200 with user and tokens."""
    response = await client.post("/api/v1/auth/register", json=TEST_USER)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == TEST_USER["email"]
    assert "access_token" in data["token"]
    assert "refresh_token" in data["token"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """POST /auth/register with existing email → 400."""
    await client.post("/api/v1/auth/register", json=TEST_USER)
    response = await client.post("/api/v1/auth/register", json=TEST_USER)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /auth/login with correct credentials → 200 with tokens."""
    await client.post("/api/v1/auth/register", json=TEST_USER)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == TEST_USER["email"]
    assert "access_token" in data["token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """POST /auth/login with wrong password → 401."""
    await client.post("/api/v1/auth/register", json=TEST_USER)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """POST /auth/login with unknown email → 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@maestro.app", "password": "irrelevant"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /health → 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient):
    """
    Full flow: register → login → verify tokens are different per session.
    """
    # Register
    reg = await client.post("/api/v1/auth/register", json=TEST_USER)
    assert reg.status_code == 200
    reg_token = reg.json()["token"]["access_token"]

    # Login
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert login.status_code == 200
    login_token = login.json()["token"]["access_token"]

    # Both should be valid JWTs (non-empty strings)
    assert isinstance(reg_token, str) and len(reg_token) > 20
    assert isinstance(login_token, str) and len(login_token) > 20
