"""
API Router for Agent Memory Management.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import OrganizationPermissionService
from app.modules.memory.services import MemoryService
from app.modules.memory.schemas import MemoryCreate, MemoryUpdate, MemoryResponse, MemoryListResponse

router = APIRouter(prefix="/organizations/{organization_id}/memories", tags=["Memory"])


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    organization_id: UUID,
    memory: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually add a memory for the organization."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = MemoryService(db)
    
    new_memory = await service.add_memory(
        organization_id=organization_id,
        content=memory.content,
        memory_type=memory.memory_type,
        source=memory.source,
        importance=memory.importance_score,
        confidence=memory.confidence_score,
        user_id=current_user.id,
        agent_id=memory.agent_id
    )
    return new_memory


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    organization_id: UUID,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List agent memories for an organization."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = MemoryService(db)
    
    items, total = await service.repo.list_by_organization(organization_id, page, page_size)
    return MemoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    organization_id: UUID,
    memory_id: UUID,
    updates: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a memory or archive it (soft delete)."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = MemoryService(db)
    
    memory = await service.repo.get(organization_id, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    if updates.content is not None:
        memory.content = updates.content
    if updates.memory_type is not None:
        memory.memory_type = updates.memory_type
    if updates.status is not None:
        memory.status = updates.status
    if updates.importance_score is not None:
        memory.importance_score = updates.importance_score
    if updates.confidence_score is not None:
        memory.confidence_score = updates.confidence_score
        
    memory = await service.repo.update(memory)
    await db.commit()
    return memory
