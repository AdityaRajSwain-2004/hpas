"""Change profile_embedding dimension from 1536 (OpenAI) to 768 (Gemini)

Revision ID: 003
Revises: 002
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Nullify existing embeddings (they are incompatible with the new dimension)
    op.execute("UPDATE prospects SET profile_embedding = NULL")
    # Drop old column and recreate with new dimension
    op.drop_column("prospects", "profile_embedding")
    op.execute("ALTER TABLE prospects ADD COLUMN profile_embedding vector(768)")


def downgrade():
    op.execute("UPDATE prospects SET profile_embedding = NULL")
    op.drop_column("prospects", "profile_embedding")
    op.execute("ALTER TABLE prospects ADD COLUMN profile_embedding vector(1536)")
