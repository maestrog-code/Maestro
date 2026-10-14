import os
from pathlib import Path

BASE_DIR = Path("/Users/cuthbertrwebilumi/Desktop/Maestro/backend/maestro/app")

files = {}

# 1. Base Model Update
files["models/base.py"] = """from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class TimestampedModel(Base):
    \"\"\"Abstract base model with common fields for all tables.\"\"\"
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)
    
    # Soft delete support
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # Audit fields
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    __mapper_args__ = {
        "version_id_col": version
    }
"""

# 2. Organization Update
files["modules/organizations/models.py"] = """from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, UniqueConstraint
import uuid

from app.models.base import TimestampedModel

class Organization(TimestampedModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization")


class OrganizationMember(TimestampedModel):
    __tablename__ = "organization_members"
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")
    role = relationship("Role")
"""

# 3. Permissions Update
files["modules/permissions/models.py"] = """from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, UniqueConstraint
import uuid

from app.models.base import TimestampedModel

class Role(TimestampedModel):
    __tablename__ = "roles"
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_role_org_name'),
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(TimestampedModel):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(TimestampedModel):
    __tablename__ = "role_permissions"
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)
    
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
"""

# 4. AuditLog & RefreshToken Update
files["core/auth/models.py"] = """from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, DateTime, JSON
import uuid
from datetime import datetime

from app.models.base import TimestampedModel

class RefreshToken(TimestampedModel):
    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"

    who: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    what: Mapped[str] = mapped_column(String, index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String, index=True, nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    ip: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    
    user = relationship("User", back_populates="audit_logs")
    organization = relationship("Organization", back_populates="audit_logs")
"""

# 5. Events Scaffolding
files["core/events/event.py"] = """# Base Event class
class Event:
    pass
"""
files["core/events/dispatcher.py"] = """# Event Dispatcher
class EventDispatcher:
    pass
"""
files["core/events/handlers.py"] = """# Event Handlers
"""
files["core/events/types.py"] = """# Event Types
from enum import Enum
class EventType(str, Enum):
    USER_CREATED = "USER_CREATED"
"""

# Write all files
for file_path, content in files.items():
    full_path = BASE_DIR / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Files generated successfully!")
