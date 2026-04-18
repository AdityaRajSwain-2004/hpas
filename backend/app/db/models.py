from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    Text, Enum, Index, BigInteger, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
from app.core.settings import settings
import enum
import uuid

# ── Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Base ──────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────
class LeadStatus(str, enum.Enum):
    RAW             = "raw"
    QUALIFIED       = "qualified"
    ENGAGED         = "engaged"
    DEMO_SCHEDULED  = "demo_scheduled"
    PROPOSAL_SENT   = "proposal_sent"
    CONVERTED       = "converted"
    CHURNED         = "churned"

class ProspectTier(int, enum.Enum):
    TIER1 = 1
    TIER2 = 2
    TIER3 = 3

class HITLStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    EDITED   = "edited"
    REJECTED = "rejected"

class CampaignStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"


# ── Models ────────────────────────────────────────────────────

class Prospect(Base):
    __tablename__ = "prospects"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain                  = Column(String(256), unique=True, nullable=False, index=True)
    company_name            = Column(String(512), nullable=False)
    industry                = Column(String(128))
    sub_industry            = Column(String(128))
    hq_country              = Column(String(64))
    employee_count          = Column(Integer)
    revenue_usd             = Column(BigInteger)
    revenue_band            = Column(String(64))
    public_listed           = Column(Boolean, default=False)
    operating_regions       = Column(ARRAY(String), default=[])

    # ESG scores
    esg_score_composite     = Column(Float)
    esg_score_env           = Column(Float)
    esg_score_social        = Column(Float)
    esg_score_governance    = Column(Float)
    esg_maturity            = Column(String(32))
    decarb_urgency          = Column(Float)
    supply_chain_risk       = Column(Float)
    icp_fit_score           = Column(Float)
    prospect_tier           = Column(Integer)

    # Pipeline
    lead_status             = Column(String(32), default=LeadStatus.RAW)
    lead_score              = Column(Float, default=0.0)

    # Contact (encrypted)
    contact_name_enc        = Column(Text)
    contact_title           = Column(String(256))
    contact_email_enc       = Column(Text)
    contact_linkedin_enc    = Column(Text)
    contact_source          = Column(String(64))
    contact_verified        = Column(Boolean, default=False)
    contact_persona         = Column(String(64))

    # Vector embedding (pgvector — Gemini)
    profile_embedding       = Column(Vector(768))

    # Raw data cache
    raw_esg_data            = Column(JSONB, default={})
    raw_firmographic_data   = Column(JSONB, default={})
    compliance_gaps         = Column(JSONB, default=[])
    benchmark_delta         = Column(JSONB, default={})
    enrichment_sources      = Column(ARRAY(String), default=[])
    data_quality_score      = Column(Float, default=0.0)

    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), onupdate=func.now())
    last_contacted_at       = Column(DateTime(timezone=True))

    interactions            = relationship("Interaction", back_populates="prospect")
    hitl_items              = relationship("HITLItem", back_populates="prospect")


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (Index("ix_interaction_prospect", "prospect_id"),)

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id         = Column(UUID(as_uuid=True), ForeignKey("prospects.id"))
    campaign_id         = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)

    channel             = Column(String(32))
    direction           = Column(String(16), default="outbound")
    event_type          = Column(String(64))
    subject             = Column(Text)
    body_preview        = Column(Text)
    ab_variant          = Column(String(4))
    esg_theme           = Column(String(64))
    persona             = Column(String(64))

    # Engagement
    opened              = Column(Boolean, default=False)
    clicked             = Column(Boolean, default=False)
    replied             = Column(Boolean, default=False)
    sentiment           = Column(String(32))
    intent              = Column(String(32))
    reward              = Column(Float, default=0.0)

    # AI metadata
    quality_score       = Column(Float)
    confidence          = Column(Float)
    personalization_score = Column(Float)
    hitl_reviewed       = Column(Boolean, default=False)

    metadata            = Column(JSONB, default={})
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    prospect            = relationship("Prospect", back_populates="interactions")


class HITLItem(Base):
    __tablename__ = "hitl_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id     = Column(UUID(as_uuid=True), ForeignKey("prospects.id"))
    workflow_run_id = Column(String(128))

    channel         = Column(String(32))
    persona         = Column(String(64))
    esg_theme       = Column(String(64))
    subject         = Column(Text)
    body            = Column(Text)
    flag_reason     = Column(Text)
    confidence      = Column(Float)
    tier            = Column(Integer)
    tags            = Column(JSONB, default=[])

    status          = Column(String(32), default=HITLStatus.PENDING)
    reviewed_by     = Column(String(256))
    reviewed_at     = Column(DateTime(timezone=True))
    edited_subject  = Column(Text)
    edited_body     = Column(Text)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    prospect        = relationship("Prospect", back_populates="hitl_items")


class Campaign(Base):
    __tablename__ = "campaigns"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(256), nullable=False)
    description     = Column(Text)
    target_segment  = Column(JSONB, default={})
    channels        = Column(ARRAY(String), default=["email"])
    esg_theme       = Column(String(64))
    persona         = Column(String(64))
    status          = Column(String(32), default=CampaignStatus.DRAFT)
    ab_test_enabled = Column(Boolean, default=True)

    total_sent      = Column(Integer, default=0)
    total_opened    = Column(Integer, default=0)
    total_replied   = Column(Integer, default=0)
    total_demos     = Column(Integer, default=0)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(256))
    variant         = Column(String(4))        # A or B
    esg_theme       = Column(String(64))
    persona         = Column(String(64))
    industry        = Column(String(64))
    channel         = Column(String(32))
    system_prompt   = Column(Text)
    user_prompt     = Column(Text)
    performance_score = Column(Float, default=0.5)
    total_uses      = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
