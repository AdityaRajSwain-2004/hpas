"""Initial schema with pgvector

Revision ID: 001
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid


def upgrade():
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── prospects ─────────────────────────────────────────────
    op.create_table("prospects",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("domain",               sa.String(256), nullable=False),
        sa.Column("company_name",         sa.String(512), nullable=False),
        sa.Column("industry",             sa.String(128)),
        sa.Column("sub_industry",         sa.String(128)),
        sa.Column("hq_country",           sa.String(64)),
        sa.Column("employee_count",       sa.Integer),
        sa.Column("revenue_usd",          sa.BigInteger),
        sa.Column("revenue_band",         sa.String(64)),
        sa.Column("public_listed",        sa.Boolean, default=False),
        sa.Column("operating_regions",    ARRAY(sa.String), default=[]),
        sa.Column("esg_score_composite",  sa.Float),
        sa.Column("esg_score_env",        sa.Float),
        sa.Column("esg_score_social",     sa.Float),
        sa.Column("esg_score_governance", sa.Float),
        sa.Column("esg_maturity",         sa.String(32)),
        sa.Column("decarb_urgency",       sa.Float),
        sa.Column("supply_chain_risk",    sa.Float),
        sa.Column("icp_fit_score",        sa.Float),
        sa.Column("prospect_tier",        sa.Integer),
        sa.Column("lead_status",          sa.String(32), default="raw"),
        sa.Column("lead_score",           sa.Float, default=0.0),
        sa.Column("contact_name_enc",     sa.Text),
        sa.Column("contact_title",        sa.String(256)),
        sa.Column("contact_email_enc",    sa.Text),
        sa.Column("contact_linkedin_enc", sa.Text),
        sa.Column("contact_source",       sa.String(64)),
        sa.Column("contact_verified",     sa.Boolean, default=False),
        sa.Column("contact_persona",      sa.String(64)),
        sa.Column("profile_embedding",    sa.Text),  # stored as text, cast to vector
        sa.Column("raw_esg_data",         JSONB, default={}),
        sa.Column("raw_firmographic_data",JSONB, default={}),
        sa.Column("compliance_gaps",      JSONB, default=[]),
        sa.Column("benchmark_delta",      JSONB, default={}),
        sa.Column("enrichment_sources",   ARRAY(sa.String), default=[]),
        sa.Column("data_quality_score",   sa.Float, default=0.0),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("last_contacted_at",    sa.DateTime(timezone=True)),
    )
    op.execute("ALTER TABLE prospects ALTER COLUMN profile_embedding TYPE vector(1536) USING profile_embedding::vector(1536)")
    op.create_index("ix_prospects_domain", "prospects", ["domain"], unique=True)
    op.create_index("ix_prospects_status", "prospects", ["lead_status"])

    # ── campaigns ─────────────────────────────────────────────
    op.create_table("campaigns",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name",            sa.String(256), nullable=False),
        sa.Column("description",     sa.Text),
        sa.Column("target_segment",  JSONB, default={}),
        sa.Column("channels",        ARRAY(sa.String), default=["email"]),
        sa.Column("esg_theme",       sa.String(64)),
        sa.Column("persona",         sa.String(64)),
        sa.Column("status",          sa.String(32), default="draft"),
        sa.Column("ab_test_enabled", sa.Boolean, default=True),
        sa.Column("total_sent",      sa.Integer, default=0),
        sa.Column("total_opened",    sa.Integer, default=0),
        sa.Column("total_replied",   sa.Integer, default=0),
        sa.Column("total_demos",     sa.Integer, default=0),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # ── interactions ──────────────────────────────────────────
    op.create_table("interactions",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("prospect_id",          UUID(as_uuid=True), sa.ForeignKey("prospects.id")),
        sa.Column("campaign_id",          UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("channel",              sa.String(32)),
        sa.Column("direction",            sa.String(16), default="outbound"),
        sa.Column("event_type",           sa.String(64)),
        sa.Column("subject",              sa.Text),
        sa.Column("body_preview",         sa.Text),
        sa.Column("ab_variant",           sa.String(4)),
        sa.Column("esg_theme",            sa.String(64)),
        sa.Column("persona",              sa.String(64)),
        sa.Column("opened",               sa.Boolean, default=False),
        sa.Column("clicked",              sa.Boolean, default=False),
        sa.Column("replied",              sa.Boolean, default=False),
        sa.Column("sentiment",            sa.String(32)),
        sa.Column("intent",               sa.String(32)),
        sa.Column("reward",               sa.Float, default=0.0),
        sa.Column("quality_score",        sa.Float),
        sa.Column("confidence",           sa.Float),
        sa.Column("personalization_score",sa.Float),
        sa.Column("hitl_reviewed",        sa.Boolean, default=False),
        sa.Column("metadata",             JSONB, default={}),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_interaction_prospect", "interactions", ["prospect_id"])

    # ── hitl_items ────────────────────────────────────────────
    op.create_table("hitl_items",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("prospect_id",     UUID(as_uuid=True), sa.ForeignKey("prospects.id")),
        sa.Column("workflow_run_id", sa.String(128)),
        sa.Column("channel",         sa.String(32)),
        sa.Column("persona",         sa.String(64)),
        sa.Column("esg_theme",       sa.String(64)),
        sa.Column("subject",         sa.Text),
        sa.Column("body",            sa.Text),
        sa.Column("flag_reason",     sa.Text),
        sa.Column("confidence",      sa.Float),
        sa.Column("tier",            sa.Integer),
        sa.Column("tags",            JSONB, default=[]),
        sa.Column("status",          sa.String(32), default="pending"),
        sa.Column("reviewed_by",     sa.String(256)),
        sa.Column("reviewed_at",     sa.DateTime(timezone=True)),
        sa.Column("edited_subject",  sa.Text),
        sa.Column("edited_body",     sa.Text),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── prompt_templates ──────────────────────────────────────
    op.create_table("prompt_templates",
        sa.Column("id",                UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name",              sa.String(256)),
        sa.Column("variant",           sa.String(4)),
        sa.Column("esg_theme",         sa.String(64)),
        sa.Column("persona",           sa.String(64)),
        sa.Column("industry",          sa.String(64)),
        sa.Column("channel",           sa.String(32)),
        sa.Column("system_prompt",     sa.Text),
        sa.Column("user_prompt",       sa.Text),
        sa.Column("performance_score", sa.Float, default=0.5),
        sa.Column("total_uses",        sa.Integer, default=0),
        sa.Column("is_active",         sa.Boolean, default=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",        sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table("prompt_templates")
    op.drop_table("hitl_items")
    op.drop_table("interactions")
    op.drop_table("campaigns")
    op.drop_table("prospects")
    op.execute("DROP EXTENSION IF EXISTS vector")
