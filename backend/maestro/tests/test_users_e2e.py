"""
End-to-end tests for User profile endpoints (Sprint 003).

Tests:
  - GET /users/me  → authenticated user profile
  - PATCH /users/me → update first_name/last_name
  - Unauthorized access rejected with 401
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.dependencies.database import get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
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


TEST_USER = {
    "email": "user@maestro.app",
    "password": "SecurePass123!",
    "first_name": "Jane",
    "last_name": "Doe",
}


async def _register_and_token(client: AsyncClient, user: dict = None) -> str:
    user = user or TEST_USER
    reg = await client.post("/api/v1/auth/register", json=user)
    assert reg.status_code == 200
    return reg.json()["token"]["access_token"]


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == TEST_USER["email"]
    assert data["first_name"] == TEST_USER["first_name"]
    assert data["last_name"] == TEST_USER["last_name"]


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_me_first_name(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Updated"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"
    assert resp.json()["last_name"] == TEST_USER["last_name"]  # unchanged


@pytest.mark.asyncio
async def test_update_me_last_name(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"last_name": "Smith"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["last_name"] == "Smith"


@pytest.mark.asyncio
async def test_update_me_unauthorized(client: AsyncClient):
    resp = await client.patch("/api/v1/users/me", json={"first_name": "Hacker"})
    assert resp.status_code == 401
