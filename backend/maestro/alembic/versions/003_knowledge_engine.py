"""knowledge_engine

Revision ID: 003
Revises: 002
Create Date: 2026-07-07

Creates the Knowledge Engine tables and vector extension.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums
doc_type_enum = ENUM("file", "note", "policy", "sop", name="doc_type_enum", create_type=False)
doc_status_enum = ENUM("pending", "processing", "indexed", "failed", name="doc_status_enum", create_type=False)
visibility_enum = ENUM("org", "private", name="visibility_enum", create_type=False)


def upgrade() -> None:
    # 1. Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create Enums
    doc_type_enum.create(op.get_bind(), checkfirst=True)
    doc_status_enum.create(op.get_bind(), checkfirst=True)
    visibility_enum.create(op.get_bind(), checkfirst=True)

    # 3. knowledge_documents
    op.create_table(
        "knowledge_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("doc_type", doc_type_enum, nullable=False, server_default="note"),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("status", doc_status_enum, nullable=False, server_default="pending", index=True),
        sa.Column("visibility", visibility_enum, nullable=False, server_default="org"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_documents_is_deleted", "knowledge_documents", ["is_deleted"])

    # 4. knowledge_chunks
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=500), nullable=True),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("parser_version", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_chunks_is_deleted", "knowledge_chunks", ["is_deleted"])

    # 5. knowledge_embeddings
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_embeddings_is_deleted", "knowledge_embeddings", ["is_deleted"])
    # Unique constraint per chunk per model so we can UPSERT cleanly
    op.create_unique_constraint("uq_knowledge_embeddings_chunk_model", "knowledge_embeddings", ["chunk_id", "model"])

    # Add the raw vector column
    op.execute("ALTER TABLE knowledge_embeddings ADD COLUMN vector vector(768);")

    # Add IVFFLAT index for cosine similarity
    op.execute("""
        CREATE INDEX ix_knowledge_embeddings_vector 
        ON knowledge_embeddings 
        USING ivfflat (vector vector_cosine_ops)
        WITH (lists = 100);
    """)

    # 6. knowledge_tags
    op.create_table(
        "knowledge_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_knowledge_tags_is_deleted", "knowledge_tags", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("knowledge_tags")
    op.drop_table("knowledge_embeddings")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")

    visibility_enum.drop(op.get_bind(), checkfirst=True)
    doc_status_enum.drop(op.get_bind(), checkfirst=True)
    doc_type_enum.drop(op.get_bind(), checkfirst=True)
    
    op.execute("DROP EXTENSION IF EXISTS vector;")
