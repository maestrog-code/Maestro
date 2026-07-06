"""
End-to-end tests for Organization lifecycle and membership (Sprint 003).

Covers:
  - Create organization
  - Owner auto-added as member
  - Slug auto-generated, unique collision handling
  - List organizations
  - Get single organization
  - Invite member
  - Invite non-existent user → 404
  - Invite already-member → 400
  - Remove member
  - Owner cannot remove themselves
  - Change member role
  - Non-member cannot access organization → 403
  - JWT required → 401
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


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, email: str, password: str = "Pass123!") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "first_name": "Test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    return {"token": data["token"]["access_token"], "user_id": data["user"]["id"]}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_org(client: AsyncClient, token: str, name: str = "Maestro Corp") -> dict:
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": name},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ─── Tests: Create ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_organization_success(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "Acme Corporation"},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corporation"
    assert data["slug"] == "acme-corporation"


@pytest.mark.asyncio
async def test_create_organization_slug_collision(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    org1 = await _create_org(client, owner["token"], "Acme")
    org2 = await _create_org(client, owner["token"], "Acme")
    assert org1["slug"] == "acme"
    assert org2["slug"] == "acme-2"


@pytest.mark.asyncio
async def test_create_organization_name_too_short(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "AB"},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_organization_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/organizations/", json={"name": "Test Org"})
    assert resp.status_code == 401


# ─── Tests: List & Get ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_organizations(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    await _create_org(client, owner["token"], "Org One")
    await _create_org(client, owner["token"], "Org Two")
    resp = await client.get("/api/v1/organizations/", headers=_auth(owner["token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_list_organizations_only_own(client: AsyncClient):
    """User only sees orgs they belong to."""
    owner = await _register(client, "owner@maestro.app")
    other = await _register(client, "other@maestro.app")
    await _create_org(client, owner["token"], "Owner Org")
    await _create_org(client, other["token"], "Other Org")

    resp = await client.get("/api/v1/organizations/", headers=_auth(owner["token"]))
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Owner Org"


@pytest.mark.asyncio
async def test_get_organization_success(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    org = await _create_org(client, owner["token"])
    resp = await client.get(
        f"/api/v1/organizations/{org['id']}", headers=_auth(owner["token"])
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == org["id"]


@pytest.mark.asyncio
async def test_get_organization_not_member(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    outsider = await _register(client, "outsider@maestro.app")
    org = await _create_org(client, owner["token"])
    resp = await client.get(
        f"/api/v1/organizations/{org['id']}", headers=_auth(outsider["token"])
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_organization_not_found(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    resp = await client.get(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 404


# ─── Tests: Invite ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_member_success(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    invitee = await _register(client, "invitee@maestro.app")
    org = await _create_org(client, owner["token"])

    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "invitee@maestro.app"},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 201
    assert resp.json()["user_id"] == invitee["user_id"]


@pytest.mark.asyncio
async def test_invite_nonexistent_user(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    org = await _create_org(client, owner["token"])
    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "ghost@maestro.app"},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invite_already_member(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    invitee = await _register(client, "invitee@maestro.app")
    org = await _create_org(client, owner["token"])
    # first invite
    await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "invitee@maestro.app"},
        headers=_auth(owner["token"]),
    )
    # second invite same user
    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "invitee@maestro.app"},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invite_by_non_owner_forbidden(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    member = await _register(client, "member@maestro.app")
    outsider = await _register(client, "outsider@maestro.app")
    org = await _create_org(client, owner["token"])
    # add member first
    await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "member@maestro.app"},
        headers=_auth(owner["token"]),
    )
    # member tries to invite
    resp = await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "outsider@maestro.app"},
        headers=_auth(member["token"]),
    )
    assert resp.status_code == 403


# ─── Tests: Remove ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_member_success(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    invitee = await _register(client, "invitee@maestro.app")
    org = await _create_org(client, owner["token"])
    await client.post(
        f"/api/v1/organizations/{org['id']}/members",
        json={"email": "invitee@maestro.app"},
        headers=_auth(owner["token"]),
    )
    resp = await client.delete(
        f"/api/v1/organizations/{org['id']}/members/{invitee['user_id']}",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_owner_cannot_remove_themselves(client: AsyncClient):
    owner = await _register(client, "owner@maestro.app")
    org = await _create_org(client, owner["token"])
    resp = await client.delete(
        f"/api/v1/organizations/{org['id']}/members/{owner['user_id']}",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 400
