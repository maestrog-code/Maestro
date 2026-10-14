"""
Pydantic v2 schemas for Organizations and Memberships.

Serialization-only — no business logic here.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ─── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Organization name must be at least 3 characters.")
        if len(v) > 120:
            raise ValueError("Organization name must be at most 120 characters.")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError("Organization name must be at least 3 characters.")
            if len(v) > 120:
                raise ValueError("Organization name must be at most 120 characters.")
        return v


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


# ─── Member Invite ─────────────────────────────────────────────────────────────

class MemberInvite(BaseModel):
    email: EmailStr
    role_id: Optional[UUID] = None


# ─── Member Role Update ────────────────────────────────────────────────────────

class MemberRoleUpdate(BaseModel):
    role_id: UUID


# ─── Member Response ──────────────────────────────────────────────────────────

class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: Optional[UUID]
    status: str
    created_at: datetime
