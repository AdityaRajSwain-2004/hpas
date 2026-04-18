"""
Treeni AI — FastAPI Application  v2.1
Priorities implemented:
  P1 — Suppression list CRUD endpoints
  P3 — ZeroBounce credit monitoring in /health
  P4 — ESG data freshness check on HITL approval
"""
from __future__ import annotations
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import arq
import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.settings import settings
from app.db.models import Base, engine, get_db
from app.pipeline.pipeline import SustainabilityPipeline
from app.integrations.encryption import decrypt
import structlog

log = structlog.get_logger()


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Treeni AI Platform", version=settings.APP_VERSION)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.redis_pool = await arq.create_pool(arq.RedisSettings.from_dsn(settings.REDIS_URL))
    yield
    await app.state.redis_pool.close()
    await engine.dispose()
    log.info("Shutdown complete")


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="Treeni AI Sustainability Platform",
    version=settings.APP_VERSION,
    description="Lean AI-powered ESG outreach and engagement platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────
async def get_api_key(x_api_key: str = "dev"):
    if settings.is_production and x_api_key != settings.SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Request models ────────────────────────────────────────────
class ProspectRunRequest(BaseModel):
    domain: str
    persona: str = "cso"
    channel: str = "email"
    campaign_id: Optional[str] = None
    ab_variant: Optional[str] = None
    followup_num: int = 1

class BulkRunRequest(BaseModel):
    domains: list[str]
    persona: str = "cso"
    channel: str = "email"

class HITLReviewRequest(BaseModel):
    decision: str             # approve | reject | edit
    edited_subject: Optional[str] = None
    edited_body: Optional[str] = None
    reviewer: str = "reviewer"

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    channels: list[str] = ["email"]
    esg_theme: Optional[str] = None
    persona: str = "cso"
    ab_test_enabled: bool = True

class FeedbackSignal(BaseModel):
    event_type: str
    prospect_id: Optional[str] = None
    interaction_id: Optional[str] = None
    reply_text: Optional[str] = None
    metadata: dict = {}

# P1: Suppression request models
class SuppressionAdd(BaseModel):
    domain: str
    reason: str = "manual"          # existing_customer | active_opportunity | manual
    notes: Optional[str] = None
    added_by: str = "admin"


