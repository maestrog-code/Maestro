"""
Memory stabilization (Sprint 006.5) — Round 2 schema hardening

Revision ID: 006_memory_embedding_index
Revises: 005_memory_stabilization
Create Date: 2026-07-07 19:30:00.000000

Changes:
    - Adds a unique partial index on (memory_id) for non-deleted memory_embeddings.
      This enforces ONE active embedding per memory at the database level, preventing
      duplicate embeddings from concurrent inserts.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '006_memory_embedding_index'
down_revision = '005_memory_stabilization'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Unique partial index: only one active (non-deleted) embedding per memory.
    # is_deleted=False rows are the only ones constrained. Soft-deleted rows are exempt,
    # so historical embeddings from superseded memories can coexist without violating the index.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_memory_embeddings_active
        ON memory_embeddings (memory_id)
        WHERE is_deleted = FALSE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uix_memory_embeddings_active;")
