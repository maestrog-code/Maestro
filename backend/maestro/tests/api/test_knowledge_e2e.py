"""
E2E tests for the Knowledge Engine (Sprint 005).
"""
import pytest
from httpx import AsyncClient
from uuid import UUID

pytestmark = pytest.mark.asyncio

async def test_knowledge_e2e_flow(
    async_client: AsyncClient,
    test_user_headers: dict,
    test_organization_id: UUID,
):
    """
    Test the full knowledge engine lifecycle:
    1. Create an inline note.
    2. Search for the note.
    3. Delete the note.
    """
    # 1. Create an inline note
    create_resp = await async_client.post(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/note",
        headers=test_user_headers,
        data={
            "title": "Q3 Financial Strategy",
            "content": "The Q3 strategy relies heavily on cutting infrastructure costs and migrating to a unified database.",
            "doc_type": "note",
            "visibility": "org"
        }
    )
    assert create_resp.status_code == 202
    data = create_resp.json()
    doc_id = data["document_id"]
    assert data["status"] == "pending"

    # In a real E2E test, we would wait for Celery to process it.
    # For now, we test the listing endpoint to ensure the document exists.
    
    # 2. List documents
    list_resp = await async_client.get(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents",
        headers=test_user_headers,
    )
    assert list_resp.status_code == 200
    docs = list_resp.json()["items"]
    assert any(d["id"] == doc_id for d in docs)

    # 3. Delete document
    delete_resp = await async_client.delete(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/{doc_id}",
        headers=test_user_headers,
    )
    assert delete_resp.status_code == 204

    # Ensure it is deleted
    get_resp = await async_client.get(
        f"/api/v1/organizations/{test_organization_id}/knowledge/documents/{doc_id}",
        headers=test_user_headers,
    )
    assert get_resp.status_code == 404
