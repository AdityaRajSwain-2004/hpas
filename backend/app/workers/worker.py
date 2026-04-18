"""
ARQ Worker — v2.1
Priorities implemented:
  P3 — ZeroBounce credit monitoring (daily 8am cron)

Also includes: follow-up sequence scheduler (daily 7am cron)
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone

import arq
from arq import cron
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.core.settings import settings
from app.pipeline.pipeline import SustainabilityPipeline

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# CORE PIPELINE JOB
# ══════════════════════════════════════════════════════════════

async def run_prospect_pipeline(
    ctx: dict,
    domain: str,
    persona: str = "cso",
    channel: str = "email",
    campaign_id: str = None,
    ab_variant: str = None,
    followup_num: int = 1,
) -> dict:
    """Main pipeline job — triggered via API or scheduled follow-up."""
    db: AsyncSession = ctx["db_session"]
    pipeline = SustainabilityPipeline(db)
    try:
        result = await pipeline.run(
            domain=domain, persona=persona, channel=channel,
            campaign_id=campaign_id, ab_variant=ab_variant,
            followup_num=followup_num,
        )
        return {
            "success":          result.success,
            "prospect_id":      result.prospect_id,
            "esg_score":        result.esg_score,
            "tier":             result.prospect_tier,
            "dispatched":       result.dispatched,
            "requires_hitl":    result.requires_hitl,
            "suppressed":       result.suppressed,
            "competitor":       result.competitor_detected,
            "content_strategy": result.content_strategy,
            "latency_ms":       result.latency_ms,
            "error":            result.error,
        }
    finally:
        await pipeline.close()


async def run_bulk_pipeline(ctx: dict, domains: list[str], persona: str = "cso", channel: str = "email") -> dict:
    """Process multiple domains with concurrency limit."""
    semaphore = asyncio.Semaphore(3)
    results   = []

    async def process_one(domain: str):
        async with semaphore:
            return await run_prospect_pipeline(ctx, domain, persona, channel)

    outcomes = await asyncio.gather(*[process_one(d) for d in domains], return_exceptions=True)
    for domain, outcome in zip(domains, outcomes):
        if isinstance(outcome, Exception):
            results.append({"domain": domain, "success": False, "error": str(outcome)})
        else:
            results.append({"domain": domain, **outcome})

    return {"processed": len(domains), "results": results}


# ══════════════════════════════════════════════════════════════
# P3 — ZEROBOUNCE CREDIT MONITORING (daily 8am)
# ══════════════════════════════════════════════════════════════

async def check_zerobounce_credits(ctx: dict) -> dict:
    """
    Daily job at 8am: fetch ZeroBounce credit balance.
    Logs CRITICAL if < 200 credits (pipeline email verification will degrade).
    Logs WARNING if < 500 credits (top up soon).
    The /health endpoint also exposes this in real time.
    """
    if not settings.ZEROBOUNCE_API_KEY:
        log.info("ZeroBounce credit check skipped — no API key configured")
        return {"skipped": True, "reason": "no_api_key"}

    credits = -1
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(
                "https://api.zerobounce.net/v2/getcredits",
                params={"api_key": settings.ZEROBOUNCE_API_KEY},
            )
            if resp.status_code == 200:
                credits = int(resp.json().get("Credits", 0))
            else:
                log.error("ZeroBounce credits API returned %d", resp.status_code)
    except Exception as e:
        log.error("ZeroBounce credit check failed: %s", e)

    if credits < 0:
        return {"credits_remaining": credits, "status": "check_failed"}

    if credits < 200:
        log.critical(
            "ZEROBOUNCE CRITICAL: %d credits remaining. "
            "Email verification will fall back to unverified mode. "
            "Purchase credits at: https://www.zerobounce.net/email-validation-pricing",
            credits,
        )
        status = "critical"
    elif credits < 500:
        log.warning("ZeroBounce LOW: %d credits remaining. Consider topping up.", credits)
        status = "low"
    else:
        log.info("ZeroBounce credits OK: %d remaining", credits)
        status = "ok"

    return {
        "credits_remaining": credits,
        "status":            status,
        "checked_at":        datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# FOLLOW-UP SEQUENCE SCHEDULER (daily 7am)
# ══════════════════════════════════════════════════════════════

async def check_and_schedule_followups(ctx: dict) -> dict:
    """
    Daily job at 7am.
    Finds prospects who received an outbound email but haven't replied,
    and whose timing window for the next follow-up has opened.

    Follow-up schedule:
      Email 2: 5–11 days after Email 1 (opened but no reply)
      Email 3: 12–20 days after Email 1 (still no reply)
      Email 4: 21+ days (breakup email — final)
    """
    db: AsyncSession = ctx["db_session"]

    # Find outbound emails with no inbound reply, within the follow-up window
    result = await db.execute(text("""
        SELECT DISTINCT ON (p.id)
            p.id                AS prospect_id,
            p.domain,
            p.contact_persona,
            p.lead_status,
            i.channel,
            i.campaign_id,
            i.ab_variant,
            i.created_at        AS last_sent_at,
            i.opened,
            (metadata->>'followup_num')::int AS last_followup_num
        FROM   prospects p
        JOIN   interactions i ON i.prospect_id = p.id
                             AND i.direction = 'outbound'
                             AND i.event_type = 'sent'
        LEFT   JOIN interactions inbound ON inbound.prospect_id = p.id
                                        AND inbound.direction = 'inbound'
        WHERE  p.lead_status IN ('qualified', 'engaged')
          AND  inbound.id IS NULL
          AND  i.created_at < now() - interval '5 days'
          AND  i.created_at > now() - interval '25 days'
        ORDER  BY p.id, i.created_at DESC
    """))
    prospects_due = result.mappings().fetchall()

    queued   = 0
    skipped  = 0
    now      = datetime.now(timezone.utc)

    for row in prospects_due:
        last_sent = row["last_sent_at"]
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        days_since    = (now - last_sent).days
        last_followup = row.get("last_followup_num") or 1

        # Determine next follow-up number and check timing window
        if last_followup == 1 and 5 <= days_since < 12:
            followup_num = 2
        elif last_followup <= 2 and 12 <= days_since < 21:
            followup_num = 3
        elif last_followup <= 3 and days_since >= 21:
            followup_num = 4
        else:
            skipped += 1
            continue

        # Skip if Email 1 was never opened — wait for open before following up
        # (Only apply this gate for follow-up 2; 3 and 4 send regardless)
        if followup_num == 2 and not row.get("opened"):
            log.debug("Skipping follow-up 2 for %s — Email 1 never opened", row["domain"])
            skipped += 1
            continue

        # Cap at Email 4 — no follow-up after breakup email
        if last_followup >= 4:
            skipped += 1
            continue

        pool = ctx.get("arq_pool")
        if pool:
            await pool.enqueue_job(
                "run_prospect_pipeline",
                row["domain"],
                row["contact_persona"] or "cso",
                row["channel"] or "email",
                row.get("campaign_id"),
                row.get("ab_variant"),
                followup_num,
            )
            queued += 1
            log.info(
                "Follow-up %d queued | domain=%s days_since=%d",
                followup_num, row["domain"], days_since,
            )

    log.info("Follow-up scheduler done | queued=%d skipped=%d", queued, skipped)
    return {
        "prospects_checked": len(prospects_due),
        "queued":            queued,
        "skipped":           skipped,
        "ran_at":            datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# WEEKLY RL OPTIMIZATION (Monday 6am)
# ══════════════════════════════════════════════════════════════

async def run_weekly_optimization(ctx: dict) -> dict:
    db: AsyncSession = ctx["db_session"]
    log.info("Running weekly RL optimization cycle")

    result = await db.execute(text("""
        SELECT ab_variant, esg_theme, persona, reward, confidence, quality_score
        FROM   interactions
        WHERE  created_at > now() - interval '7 days'
          AND  reward IS NOT NULL
    """))
    signals = result.fetchall()

    if not signals:
        return {"skipped": True, "reason": "No signals in last 7 days"}

    variant_rewards: dict = {}
    for s in signals:
        v = s.ab_variant or "A"
        variant_rewards.setdefault(v, [])
        variant_rewards[v].append(s.reward or 0)

    stats   = {v: {"count": len(r), "avg_reward": round(sum(r)/len(r), 4)} for v, r in variant_rewards.items()}
    updates = []
    for variant, s in stats.items():
        await db.execute(text("""
            UPDATE prompt_templates
            SET    performance_score = performance_score + 0.08 * (:reward - performance_score),
                   total_uses        = total_uses + :count,
                   updated_at        = now()
            WHERE  variant = :variant AND is_active = true
        """), {"reward": s["avg_reward"], "count": s["count"], "variant": variant})
        updates.append({"variant": variant, **s})

    log.info("Optimization complete: %s", updates)
    return {"signals_processed": len(signals), "template_updates": updates,
            "ran_at": datetime.now(timezone.utc).isoformat()}


# ══════════════════════════════════════════════════════════════
# DAILY ESG REFRESH (2am)
# ══════════════════════════════════════════════════════════════

async def refresh_esg_data_daily(ctx: dict) -> dict:
    db: AsyncSession = ctx["db_session"]
    result = await db.execute(text("""
        SELECT domain FROM prospects
        WHERE  (updated_at IS NULL OR updated_at < now() - interval '30 days')
          AND  lead_status NOT IN ('churned','converted')
        LIMIT  50
    """))
    domains = [row.domain for row in result.fetchall()]
    if not domains:
        return {"refreshed": 0}
    log.info("Refreshing ESG data for %d prospects", len(domains))
    for domain in domains:
        await run_prospect_pipeline(ctx, domain)
    return {"refreshed": len(domains)}


# ══════════════════════════════════════════════════════════════
# FEEDBACK PROCESSING
# ══════════════════════════════════════════════════════════════

async def process_feedback_signal(ctx: dict, signal: dict) -> dict:
    db: AsyncSession = ctx["db_session"]
    REWARD_MAP = {
        "demo_booked": 1.0, "form_filled": 0.80, "replied": 0.60,
        "clicked": 0.30,    "opened": 0.10,      "bounced_soft": -0.10,
        "bounced_hard": -0.50, "unsubscribed": -0.80, "spam_reported": -1.0,
    }
    event_type     = signal.get("event_type", "")
    prospect_id    = signal.get("prospect_id")
    interaction_id = signal.get("interaction_id")
    reward         = REWARD_MAP.get(event_type, 0.0)

    sentiment = None
    if event_type == "replied" and signal.get("reply_text"):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            resp   = await client.aio.models.generate_content(
                model=settings.LLM_MODEL,
                contents=signal["reply_text"][:400],
                config=types.GenerateContentConfig(
                    system_instruction="Return only one of: very_positive, positive, neutral, negative, very_negative",
                    max_output_tokens=10,
                    temperature=0.0
                )
            )
            sentiment = resp.text.strip().lower()
            mod = {"very_positive": 0.40,"positive": 0.20,"neutral": 0.0,
                   "negative": -0.20,"very_negative": -0.40}
            reward = max(-1.0, min(1.0, reward + mod.get(sentiment, 0.0)))
        except Exception:
            pass

    if interaction_id:
        update_fields: dict = {"reward": reward}
        if event_type == "opened":  update_fields["opened"]  = True
        if event_type == "clicked": update_fields["clicked"] = True
        if event_type in ("replied","demo_booked"):
            update_fields["replied"] = True
            if sentiment: update_fields["sentiment"] = sentiment
        set_clause = ", ".join(f"{k} = :{k}" for k in update_fields)
        await db.execute(
            text(f"UPDATE interactions SET {set_clause} WHERE id = :id"),
            {**update_fields, "id": interaction_id},
        )

    status_map = {"demo_booked":"demo_scheduled","replied":"engaged",
                  "spam_reported":"churned","unsubscribed":"churned"}
    new_status = status_map.get(event_type)
    if new_status and prospect_id:
        await db.execute(
            text("UPDATE prospects SET lead_status = :s WHERE id = :id"),
            {"s": new_status, "id": prospect_id},
        )

    # Auto-add hard bounces and spam reports to suppression list
    if event_type in ("bounced_hard", "spam_reported") and prospect_id:
        result = await db.execute(
            text("SELECT domain FROM prospects WHERE id = :id"), {"id": prospect_id}
        )
        row = result.scalar()
        if row:
            await db.execute(text("""
                INSERT INTO suppression_domains (id, domain, reason, notes, added_by)
                VALUES (gen_random_uuid(), :d, :r, :n, 'system_auto')
                ON CONFLICT (domain) DO NOTHING
            """), {
                "d": row,
                "r": "hard_bounce" if event_type == "bounced_hard" else "spam_report",
                "n": f"Auto-suppressed on {event_type} event at {datetime.now(timezone.utc).isoformat()}",
            })
            log.warning("Auto-suppressed domain %s due to %s", row, event_type)

    return {"event_type": event_type, "reward": reward, "sentiment": sentiment, "new_status": new_status}


# ══════════════════════════════════════════════════════════════
# WORKER STARTUP / SHUTDOWN
# ══════════════════════════════════════════════════════════════

async def startup(ctx: dict):
    engine  = create_async_engine(settings.DATABASE_URL, pool_size=5, max_overflow=5)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ctx["engine"]      = engine
    ctx["db_factory"]  = factory
    ctx["db_session"]  = factory()
    log.info("Worker started — DB pool ready")


async def shutdown(ctx: dict):
    await ctx["db_session"].close()
    await ctx["engine"].dispose()
    log.info("Worker shut down cleanly")


class WorkerSettings:
    functions = [
        run_prospect_pipeline,
        run_bulk_pipeline,
        process_feedback_signal,
        refresh_esg_data_daily,
        run_weekly_optimization,
        check_zerobounce_credits,        # P3
        check_and_schedule_followups,    # Follow-up sequences
    ]
    cron_jobs = [
        cron(run_weekly_optimization,    weekday=0, hour=6, minute=0),   # Mon 6am
        cron(refresh_esg_data_daily,     hour=2,    minute=0),           # Daily 2am
        cron(check_zerobounce_credits,   hour=8,    minute=0),           # Daily 8am — P3
        cron(check_and_schedule_followups, hour=7,  minute=0),           # Daily 7am
    ]
    on_startup  = startup
    on_shutdown = shutdown
    redis_settings = arq.RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs    = settings.WORKER_CONCURRENCY
    job_timeout = 120
    keep_result = 3600
