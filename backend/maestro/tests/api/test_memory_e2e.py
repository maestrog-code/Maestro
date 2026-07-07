import pytest
from httpx import AsyncClient
from uuid import UUID

from app.modules.memory.models import MemoryType, MemoryStatus, MemorySource
from app.modules.organizations.models import Organization
from app.modules.users.models import User

# Assuming standard test fixtures are available from conftest.py
@pytest.fixture
def memory_payload():
    return {
        "content": "The CEO prefers quarterly reports formatted as tables.",
        "memory_type": "preference",
        "importance_score": 0.8,
        "confidence_score": 0.9,
        "source": "manual",
        "agent_id": "CEO"
    }

@pytest.mark.asyncio
async def test_create_memory(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test manual memory creation via the API."""
    response = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == memory_payload["content"]
    assert data["memory_type"] == memory_payload["memory_type"]
    assert data["status"] == "active"
    assert "id" in data

@pytest.mark.asyncio
async def test_list_memories(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test listing memories."""
    # Create one first
    await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    
    response = await async_client.get(
        f"/api/v1/organizations/{test_organization.id}/memories",
        headers=authenticated_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["content"] == memory_payload["content"]

@pytest.mark.asyncio
async def test_update_memory_to_archived(
    async_client: AsyncClient,
    test_organization: Organization,
    test_user: User,
    authenticated_headers: dict,
    memory_payload: dict
):
    """Test updating a memory, specifically soft-deleting it."""
    create_resp = await async_client.post(
        f"/api/v1/organizations/{test_organization.id}/memories",
        json=memory_payload,
        headers=authenticated_headers
    )
    memory_id = create_resp.json()["id"]
    
    update_resp = await async_client.patch(
        f"/api/v1/organizations/{test_organization.id}/memories/{memory_id}",
        json={"status": "archived"},
        headers=authenticated_headers
    )
    
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "archived"
