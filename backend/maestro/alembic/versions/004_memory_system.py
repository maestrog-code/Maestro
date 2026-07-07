"""
Memory system models and tables (Sprint 006)

Revision ID: 004_memory_system
Revises: 003_knowledge_engine
Create Date: 2026-07-07 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.core.ai_settings import ai_settings

# revision identifiers, used by Alembic.
revision = '004_memory_system'
down_revision = '003_knowledge_engine'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create Enums
    memory_type_enum = postgresql.ENUM('FACT', 'PREFERENCE', 'GOAL', 'DECISION', 'PROFILE', 'WARNING', 'TASK', 'RELATIONSHIP', 'CONSTRAINT', name='memory_type_enum', create_type=False)
    memory_type_enum.create(op.get_bind(), checkfirst=True)

    memory_status_enum = postgresql.ENUM('ACTIVE', 'STALE', 'ARCHIVED', 'CONFLICTED', name='memory_status_enum', create_type=False)
    memory_status_enum.create(op.get_bind(), checkfirst=True)

    memory_source_enum = postgresql.ENUM('CONVERSATION', 'MANUAL', 'TOOL', 'IMPORT', 'SYSTEM', name='memory_source_enum', create_type=False)
    memory_source_enum.create(op.get_bind(), checkfirst=True)

    # 2. agent_memories
    op.create_table('agent_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', memory_type_enum, nullable=False, server_default='FACT'),
        sa.Column('status', memory_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('source', memory_source_enum, nullable=False, server_default='SYSTEM'),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_memories_organization_id'), 'agent_memories', ['organization_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_user_id'), 'agent_memories', ['user_id'], unique=False)
    op.create_index(op.f('ix_agent_memories_agent_id'), 'agent_memories', ['agent_id'], unique=False)

    # 3. memory_embeddings
    op.create_table('memory_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_embeddings_memory_id'), 'memory_embeddings', ['memory_id'], unique=False)
    
    # Add dynamic vector column
    dim = ai_settings.EMBEDDING_DIMENSIONS
    op.execute(f"ALTER TABLE memory_embeddings ADD COLUMN vector vector({dim});")
    op.execute(f"CREATE INDEX ix_memory_embeddings_vector ON memory_embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);")

    # 4. memory_access_logs
    op.create_table('memory_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_access_logs_memory_id'), 'memory_access_logs', ['memory_id'], unique=False)
    op.create_index(op.f('ix_memory_access_logs_organization_id'), 'memory_access_logs', ['organization_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_memory_access_logs_organization_id'), table_name='memory_access_logs')
    op.drop_index(op.f('ix_memory_access_logs_memory_id'), table_name='memory_access_logs')
    op.drop_table('memory_access_logs')
    
    op.execute('DROP INDEX IF EXISTS ix_memory_embeddings_vector;')
    op.drop_index(op.f('ix_memory_embeddings_memory_id'), table_name='memory_embeddings')
    op.drop_table('memory_embeddings')
    
    op.drop_index(op.f('ix_agent_memories_agent_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_user_id'), table_name='agent_memories')
    op.drop_index(op.f('ix_agent_memories_organization_id'), table_name='agent_memories')
    op.drop_table('agent_memories')

    # Drop enums
    op.execute('DROP TYPE memory_type_enum;')
    op.execute('DROP TYPE memory_status_enum;')
    op.execute('DROP TYPE memory_source_enum;')
