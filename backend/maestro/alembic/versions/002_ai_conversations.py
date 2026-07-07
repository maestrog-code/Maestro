"""ai_conversations

Revision ID: 002
Revises: 001
Create Date: 2026-07-07

Creates all tables for Sprint 004 AI Executive Engine:
- message_role_enum       (PostgreSQL ENUM)
- ai_conversations        (per-organization conversation sessions)
- ai_messages             (individual messages within a conversation)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, ENUM
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- Enum type (created once at the DB level) ---
message_role_enum = ENUM(
    "system", "user", "assistant", "tool",
    name="message_role_enum",
    create_type=False,  # We manage creation/drop manually below
)


def upgrade() -> None:
    # 1. Create the PostgreSQL ENUM type first
    message_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. --- ai_conversations ---
    op.create_table(
        "ai_conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),

        # Organization scoping — every conversation is owned by an org
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),

        # Human-readable session label
        sa.Column("title", sa.String(255), nullable=True),

        # AI runtime metadata recorded at conversation creation
        sa.Column("active_agent", sa.String(50), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),

        # TimestampedModel fields
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_ai_conversations_id", "ai_conversations", ["id"])
    op.create_index("ix_ai_conversations_organization_id", "ai_conversations", ["organization_id"])
    op.create_index("ix_ai_conversations_is_deleted", "ai_conversations", ["is_deleted"])
    # Composite index for listing an org's active conversations efficiently
    op.create_index(
        "ix_ai_conversations_org_created",
        "ai_conversations",
        ["organization_id", "created_at"],
    )

    # 3. --- ai_messages ---
    op.create_table(
        "ai_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),

        # FK back to the owning conversation — cascade deletes clean up messages
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),

        # Message role stored as a Postgres ENUM for DB-level constraint enforcement
        sa.Column(
            "role",
            ENUM(
                "system", "user", "assistant", "tool",
                name="message_role_enum",
                create_type=False,
            ),
            nullable=False,
        ),

        # The actual message body
        sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),

        # Optional fields used for tool-calling messages
        sa.Column("name", sa.String(255), nullable=True),         # tool name when role=tool
        sa.Column("tool_calls", JSON, nullable=True),              # list of ToolCall dicts
        sa.Column("tool_call_id", sa.String(255), nullable=True),  # correlation id for tool results

        # TimestampedModel fields
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_ai_messages_id", "ai_messages", ["id"])
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_index("ix_ai_messages_is_deleted", "ai_messages", ["is_deleted"])
    # Composite index for fetching ordered message history per conversation
    op.create_index(
        "ix_ai_messages_conversation_created",
        "ai_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index("ix_ai_messages_conversation_created", table_name="ai_messages")
    op.drop_index("ix_ai_messages_is_deleted", table_name="ai_messages")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_index("ix_ai_messages_id", table_name="ai_messages")
    op.drop_table("ai_messages")

    op.drop_index("ix_ai_conversations_org_created", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_is_deleted", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_organization_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")

    # Drop the ENUM type last (after all columns referencing it are gone)
    message_role_enum.drop(op.get_bind(), checkfirst=True)
