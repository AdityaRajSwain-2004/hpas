"""Add suppression_domains table

Revision ID: 002
Revises: 001
Create Date: 2025-01-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


def upgrade():
    op.create_table(
        "suppression_domains",
        sa.Column("id",         UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("domain",     sa.String(256), nullable=False),
        sa.Column("reason",     sa.String(64),  nullable=False, server_default="manual"),
        sa.Column("notes",      sa.Text),
        sa.Column("added_by",   sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_suppression_domain", "suppression_domains", ["domain"], unique=True
    )


def downgrade():
    op.drop_index("ix_suppression_domain", table_name="suppression_domains")
    op.drop_table("suppression_domains")
