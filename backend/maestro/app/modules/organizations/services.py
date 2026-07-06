"""
Organization Service — all business logic lives here.

Rules enforced here:
- Multi-step org creation happens in a single transaction
- Slug uniqueness with collision fallback
- Authorization helpers (require_member, require_owner) centralize checks
- Domain events published after successful writes
- Repositories are never committed from outside this service
"""
import re
import uuid
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.dispatcher import dispatcher
from app.core.events.types import EventType
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.organizations.repositories import (
    member_repository,
    organization_repository,
    role_repository,
)
from app.modules.organizations.schemas import (
    MemberInvite,
    MemberRoleUpdate,
    OrganizationCreate,
)
from app.modules.permissions.models import Role
from app.modules.users.repositories import user_repository


# ─── Slug helpers ──────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


async def _generate_unique_slug(db: AsyncSession, name: str) -> str:
    """
    Generate a slug and increment if needed:
      Acme → acme → acme-2 → acme-3
    Never exposes DB uniqueness errors to callers.
    """
    base = _slugify(name)
    if not await organization_repository.slug_exists(db, base):
        return base
    counter = 2
    while True:
        candidate = f"{base}-{counter}"
        if not await organization_repository.slug_exists(db, candidate):
            return candidate
        counter += 1


# ─── Authorization helpers ─────────────────────────────────────────────────────

async def _get_organization_or_404(
    db: AsyncSession, org_id: UUID
) -> Organization:
    org = await organization_repository.get(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    return org


async def require_member(
    db: AsyncSession, organization_id: UUID, user_id: UUID
) -> OrganizationMember:
    """
    Ensures the user is an active member of the organization.
    Returns the membership record.
    Raises HTTP 403 if not a member.
    """
    member = await member_repository.find_member(db, organization_id, user_id)
    if not member or member.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization.",
        )
    return member


async def require_owner(
    db: AsyncSession, organization_id: UUID, user_id: UUID
) -> OrganizationMember:
    """
    Ensures the user is the owner of the organization.
    Never compares role names in routers — this is the one place.
    Raises HTTP 403 if not the owner.
    """
    member = await require_member(db, organization_id, user_id)
    owner_role = await role_repository.find_owner_role(db, organization_id)
    if owner_role is None or member.role_id != owner_role.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have owner permissions in this organization.",
        )
    return member


# ─── Organization CRUD ─────────────────────────────────────────────────────────

async def create_organization(
    db: AsyncSession, *, creator_id: UUID, org_in: OrganizationCreate
) -> Organization:
    """
    Creates an organization in a single atomic transaction:
      1. Generate unique slug
      2. Create the organization
      3. Create an 'owner' role for this organization
      4. Add the creator as an active member with the owner role
      5. Commit once — never partially created
    """
    slug = await _generate_unique_slug(db, org_in.name)

    org = Organization(name=org_in.name, slug=slug, created_by=creator_id)
    db.add(org)
    await db.flush()  # get org.id without committing

    # Create the owner role
    owner_role = Role(
        name="owner",
        description="Full control over the organization.",
        organization_id=org.id,
        created_by=creator_id,
    )
    db.add(owner_role)
    await db.flush()  # get owner_role.id

    # Add creator as owner member
    await member_repository.add_member(
        db,
        organization_id=org.id,
        user_id=creator_id,
        role_id=owner_role.id,
        status="active",
    )

    await db.commit()
    await db.refresh(org)

    dispatcher.publish(
        EventType.ORGANIZATION_CREATED,
        {"organization_id": str(org.id), "creator_id": str(creator_id)},
    )

    return org


async def get_organization(
    db: AsyncSession, *, org_id: UUID, requesting_user_id: UUID
) -> Organization:
    """Returns an organization only if the requesting user is a member."""
    org = await _get_organization_or_404(db, org_id)
    await require_member(db, org_id, requesting_user_id)
    return org


async def list_user_organizations(
    db: AsyncSession, *, user_id: UUID
) -> List[Organization]:
    return await organization_repository.list_for_user(db, user_id)


# ─── Membership management ────────────────────────────────────────────────────

async def invite_member(
    db: AsyncSession,
    *,
    org_id: UUID,
    requesting_user_id: UUID,
    invite: MemberInvite,
) -> OrganizationMember:
    """
    Invite an existing user to an organization by email.
    Only the owner can invite.
    """
    await _get_organization_or_404(db, org_id)
    await require_owner(db, org_id, requesting_user_id)

    # Resolve invitee
    invitee = await user_repository.get_by_email(db, email=str(invite.email))
    if not invitee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email address.",
        )

    # Check not already a member
    existing = await member_repository.find_member(db, org_id, invitee.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization.",
        )

    member = await member_repository.add_member(
        db,
        organization_id=org_id,
        user_id=invitee.id,
        role_id=invite.role_id,
        status="active",
    )
    await db.commit()
    await db.refresh(member)

    dispatcher.publish(
        EventType.MEMBER_INVITED,
        {
            "organization_id": str(org_id),
            "invitee_id": str(invitee.id),
            "invited_by": str(requesting_user_id),
        },
    )

    return member


async def remove_member(
    db: AsyncSession,
    *,
    org_id: UUID,
    requesting_user_id: UUID,
    target_user_id: UUID,
) -> None:
    """
    Remove a member from an organization.
    Only the owner can remove members.
    The owner cannot remove themselves.
    """
    await _get_organization_or_404(db, org_id)
    await require_owner(db, org_id, requesting_user_id)

    if requesting_user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The organization owner cannot remove themselves.",
        )

    target_member = await member_repository.find_member(db, org_id, target_user_id)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization.",
        )

    await member_repository.soft_delete(db, id=target_member.id)

    dispatcher.publish(
        EventType.MEMBER_REMOVED,
        {
            "organization_id": str(org_id),
            "removed_user_id": str(target_user_id),
            "removed_by": str(requesting_user_id),
        },
    )


async def change_member_role(
    db: AsyncSession,
    *,
    org_id: UUID,
    requesting_user_id: UUID,
    target_user_id: UUID,
    role_update: MemberRoleUpdate,
) -> OrganizationMember:
    """
    Assign a new role to a member.
    Only the owner can change roles.
    """
    await _get_organization_or_404(db, org_id)
    await require_owner(db, org_id, requesting_user_id)

    target_member = await member_repository.find_member(db, org_id, target_user_id)
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization.",
        )

    # Validate role exists and belongs to this org
    role = await role_repository.get(db, role_update.role_id)
    if not role or role.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found in this organization.",
        )

    updated = await member_repository.update_member_role(
        db, member=target_member, role_id=role_update.role_id
    )
    await db.commit()
    await db.refresh(updated)

    dispatcher.publish(
        EventType.MEMBER_ROLE_CHANGED,
        {
            "organization_id": str(org_id),
            "user_id": str(target_user_id),
            "new_role_id": str(role_update.role_id),
            "changed_by": str(requesting_user_id),
        },
    )

    return updated
