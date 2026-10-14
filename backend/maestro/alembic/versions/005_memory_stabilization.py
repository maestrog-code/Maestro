"""
Memory system stabilization (Sprint 006.5)

Revision ID: 005_memory_stabilization
Revises: 004_memory_system
Create Date: 2026-07-07 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_memory_stabilization'
down_revision = '004_memory_system'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add 'PROJECT' to memory_type_enum
    # Add 'SUPERSEDED' to memory_status_enum
    
    # In PostgreSQL, we can add enum values using ALTER TYPE
    op.execute("ALTER TYPE memory_type_enum ADD VALUE IF NOT EXISTS 'project'")
    op.execute("ALTER TYPE memory_status_enum ADD VALUE IF NOT EXISTS 'superseded'")

def downgrade() -> None:
    # PostgreSQL does not support safely removing values from an ENUM type
    # without completely recreating the type and all columns that depend on it.
    # Therefore, the downgrade is a no-op.
    
    # Downgrade:
    # No-op.
    #
    # Reason:
    # Postgres cannot safely remove enum values without recreating the enum.
    pass
