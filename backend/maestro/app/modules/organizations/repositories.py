"""
Organization repositories — persistence only.

No authorization, no business rules, no commits from services.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.permissions.models import Role
from app.shared.utils.repository import BaseRepository


# ─── Organization Repository ───────────────────────────────────────────────────

class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self) -> None:
        super().__init__(Organization)

    async def get_by_slug(
        self, db: AsyncSession, slug: str
    ) -> Optional[Organization]:
        result = await db.execute(
            select(Organization).where(
                Organization.slug == slug,
                Organization.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, db: AsyncSession, slug: str) -> bool:
        result = await db.execute(
            select(Organization.id).where(Organization.slug == slug)
        )
        return result.first() is not None

    async def list_for_user(
        self, db: AsyncSession, user_id: UUID
    ) -> List[Organization]:
        """Return all non-deleted orgs that the user is an active member of."""
        result = await db.execute(
            select(Organization)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
                OrganizationMember.is_deleted == False,  # noqa: E712
                Organization.is_deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())


# ─── Organization Member Repository ───────────────────────────────────────────

class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    def __init__(self) -> None:
        super().__init__(OrganizationMember)

    async def find_member(
        self, db: AsyncSession, organization_id: UUID, user_id: UUID
    ) -> Optional[OrganizationMember]:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self,
        db: AsyncSession,
        *,
        organization_id: UUID,
        user_id: UUID,
        role_id: Optional[UUID] = None,
        status: str = "active",
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role_id=role_id,
            status=status,
        )
        db.add(member)
        return member  # caller flushes/commits inside the transaction

    async def update_member_role(
        self,
        db: AsyncSession,
        *,
        member: OrganizationMember,
        role_id: UUID,
    ) -> OrganizationMember:
        member.role_id = role_id
        db.add(member)
        return member

    async def list_org_members(
        self, db: AsyncSession, organization_id: UUID
    ) -> List[OrganizationMember]:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())


# ─── Role Repository ───────────────────────────────────────────────────────────

class RoleRepository(BaseRepository[Role]):
    def __init__(self) -> None:
        super().__init__(Role)

    async def find_by_name(
        self, db: AsyncSession, organization_id: UUID, name: str
    ) -> Optional[Role]:
        result = await db.execute(
            select(Role).where(
                Role.organization_id == organization_id,
                Role.name == name,
                Role.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def find_owner_role(
        self, db: AsyncSession, organization_id: UUID
    ) -> Optional[Role]:
        return await self.find_by_name(db, organization_id, "owner")


# ─── Singletons ───────────────────────────────────────────────────────────────

organization_repository = OrganizationRepository()
member_repository = OrganizationMemberRepository()
role_repository = RoleRepository()
