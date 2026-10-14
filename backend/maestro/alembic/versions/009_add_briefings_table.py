"""add_briefings_table

Revision ID: 009_add_briefings_table
Revises: 008_business_models
Create Date: 2026-07-11 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = '009_add_briefings_table'
down_revision: Union[str, None] = '008_business_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums
briefing_status_enum = ENUM("processing", "completed", "failed", name="briefingstatus", create_type=False)


def upgrade() -> None:
    # 1. Create Enum
    briefing_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create briefings table
    op.create_table(
        "briefings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", briefing_status_enum, nullable=False, server_default="processing", index=True),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    # 3. Create unique constraint
    op.create_unique_constraint("uq_briefing_org_date", "briefings", ["organization_id", "date"])


def downgrade() -> None:
    op.drop_table("briefings")
    briefing_status_enum.drop(op.get_bind(), checkfirst=True)