# ══════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
async def health():
    """
    System health — includes P3: ZeroBounce credit balance and warning.
    """
    # P3 — ZeroBounce credit check
    zb_credits = -1
    zb_warning = None
    if settings.ZEROBOUNCE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5) as http:
                resp = await http.get(
                    "https://api.zerobounce.net/v2/getcredits",
                    params={"api_key": settings.ZEROBOUNCE_API_KEY},
                )
                if resp.status_code == 200:
                    zb_credits = int(resp.json().get("Credits", 0))
        except Exception:
            pass

    if 0 <= zb_credits < 200:
        zb_warning = f"CRITICAL: Only {zb_credits} ZeroBounce credits remaining. Buy more immediately."
    elif 0 <= zb_credits < 500:
        zb_warning = f"WARNING: {zb_credits} ZeroBounce credits remaining. Consider topping up."

    return {
        "status":             "healthy",
        "version":            settings.APP_VERSION,
        "environment":        settings.ENVIRONMENT,
        "keys_configured":    settings.all_keys_configured,
        "zerobounce_credits": zb_credits,
        "zerobounce_warning": zb_warning,
        "timestamp":          datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# P1 — SUPPRESSION LIST (full CRUD)
# ══════════════════════════════════════════════════════════════

@app.get("/api/suppression", tags=["Suppression"])
async def list_suppressed(db: AsyncSession = Depends(get_db)):
    """List all suppressed domains."""
    result = await db.execute(
        text("SELECT * FROM suppression_domains ORDER BY created_at DESC")
    )
    return {"domains": [dict(r) for r in result.mappings().fetchall()]}


@app.post("/api/suppression", tags=["Suppression"], status_code=201)
async def add_suppression(req: SuppressionAdd, db: AsyncSession = Depends(get_db)):
    """
    Add a domain to the suppression list.
    reason options: existing_customer | active_opportunity | manual
    The pipeline checks this BEFORE any external API call — zero cost if suppressed.
    """
    domain = req.domain.lower().strip().removeprefix("www.")
    await db.execute(text("""
        INSERT INTO suppression_domains (id, domain, reason, notes, added_by)
        VALUES (gen_random_uuid(), :d, :r, :n, :a)
        ON CONFLICT (domain) DO UPDATE
            SET reason   = EXCLUDED.reason,
                notes    = EXCLUDED.notes,
                added_by = EXCLUDED.added_by
    """), {"d": domain, "r": req.reason, "n": req.notes, "a": req.added_by})
    log.info("Domain suppressed", domain=domain, reason=req.reason, by=req.added_by)
    return {"domain": domain, "reason": req.reason, "suppressed": True}


@app.delete("/api/suppression/{domain}", tags=["Suppression"])
async def remove_suppression(domain: str, db: AsyncSession = Depends(get_db)):
    """Remove a domain from the suppression list."""
    domain = domain.lower().strip().removeprefix("www.")
    await db.execute(
        text("DELETE FROM suppression_domains WHERE domain = :d"), {"d": domain}
    )
    return {"domain": domain, "suppressed": False}


@app.get("/api/suppression/{domain}", tags=["Suppression"])
async def check_suppression(domain: str, db: AsyncSession = Depends(get_db)):
    """Check whether a specific domain is suppressed before running the pipeline."""
    domain = domain.lower().strip().removeprefix("www.")
    result = await db.execute(
        text("SELECT * FROM suppression_domains WHERE domain = :d"), {"d": domain}
    )
    row = result.mappings().fetchone()
    if row:
        return {"domain": domain, "suppressed": True, "reason": row["reason"], "notes": row["notes"]}
    return {"domain": domain, "suppressed": False}


# ══════════════════════════════════════════════════════════════
# PROSPECTS
# ══════════════════════════════════════════════════════════════

@app.post("/api/prospects/run", tags=["Prospects"], status_code=202)
async def run_prospect(
    req: ProspectRunRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """Queue pipeline for a domain (async). Returns job_id immediately."""
    pool = app.state.redis_pool
    job  = await pool.enqueue_job(
        "run_prospect_pipeline",
        req.domain, req.persona, req.channel, req.campaign_id, req.ab_variant, req.followup_num,
    )
    return {"job_id": job.job_id, "domain": req.domain, "status": "queued"}


@app.post("/api/prospects/run/sync", tags=["Prospects"])
async def run_prospect_sync(
    req: ProspectRunRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """Run pipeline synchronously (max 120s). Returns full PipelineResult."""
    pipeline = SustainabilityPipeline(db)
    try:
        result = await pipeline.run(
            domain=req.domain, persona=req.persona, channel=req.channel,
            campaign_id=req.campaign_id, ab_variant=req.ab_variant,
            followup_num=req.followup_num,
        )
        return result.__dict__
    finally:
        await pipeline.close()


@app.post("/api/prospects/bulk", tags=["Prospects"], status_code=202)
async def run_bulk(req: BulkRunRequest, _: str = Depends(get_api_key)):
    """Queue pipeline for up to 100 domains."""
    pool = app.state.redis_pool
    jobs = []
    for domain in req.domains[:100]:
        job = await pool.enqueue_job("run_prospect_pipeline", domain, req.persona, req.channel)
        jobs.append({"domain": domain, "job_id": job.job_id})
    return {"queued": len(jobs), "jobs": jobs}


@app.get("/api/prospects", tags=["Prospects"])
async def list_prospects(
    page: int = 1, page_size: int = 20,
    tier: Optional[int] = None, status: Optional[str] = None,
    industry: Optional[str] = None, search: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key),
):
    filters = []; params: dict = {"limit": page_size, "offset": (page-1)*page_size}
    if tier:     filters.append("prospect_tier = :tier");                    params["tier"]     = tier
    if status:   filters.append("lead_status = :status");                   params["status"]   = status
    if industry: filters.append("industry ILIKE :industry");                params["industry"] = f"%{industry}%"
    if search:   filters.append("(company_name ILIKE :search OR domain ILIKE :search)"); params["search"] = f"%{search}%"
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    result = await db.execute(text(f"""
        SELECT id, domain, company_name, industry, hq_country, employee_count,
               esg_score_composite, prospect_tier, lead_status, icp_fit_score,
               decarb_urgency, supply_chain_risk, data_quality_score,
               contact_title, contact_source, contact_verified,
               created_at, updated_at, last_contacted_at
        FROM   prospects {where}
        ORDER  BY esg_score_composite ASC NULLS LAST, created_at DESC
        LIMIT  :limit OFFSET :offset
    """), params)

    fp = {k:v for k,v in params.items() if k not in ("limit","offset")}
    count = await db.execute(text(f"SELECT count(*) FROM prospects {where}"), fp)
    return {"total": count.scalar(), "page": page, "page_size": page_size,
            "data": [dict(r) for r in result.mappings().fetchall()]}


@app.get("/api/prospects/{prospect_id}", tags=["Prospects"])
async def get_prospect(prospect_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    result = await db.execute(text("SELECT * FROM prospects WHERE id = :id"), {"id": prospect_id})
    row = result.mappings().fetchone()
    if not row: raise HTTPException(status_code=404, detail="Prospect not found")
    data = dict(row)
    data["contact_email"] = decrypt(data.pop("contact_email_enc", None))
    data["contact_name"]  = decrypt(data.pop("contact_name_enc", None))
    data.pop("contact_linkedin_enc", None)
    data.pop("profile_embedding", None)
    return data


# ══════════════════════════════════════════════════════════════
# HITL — with P4: Freshness check on approval
# ══════════════════════════════════════════════════════════════

@app.get("/api/hitl", tags=["HITL"])
async def get_hitl_queue(db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    result = await db.execute(text("""
        SELECT h.*, p.company_name, p.domain, p.industry, p.prospect_tier, p.updated_at AS esg_updated_at
        FROM   hitl_items h
        JOIN   prospects p ON p.id = h.prospect_id
        WHERE  h.status = 'pending'
        ORDER  BY h.confidence ASC, h.created_at ASC
        LIMIT  50
    """))
    rows = result.mappings().fetchall()

    # Annotate each item with age_hours for frontend freshness indicator
    now  = datetime.now(timezone.utc)
    items = []
    for r in rows:
        item = dict(r)
        if item.get("created_at"):
            created = item["created_at"]
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            item["age_hours"] = round((now - created).total_seconds() / 3600, 1)
        else:
            item["age_hours"] = 0
        items.append(item)

    return {"queue_size": len(items), "items": items}


@app.post("/api/hitl/{item_id}/review", tags=["HITL"])
async def review_hitl_item(
    item_id: str,
    req: HITLReviewRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_api_key),
):
    """
    Submit approve / reject / edit decision on a HITL item.
    P4: On approve/edit, checks ESG data freshness.
        If data is > 48h old, returns a freshness_warning in the response.
    """
    if req.decision not in ("approve", "reject", "edit"):
        raise HTTPException(status_code=400, detail="decision must be: approve | reject | edit")

    result = await db.execute(text("""
        SELECT h.*, p.domain, p.updated_at AS esg_updated_at,
               p.contact_email_enc, p.contact_name_enc
        FROM   hitl_items h
        JOIN   prospects p ON p.id = h.prospect_id
        WHERE  h.id = :id
    """), {"id": item_id})
    item = result.mappings().fetchone()
    if not item: raise HTTPException(status_code=404, detail="HITL item not found")

    # ══ P4 — ESG DATA FRESHNESS CHECK ══════════════════════════
    freshness_warning = None
    if req.decision in ("approve", "edit") and item.get("esg_updated_at"):
        esg_updated = item["esg_updated_at"]
        if esg_updated.tzinfo is None:
            esg_updated = esg_updated.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - esg_updated).total_seconds() / 3600
        if age_hours > 48:
            freshness_warning = (
                f"ESG data is {age_hours:.0f} hours old. Key facts may have changed since "
                f"this message was generated. Recommend verifying: SBTi status, sustainability "
                f"report publication, any major ESG announcement by {item['domain']}."
            )
            log.warning("Stale ESG data on HITL approval | domain=%s age_hours=%.0f", item["domain"], age_hours)
    # ══════════════════════════════════════════════════════════════

    status_map = {"approve": "approved", "reject": "rejected", "edit": "edited"}
    await db.execute(text("""
        UPDATE hitl_items
        SET    status = :status, reviewed_by = :reviewer,
               reviewed_at = now(), edited_subject = :subj, edited_body = :body
        WHERE  id = :id
    """), {"status": status_map[req.decision], "reviewer": req.reviewer,
           "subj": req.edited_subject, "body": req.edited_body, "id": item_id})

    dispatched = False
    if req.decision in ("approve", "edit"):
        from app.integrations.dispatch import DispatchService
        email = decrypt(item.get("contact_email_enc"))
        name  = decrypt(item.get("contact_name_enc")) or "there"
        final_subject = req.edited_subject or item["subject"]
        final_body    = req.edited_body    or item["body"]

        if email:
            async with httpx.AsyncClient(timeout=20) as http:
                dispatch = DispatchService(http)
                dispatched = await dispatch.send(
                    channel=item["channel"], email=email, name=name,
                    subject=final_subject, body=final_body,
                    metadata={"hitl_item_id": item_id, "reviewer": req.reviewer},
                )

    await db.execute(text("""
        UPDATE interactions SET hitl_reviewed = true
        WHERE  prospect_id = :pid AND created_at >= :since
    """), {"pid": str(item["prospect_id"]), "since": item["created_at"]})

    return {
        "item_id":           item_id,
        "decision":          req.decision,
        "reviewer":          req.reviewer,
        "dispatched":        dispatched,
        "freshness_warning": freshness_warning,   # P4
    }


# ══════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════

@app.get("/api/analytics/dashboard", tags=["Analytics"])
async def get_dashboard(db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    kpis = await db.execute(text("""
        SELECT count(*)                                              AS total_prospects,
               count(*) FILTER (WHERE lead_status='demo_scheduled') AS demos_booked,
               count(*) FILTER (WHERE lead_status='converted')      AS converted,
               count(*) FILTER (WHERE lead_status='engaged')        AS engaged,
               avg(esg_score_composite)                             AS avg_esg_score,
               avg(icp_fit_score)                                   AS avg_icp_fit,
               count(*) FILTER (WHERE prospect_tier=1)              AS tier1_count,
               count(*) FILTER (WHERE prospect_tier=2)              AS tier2_count,
               count(*) FILTER (WHERE prospect_tier=3)              AS tier3_count
        FROM prospects
    """))
    kpi = kpis.mappings().fetchone()

    eng = await db.execute(text("""
        SELECT count(*)                                AS total_sent,
               count(*) FILTER (WHERE opened=true)    AS total_opened,
               count(*) FILTER (WHERE clicked=true)   AS total_clicked,
               count(*) FILTER (WHERE replied=true)   AS total_replied,
               count(*) FILTER (WHERE reward >= 0.8)  AS demos_booked,
               avg(quality_score)                     AS avg_quality,
               avg(confidence)                        AS avg_confidence
        FROM interactions
        WHERE created_at > now() - interval '30 days'
    """))
    en = eng.mappings().fetchone()

    themes = await db.execute(text("""
        SELECT esg_theme, count(*) AS count, avg(reward) AS avg_reward
        FROM   interactions
        WHERE  esg_theme IS NOT NULL AND created_at > now() - interval '30 days'
        GROUP  BY esg_theme ORDER BY avg_reward DESC
    """))

    hitl_count = await db.execute(text("SELECT count(*) FROM hitl_items WHERE status='pending'"))
    ts = (en["total_sent"] or 0)

    return {
        "kpis": {
            "total_prospects": kpi["total_prospects"],
            "demos_booked":    kpi["demos_booked"],
            "converted":       kpi["converted"],
            "engaged":         kpi["engaged"],
            "avg_esg_score":   round(kpi["avg_esg_score"] or 0, 1),
            "tier_breakdown":  {"tier1": kpi["tier1_count"],"tier2": kpi["tier2_count"],"tier3": kpi["tier3_count"]},
        },
        "outreach": {
            "sent_30d":      ts,
            "open_rate":     round((en["total_opened"] or 0)/max(ts,1), 4),
            "click_rate":    round((en["total_clicked"] or 0)/max(ts,1), 4),
            "reply_rate":    round((en["total_replied"] or 0)/max(ts,1), 4),
            "avg_quality":   round(en["avg_quality"] or 0, 3),
            "avg_confidence":round(en["avg_confidence"] or 0, 3),
        },
        "esg_themes":   [dict(r) for r in themes.mappings().fetchall()],
        "hitl_pending": hitl_count.scalar(),
    }


@app.get("/api/analytics/pipeline", tags=["Analytics"])
async def get_pipeline(db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    result = await db.execute(text("SELECT lead_status, count(*) AS count FROM prospects GROUP BY lead_status"))
    stages = {r.lead_status: r.count for r in result.fetchall()}
    return {"stages": {s: stages.get(s,0) for s in ["raw","qualified","engaged","demo_scheduled","proposal_sent","converted","churned"]}}


# ══════════════════════════════════════════════════════════════
# CAMPAIGNS
# ══════════════════════════════════════════════════════════════

@app.get("/api/campaigns", tags=["Campaigns"])
async def list_campaigns(db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    result = await db.execute(text("SELECT * FROM campaigns ORDER BY created_at DESC"))
    return {"data": [dict(r) for r in result.mappings().fetchall()]}


@app.post("/api/campaigns", tags=["Campaigns"], status_code=201)
async def create_campaign(req: CampaignCreate, db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    cid = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO campaigns (id, name, description, channels, esg_theme, persona, ab_test_enabled)
        VALUES (:id,:name,:desc,:channels,:theme,:persona,:ab)
    """), {"id":cid,"name":req.name,"desc":req.description,"channels":req.channels,
           "theme":req.esg_theme,"persona":req.persona,"ab":req.ab_test_enabled})
    return {"id": cid, "name": req.name, "status": "draft"}


@app.post("/api/campaigns/{campaign_id}/launch", tags=["Campaigns"])
async def launch_campaign(campaign_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_api_key)):
    await db.execute(text("UPDATE campaigns SET status='active', updated_at=now() WHERE id=:id"), {"id":campaign_id})
    return {"campaign_id": campaign_id, "status": "active"}


# ══════════════════════════════════════════════════════════════
# FEEDBACK & JOBS
# ══════════════════════════════════════════════════════════════

@app.post("/api/feedback/webhook", tags=["Feedback"])
async def feedback_webhook(signal: FeedbackSignal, _: str = Depends(get_api_key)):
    pool = app.state.redis_pool
    await pool.enqueue_job("process_feedback_signal", signal.model_dump())
    return {"status": "received", "event": signal.event_type}


@app.get("/api/jobs/{job_id}", tags=["System"])
async def get_job_status(job_id: str):
    pool = app.state.redis_pool
    job  = arq.Job(job_id, pool)
    try:
        result = await job.result(timeout=0)
        return {"job_id": job_id, "status": "complete", "result": result}
    except Exception:
        return {"job_id": job_id, "status": "pending_or_not_found"}


# ── Global error handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request, exc):
    log.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
