"""
Organization Router — thin HTTP layer.

Responsibilities:
- Dependency injection
- Response models
- HTTP status codes
- Calling services

No business logic here. Authorization is in services.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.modules.organizations import services
from app.modules.organizations.schemas import (
    MemberInvite,
    MemberResponse,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationResponse,
)
from app.modules.users.models import User

router = APIRouter()


# ─── Organizations ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
)
async def create_organization(
    org_in: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.create_organization(
        db, creator_id=current_user.id, org_in=org_in
    )


@router.get(
    "/",
    response_model=list[OrganizationResponse],
    summary="List all organizations the current user belongs to",
)
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.list_user_organizations(db, user_id=current_user.id)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get a single organization",
)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.get_organization(
        db, org_id=org_id, requesting_user_id=current_user.id
    )


# ─── Members ───────────────────────────────────────────────────────────────────

@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a user to the organization by email",
)
async def invite_member(
    org_id: UUID,
    invite: MemberInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.invite_member(
        db,
        org_id=org_id,
        requesting_user_id=current_user.id,
        invite=invite,
    )


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the organization",
)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await services.remove_member(
        db,
        org_id=org_id,
        requesting_user_id=current_user.id,
        target_user_id=user_id,
    )


@router.patch(
    "/{org_id}/members/{user_id}/role",
    response_model=MemberResponse,
    summary="Change a member's role in the organization",
)
async def change_member_role(
    org_id: UUID,
    user_id: UUID,
    role_update: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.change_member_role(
        db,
        org_id=org_id,
        requesting_user_id=current_user.id,
        target_user_id=user_id,
        role_update=role_update,
    )
