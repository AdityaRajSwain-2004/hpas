"""
Treeni AI — Lean Sustainability Pipeline  v2.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Priorities implemented in this version:
  P1 — Suppression list check (before any API call)
  P2 — Competitor platform detection (parallel with Stage 1+2)
"""
from __future__ import annotations
import asyncio
import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.settings import settings
from app.integrations.contact import ContactIntelligenceService
from app.integrations.esg_sources import ESGSourceAggregator
from app.integrations.dispatch import DispatchService

log = logging.getLogger(__name__)

# ── Industry benchmarks ───────────────────────────────────────
BENCHMARKS = {
    "automotive":    {"renewable_energy_pct": 49.0, "supplier_esg_audit_pct": 63.0, "carbon_intensity": 8.5},
    "manufacturing": {"renewable_energy_pct": 38.0, "supplier_esg_audit_pct": 51.0, "carbon_intensity": 12.0},
    "chemicals":     {"renewable_energy_pct": 28.0, "supplier_esg_audit_pct": 58.0, "carbon_intensity": 18.0},
    "steel":         {"renewable_energy_pct": 22.0, "supplier_esg_audit_pct": 44.0, "carbon_intensity": 24.0},
    "food_beverage": {"renewable_energy_pct": 42.0, "supplier_esg_audit_pct": 55.0, "carbon_intensity": 10.0},
    "luxury":        {"renewable_energy_pct": 52.0, "supplier_esg_audit_pct": 48.0, "carbon_intensity": 6.0},
    "_default":      {"renewable_energy_pct": 35.0, "supplier_esg_audit_pct": 50.0, "carbon_intensity": 12.0},
}

INDUSTRY_ICP = {
    "automotive": 1.0, "manufacturing": 1.0, "chemicals": 0.95,
    "steel": 0.90,     "textiles": 0.90,     "food_beverage": 0.85,
    "logistics": 0.80, "energy": 0.80,       "luxury": 0.65,
    "_default": 0.40,
}

# ── P2: Competitor detection ───────────────────────────────────
COMPETITOR_TOOLS = {
    "watershed":           "Watershed",
    "persefoni":           "Persefoni",
    "plan a":              "Plan A",
    "sweep.net":           "Sweep",
    "normative.io":        "Normative",
    "ecochain":            "Ecochain",
    "workiva":             "Workiva ESG",
    "sphera":              "Sphera",
    "sap sustainability":  "SAP SFM",
    "sap sfm":             "SAP SFM",
    "ibm envizi":          "IBM Envizi",
    "envizi":              "IBM Envizi",
    "measurabl":           "Measurabl",
    "sinai technologies":  "Sinai Technologies",
    "cr360":               "CR360",
    "esg book":            "ESG Book",
}

COMPETITOR_URL_PATHS = [
    "/sustainability", "/esg", "/environment",
    "/corporate-responsibility", "/csr", "/net-zero",
    "/sustainability-report", "/responsible-business",
]

WEDGE_MAP = {
    "Watershed":    "supply_chain_wedge",
    "SAP SFM":      "supply_chain_wedge",
    "IBM Envizi":   "supply_chain_wedge",
    "Plan A":       "supply_chain_wedge",
    "Persefoni":    "supply_chain_wedge",
    "Normative":    "supply_chain_wedge",
    "Workiva ESG":  "reporting_wedge",
    "Sweep":        "supply_chain_wedge",
    "Ecochain":     "supply_chain_wedge",
    "Sphera":       "reporting_wedge",
    "CR360":        "reporting_wedge",
    "ESG Book":     "data_wedge",
    "Measurabl":    "reporting_wedge",
}

WEDGE_PROMPTS = {
    "supply_chain_wedge": (
        "IMPORTANT — WEDGE STRATEGY (supply chain gap):\n"
        "This company uses {tool}. {tool} covers internal Scope 1/2 accounting but does NOT "
        "cover Scope 3 Category 1 supplier-level traceability or EUDR/CSDDD due diligence. "
        "Position resustain™ SCSM exclusively as a complement — the supply chain layer {tool} is missing. "
        "Never suggest replacing {tool}. Never mention {tool} negatively."
    ),
    "reporting_wedge": (
        "IMPORTANT — WEDGE STRATEGY (regulatory traceability gap):\n"
        "This company uses {tool} for ESG reporting. {tool} helps with disclosure but does NOT "
        "automate EUDR commodity traceability or CSDDD supplier due diligence. "
        "Position resustain™ SCSM as the operational supply chain layer that feeds verified "
        "data into their existing {tool} reporting workflow."
    ),
    "data_wedge": (
        "IMPORTANT — WEDGE STRATEGY (data quality gap):\n"
        "This company uses {tool} for ESG data/ratings. Show how resustain™ SCSM provides "
        "primary supplier-collected ESG data vs modelled/estimated scores — giving them "
        "audit-ready evidence for CSRD ESRS E1 that {tool} cannot provide."
    ),
}


@dataclass
class PipelineResult:
    success: bool
    prospect_id: str
    domain: str
    company_name: str
    esg_score: float = 0.0
    prospect_tier: int = 3
    compliance_gaps: list = field(default_factory=list)
    content: dict = field(default_factory=dict)
    quality_score: float = 0.0
    confidence: float = 0.0
    requires_hitl: bool = False
    hitl_reason: str = ""
    dispatched: bool = False
    latency_ms: int = 0
    competitor_detected: Optional[str] = None
    content_strategy: str = "standard"
    suppressed: bool = False
    error: str = ""


class SustainabilityPipeline:
    def __init__(self, db: AsyncSession):
        self.db           = db
        self.ai_client    = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
        self.http         = httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT)
        self.esg_sources  = ESGSourceAggregator(self.http)
        self.contact_svc  = ContactIntelligenceService(self.http)
        self.dispatch_svc = DispatchService(self.http)
        self._run_id      = str(uuid.uuid4())

    async def run(
        self,
        domain: str,
        persona: str = "cso",
        channel: str = "email",
        campaign_id: str = None,
        ab_variant: str = None,
        followup_num: int = 1,
    ) -> PipelineResult:
        start  = time.monotonic()
        domain = domain.lower().strip().removeprefix("www.")
        log.info("Pipeline start | domain=%s persona=%s run=%s followup=%d",
                 domain, persona, self._run_id, followup_num)
        try:
            result = await self._execute(domain, persona, channel, campaign_id, ab_variant, followup_num)
        except Exception as exc:
            log.exception("Pipeline failed | domain=%s", domain)
            result = PipelineResult(
                success=False, prospect_id="", domain=domain,
                company_name=domain, error=str(exc),
            )
        result.latency_ms = int((time.monotonic() - start) * 1000)
        log.info("Pipeline complete | domain=%s success=%s latency=%dms",
                 domain, result.success, result.latency_ms)
        return result

    # ──────────────────────────────────────────────────────────
    async def _execute(self, domain, persona, channel, campaign_id, ab_variant, followup_num) -> PipelineResult:

        # ══════════════════════════════════════════════════════
        # PRIORITY 1 — SUPPRESSION CHECK
        # Before ANY external API call. Zero cost if suppressed.
        # ══════════════════════════════════════════════════════
        sup = await self.db.execute(
            text("SELECT reason, notes FROM suppression_domains WHERE domain = :d"),
            {"d": domain},
        )
        sup_row = sup.mappings().fetchone()
        if sup_row:
            log.warning("SUPPRESSED domain=%s reason=%s", domain, sup_row["reason"])
            return PipelineResult(
                success=False, prospect_id="", domain=domain, company_name=domain,
                suppressed=True,
                error=f"Suppressed: {sup_row['reason']}. {sup_row['notes'] or ''}".strip(),
            )

        # ══════════════════════════════════════════════════════
        # STAGES 1 + 2 + COMPETITOR — Three concurrent I/O calls
        # ══════════════════════════════════════════════════════
        esg_data, firmographics, competitor_info = await asyncio.gather(
            self.esg_sources.fetch_all(domain),
            self._infer_firmographics(domain),
            self._detect_competitor(domain),   # P2
        )
        firmographics["competitor_detected"] = competitor_info.get("tool")
        firmographics["content_strategy"]    = competitor_info.get("strategy", "standard")

        company_name = firmographics.get("company_name", domain.split(".")[0].title())

        # Pure math stages
        scores     = self._compute_scores(esg_data, firmographics)
        gaps       = self._detect_compliance_gaps(esg_data, firmographics)
        tier       = self._classify_tier(esg_data, firmographics)
        benchmarks = self._compute_benchmarks(esg_data, firmographics.get("industry", "_default"))

        # Contact + embedding concurrent
        contact_result, embedding = await asyncio.gather(
            self.contact_svc.find_and_verify(domain, company_name, persona),
            self._generate_embedding(esg_data, scores, firmographics),
        )

        similar = await self._find_similar_prospects(embedding, firmographics.get("industry", "other"))

        variant = ab_variant or random.choice(["A", "B"])
        content = await self._generate_content(
            firmographics=firmographics, esg_data=esg_data, scores=scores,
            gaps=gaps, tier=tier, similar=similar, benchmarks=benchmarks,
            persona=persona, channel=channel, variant=variant, followup_num=followup_num,
        )

        threshold     = settings.TIER3_HITL_THRESHOLD if tier == 3 else settings.HITL_CONFIDENCE_THRESHOLD
        requires_hitl = content["confidence"] < threshold

        prospect_id = await self._persist(
            domain=domain, company_name=company_name, firmographics=firmographics,
            esg_data=esg_data, scores=scores, gaps=gaps, tier=tier,
            contact_result=contact_result, embedding=embedding,
            data_quality=esg_data.get("_quality_score", 0.0),
        )

        dispatched = False
        if not requires_hitl:
            contact = contact_result.get("contact", {})
            if contact.get("safe_to_send") and contact.get("email"):
                dispatched = await self.dispatch_svc.send(
                    channel=channel, email=contact["email"],
                    name=contact.get("first_name", company_name),
                    subject=content.get("subject", ""), body=content.get("body", ""),
                    metadata={"prospect_id": prospect_id, "run_id": self._run_id},
                )
            await self._log_interaction(
                prospect_id=prospect_id, campaign_id=campaign_id, channel=channel,
                variant=variant, content=content, dispatched=dispatched,
                persona=persona, followup_num=followup_num,
            )
        else:
            await self._queue_hitl(
                prospect_id=prospect_id, content=content, persona=persona,
                channel=channel, tier=tier, gaps=gaps, competitor_info=competitor_info,
            )

        await self._update_embedding(prospect_id, embedding)

        return PipelineResult(
            success=True, prospect_id=prospect_id, domain=domain,
            company_name=company_name, esg_score=scores["composite"],
            prospect_tier=tier, compliance_gaps=gaps[:3], content=content,
            quality_score=content.get("quality_score", 0.0),
            confidence=content.get("confidence", 0.0),
            requires_hitl=requires_hitl,
            hitl_reason=f"Confidence {content['confidence']:.2f} below {threshold}" if requires_hitl else "",
            dispatched=dispatched,
            competitor_detected=competitor_info.get("tool"),
            content_strategy=competitor_info.get("strategy", "standard"),
        )

    # ══════════════════════════════════════════════════════════
    # P2 — Competitor detection
    # ══════════════════════════════════════════════════════════

    async def _detect_competitor(self, domain: str) -> dict:
        base_url = f"https://www.{domain}"
        for path in COMPETITOR_URL_PATHS:
            try:
                resp = await self.http.get(
                    base_url + path, timeout=8, follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; resustain-research/1.0)"},
                )
                if resp.status_code == 200:
                    page_text = resp.text.lower()
                    for keyword, tool_name in COMPETITOR_TOOLS.items():
                        if keyword in page_text:
                            strategy = WEDGE_MAP.get(tool_name, "supply_chain_wedge")
                            log.info("Competitor detected | domain=%s tool=%s", domain, tool_name)
                            return {"detected": True, "tool": tool_name, "strategy": strategy}
            except Exception:
                continue
        return {"detected": False, "tool": None, "strategy": "standard"}

    # ══════════════════════════════════════════════════════════
    # Stage 2 — Firmographic inference
    # ══════════════════════════════════════════════════════════

    async def _infer_firmographics(self, domain: str) -> dict:
        company_name = domain.split(".")[0].replace("-", " ").title()
        if not self.ai_client:
            return {"company_name": company_name, "industry": "manufacturing", "sources_used": ["fallback"]}
        try:
            resp = await self.ai_client.aio.models.generate_content(
                model=settings.LLM_MODEL,
                contents=f"""Company domain: {domain}
Return this JSON:
{{
  "company_name": "Full official company name",
  "industry": "one of: automotive|manufacturing|chemicals|steel|textiles|food_beverage|logistics|energy|pharma|retail|construction|technology|luxury|other",
  "sub_industry": "specific sub-sector",
  "employee_count": integer,
  "revenue_usd": integer,
  "revenue_band": "e.g. $1B-$5B",
  "hq_country": "country name",
  "hq_city": "city name",
  "operating_regions": ["EU", "Asia-Pacific", "Americas"],
  "public_listed": true or false,
  "stock_ticker": "ticker or null",
  "sources_used": ["llm_inference"]
}}""",
                config=types.GenerateContentConfig(
                    system_instruction="You are a business intelligence analyst. Return ONLY valid JSON. No markdown.",
                    max_output_tokens=500,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            t = resp.text.strip()
            if t.startswith("```"):
                t = t.split("```")[1].lstrip("json").strip()
            return json.loads(t)
        except Exception:
            return {"company_name": company_name, "industry": "manufacturing", "sources_used": ["fallback"]}

    # ══════════════════════════════════════════════════════════
    # Stage 3 — ESG Scoring
    # ══════════════════════════════════════════════════════════

    def _compute_scores(self, esg: dict, firm: dict) -> dict:
        env  = self._score_env(esg)
        soc  = self._score_social(esg)
        gov  = self._score_governance(esg)
        comp = round(env * 0.45 + soc * 0.30 + gov * 0.25, 1)
        du   = self._decarb_urgency(esg)
        return {
            "composite": comp, "environment": env, "social": soc, "governance": gov,
            "decarb_urgency": du, "supply_chain_risk": self._sc_risk(esg, firm),
            "regulatory_exposure": self._reg_exposure(esg, firm),
            "icp_fit": self._icp_score(firm),
            "treeni_fit": round(min(((100 - comp) / 100) * 0.5 + du * 0.5, 1.0), 3),
        }

    def _score_env(self, esg: dict) -> float:
        pts = []
        ci = esg.get("carbon_intensity")
        if ci: pts.append(("c", max(0, 100-(ci/30)*100), 0.30))
        re = esg.get("renewable_energy_pct")
        if re: pts.append(("r", min(re,100), 0.25))
        pts.append(("s3", 60.0 if esg.get("scope3_emissions_tco2e") else 15.0, 0.20))
        wr = esg.get("water_recycled_pct")
        if wr: pts.append(("w", min(wr,100), 0.15))
        wa = esg.get("waste_recycled_pct")
        if wa: pts.append(("wa", min(wa,100), 0.10))
        return self._wavg(pts) if pts else 40.0

    def _score_social(self, esg: dict) -> float:
        pts = []
        if esg.get("lost_time_injury_rate"): pts.append(("s", max(0,100-esg["lost_time_injury_rate"]*20), 0.30))
        if esg.get("gender_pay_gap_pct"):    pts.append(("g", max(0,100-esg["gender_pay_gap_pct"]*3), 0.30))
        if esg.get("board_diversity_pct"):   pts.append(("d", min(esg["board_diversity_pct"]*2,100), 0.20))
        if esg.get("living_wage_compliant"): pts.append(("w", 90.0, 0.20))
        return self._wavg(pts) if pts else 50.0

    def _score_governance(self, esg: dict) -> float:
        pts = []
        if esg.get("esg_board_committee"):            pts.append(("b", 95.0, 0.30))
        if esg.get("third_party_verified"):           pts.append(("v", 95.0, 0.25))
        if esg.get("sustainability_report_published"):pts.append(("r", 80.0, 0.25))
        if esg.get("ceo_esg_linked_pay"):             pts.append(("c", 90.0, 0.20))
        return self._wavg(pts) if pts else 40.0

    def _decarb_urgency(self, esg: dict) -> float:
        s = 0.0
        t = esg.get("total_carbon_footprint_tco2e", 0) or 0
        if t > 10_000_000: s += 0.30
        elif t > 1_000_000: s += 0.20
        elif t > 100_000:   s += 0.10
        re = esg.get("renewable_energy_pct", 0) or 0
        if re < 20: s += 0.20
        elif re < 50: s += 0.10
        if not esg.get("sbti_committed"):      s += 0.20
        if not esg.get("net_zero_target_year"):s += 0.10
        return round(min(s, 1.0), 3)

    def _sc_risk(self, esg: dict, firm: dict) -> float:
        s = 0.0
        a = esg.get("supplier_esg_audit_pct", 100) or 100
        if a < 30: s += 0.40
        elif a < 50: s += 0.25
        elif a < 70: s += 0.10
        d = esg.get("deforestation_risk_score", 0) or 0
        if d > 0.7: s += 0.25
        elif d > 0.4: s += 0.15
        return round(min(s, 1.0), 3)

    def _reg_exposure(self, esg: dict, firm: dict) -> float:
        s = 0.0
        c = (firm.get("hq_country") or "").lower()
        eu = {"germany","france","italy","spain","netherlands","belgium","sweden","denmark","poland","austria"}
        if c in eu: s += 0.30
        if c == "india": s += 0.25
        r = firm.get("revenue_usd", 0) or 0
        if r > 50_000_000_000: s += 0.25
        elif r > 1_000_000_000: s += 0.15
        if not esg.get("sustainability_report_published"): s += 0.20
        return round(min(s, 1.0), 3)

    def _icp_score(self, firm: dict) -> float:
        ind = (firm.get("industry") or "_default").lower()
        is_ = INDUSTRY_ICP.get(ind, INDUSTRY_ICP["_default"])
        r   = firm.get("revenue_usd", 0) or 0
        rs  = 0.3
        if r > 50_000_000_000: rs = 1.0
        elif r > 10_000_000_000: rs = 0.90
        elif r > 1_000_000_000:  rs = 0.80
        elif r > 200_000_000:    rs = 0.65
        elif r > 50_000_000:     rs = 0.50
        return round(is_ * 0.55 + rs * 0.45, 3)

    # ══════════════════════════════════════════════════════════
    # Stage 4 — Compliance gaps
    # ══════════════════════════════════════════════════════════

    def _detect_compliance_gaps(self, esg: dict, firm: dict) -> list[dict]:
        gaps = []
        country  = (firm.get("hq_country") or "").lower()
        industry = (firm.get("industry") or "other").lower()
        employees = firm.get("employee_count", 0) or 0
        revenue   = firm.get("revenue_usd", 0) or 0
        listed    = firm.get("public_listed", False)
        eu = {"germany","france","italy","spain","netherlands","belgium","sweden","denmark","poland","austria"}

        if country in eu and (employees >= 250 or revenue >= 37_000_000 or listed):
            if not esg.get("scope1_emissions_tco2e"):
                gaps.append({"framework":"CSRD","severity":"critical","label":"CSRD ESRS E1 — Scope 1/2 emissions not reported","deadline_days":180,"penalty_usd":int(revenue*0.05),"module":"Compliance Hub"})
            if not esg.get("third_party_verified"):
                gaps.append({"framework":"CSRD","severity":"high","label":"CSRD — GHG data not third-party verified","deadline_days":180,"penalty_usd":int(revenue*0.03),"module":"Compliance Hub"})

        if industry in ["food_beverage","automotive","textiles","chemicals"]:
            audit = esg.get("supplier_esg_audit_pct", 0) or 0
            if audit < 50:
                gaps.append({"framework":"EUDR","severity":"critical","label":f"EUDR — Supplier audit {audit:.0f}% (traceability required)","deadline_days":45,"penalty_usd":int(revenue*0.04),"module":"resustain™ SCSM"})

        if country == "india" and listed and not esg.get("sustainability_report_published"):
            gaps.append({"framework":"BRSR","severity":"critical","label":"BRSR Core — No sustainability report published","deadline_days":0,"penalty_usd":int(revenue*0.02),"module":"Compliance Hub"})

        if not esg.get("sbti_committed"):
            gaps.append({"framework":"SBTi","severity":"high","label":"SBTi — No science-based target commitment","deadline_days":None,"penalty_usd":0,"module":"Carbon Intelligence"})

        if not esg.get("scope3_emissions_tco2e"):
            gaps.append({"framework":"SCOPE3","severity":"high","label":"Scope 3 not tracked — majority of value chain emissions","deadline_days":None,"penalty_usd":0,"module":"Carbon Intelligence"})

        gaps.sort(key=lambda g: {"critical":0,"high":1,"medium":2,"low":3}.get(g["severity"],4))
        return gaps

    def _classify_tier(self, esg: dict, firm: dict) -> int:
        q = esg.get("_quality_score", 0.0)
        r = firm.get("revenue_usd", 0) or 0
        l = firm.get("public_listed", False)
        if q >= 0.70 and r >= 1_000_000_000 and l: return 1
        if q >= 0.45 or r >= 200_000_000: return 2
        return 3

    def _compute_benchmarks(self, esg: dict, industry: str) -> dict:
        bench = BENCHMARKS.get(industry, BENCHMARKS["_default"])
        delta = {}
        for f, label, hb in [
            ("renewable_energy_pct", "Renewable energy", True),
            ("supplier_esg_audit_pct", "Supplier ESG audit", True),
            ("carbon_intensity", "Carbon intensity", False),
        ]:
            cv = esg.get(f); bv = bench.get(f)
            if cv and bv:
                diff = cv - bv; pct = round((diff/bv)*100, 1)
                delta[f] = {"label":label,"company":cv,"benchmark":bv,"diff_pct":pct,
                            "display":f"{'+'if diff>0 else ''}{pct:.0f}% vs peers","better":(diff>0)==hb}
        return delta

    # ══════════════════════════════════════════════════════════
    # Stage 6b — Embedding
    # ══════════════════════════════════════════════════════════

    async def _generate_embedding(self, esg: dict, scores: dict, firm: dict) -> list[float]:
        t = (
            f"Company: {firm.get('company_name','unknown')} | Industry: {firm.get('industry','unknown')} | "
            f"Country: {firm.get('hq_country','unknown')} | ESG: {scores.get('composite',0)} | "
            f"Decarb: {scores.get('decarb_urgency',0):.2f} | SC risk: {scores.get('supply_chain_risk',0):.2f} | "
            f"Scope3: {esg.get('scope3_emissions_tco2e','nd')} | RE: {esg.get('renewable_energy_pct','?')}% | "
            f"Audit: {esg.get('supplier_esg_audit_pct','?')}%"
        )
        if not self.ai_client:
            return [0.0] * 768
        resp = await self.ai_client.aio.models.embed_content(model=settings.EMBEDDING_MODEL, contents=t[:8191])
        return resp.embeddings[0].values

    async def _find_similar_prospects(self, embedding: list[float], industry: str) -> list[dict]:
        if not any(embedding): return []
        try:
            vec = "[" + ",".join(str(round(v,6)) for v in embedding) + "]"
            result = await self.db.execute(text("""
                SELECT company_name, 1-(profile_embedding <=> :e::vector) AS sim, lead_status
                FROM   prospects
                WHERE  profile_embedding IS NOT NULL
                  AND  lead_status IN ('converted','demo_scheduled','engaged')
                ORDER  BY profile_embedding <=> :e::vector LIMIT 3
            """), {"e": vec})
            return [{"company":r.company_name,"similarity":round(r.sim,3),"status":r.lead_status}
                    for r in result.fetchall()]
        except Exception as e:
            log.warning("pgvector failed: %s", e)
            return []

    # ══════════════════════════════════════════════════════════
    # Stage 8 — Content generation
    # ══════════════════════════════════════════════════════════

    async def _generate_content(self, firmographics, esg_data, scores, gaps, tier,
                                 similar, benchmarks, persona, channel, variant, followup_num=1) -> dict:
        if followup_num > 1:
            content = await self._generate_followup_content(firmographics, gaps, persona, channel, followup_num)
        elif tier == 3:
            content = await self._generate_tier3_content(firmographics, gaps, persona, channel, variant)
        else:
            content = await self._generate_data_led_content(
                firmographics, esg_data, scores, gaps, similar, benchmarks, persona, channel, variant)

        qs = await self._score_content(content, firmographics, persona, tier)
        ps = self._heuristic_personalization(content, firmographics, esg_data)
        content["quality_score"] = qs
        content["personalization_score"] = ps
        content["confidence"] = round((qs + ps) / 2, 3)
        content["variant"] = variant
        return content

    async def _generate_data_led_content(self, firm, esg, scores, gaps, similar, benchmarks, persona, channel, variant) -> dict:
        persona_ctx = {
            "cso":                ("Chief Sustainability Officer","ESG strategy, net-zero, board credibility, stakeholder reporting"),
            "cfo":                ("Chief Financial Officer",     "regulatory risk, investor ESG mandates, ESG-linked financing"),
            "head_supply_chain":  ("Head of Supply Chain",       "supplier risk, EUDR traceability, audit coverage"),
            "sustainability_manager": ("Sustainability Manager",  "data collection, reporting accuracy, compliance automation"),
        }.get(persona, ("Decision Maker","sustainability performance"))

        top_gap   = gaps[0] if gaps else {}
        top_delta = next((v for v in benchmarks.values() if not v.get("better")), {})
        similar_ref = f" Companies like {similar[0]['company']} have already used resustain™ for this." if similar else ""
        key_metrics = [f"{l}: {esg.get(f)} {u}" for f,l,u in [
            ("scope3_emissions_tco2e","Scope 3 emissions","tCO₂e"),
            ("supplier_esg_audit_pct","Supplier ESG audit coverage","%"),
            ("renewable_energy_pct","Renewable energy","%"),
            ("carbon_intensity","Carbon intensity","tCO₂e/$M"),
        ] if esg.get(f)]

        competitor = firm.get("competitor_detected")
        competitor_note = ""
        if competitor:
            tmpl = WEDGE_PROMPTS.get(firm.get("content_strategy","supply_chain_wedge"), WEDGE_PROMPTS["supply_chain_wedge"])
            competitor_note = "\n\n" + tmpl.format(tool=competitor)

        system = (
            f"You are a senior sustainability consultant at Treeni writing {channel} outreach.\n"
            f"Products: resustain™ Enterprise (ESG) and resustain™ SCSM (supply chain).\n"
            f"RULES: Open with a SPECIFIC numeric ESG fact. Reference {top_gap.get('framework','ESG regulations')} by name.\n"
            f"Address a {persona_ctx[0]} whose priorities are: {persona_ctx[1]}.\n"
            f"Variant {'A: data-led' if variant=='A' else 'B: narrative-led'}.\n"
            f"End with ONE clear CTA. Never be generic.{competitor_note}"
        )
        user = (
            f"Company: {firm.get('company_name')} | Industry: {firm.get('industry')} | "
            f"Country: {firm.get('hq_country')} | Revenue: {firm.get('revenue_band','')}\n"
            f"ESG Score: {scores['composite']}/100 (~{self._percentile(scores['composite'])}th pct)\n"
            f"Key ESG data: {' | '.join(key_metrics) or 'Limited disclosure'}\n"
            f"Top benchmark gap: {top_delta.get('display','')} ({top_delta.get('label','')})\n"
            f"Critical compliance: {top_gap.get('label','')} — {top_gap.get('deadline_days','ongoing')} days{similar_ref}\n\n"
            f"Return JSON only: {{\"subject\":\"...\",\"opening_hook\":\"...\",\"body\":\"...\",\"cta\":\"...\",\"ps_line\":\"...\"}}"
        )
        resp = await self.ai_client.aio.models.generate_content(
            model=settings.LLM_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=800,
                temperature=0.35,
                response_mime_type="application/json"
            )
        )
        return self._parse_json_response(resp.text)

    async def _generate_tier3_content(self, firm, gaps, persona, channel, variant) -> dict:
        top_gap = gaps[0] if gaps else {"framework":"ESG regulations","label":"mandatory sustainability reporting","module":"resustain™ Enterprise"}
        competitor = firm.get("competitor_detected")
        competitor_note = ""
        if competitor:
            tmpl = WEDGE_PROMPTS.get(firm.get("content_strategy","supply_chain_wedge"), WEDGE_PROMPTS["supply_chain_wedge"])
            competitor_note = "\n\n" + tmpl.format(tool=competitor)

        system = (
            f"You are a sustainability consultant at Treeni. No verified ESG data available — "
            f"use ONLY regulation and industry context. No company-specific numbers. "
            f"Position resustain™ as the starting point.{competitor_note}"
        )
        user = (
            f"Company: {firm.get('company_name')} | Industry: {firm.get('industry')} | Country: {firm.get('hq_country')}\n"
            f"Regulation: {top_gap.get('framework')} — {top_gap.get('label')}\n"
            f"Module: {top_gap.get('module')}\n\n"
            f"Return JSON: {{\"subject\":\"...\",\"opening_hook\":\"...\",\"body\":\"...\",\"cta\":\"...\",\"ps_line\":\"...\"}}"
        )
        resp = await self.ai_client.aio.models.generate_content(
            model=settings.LLM_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=600,
                temperature=0.4,
                response_mime_type="application/json"
            )
        )
        return self._parse_json_response(resp.text)

    async def _generate_followup_content(self, firm, gaps, persona, channel, followup_num) -> dict:
        top_gap = gaps[0] if gaps else {}
        configs = {
            2: {"tone":"shorter, different angle, references earlier outreach briefly","angle":"supply chain benchmark gap or second regulation angle","cta":"case study link or short call","length":"2 short paragraphs"},
            3: {"tone":"very short and direct, references 2 previous emails","angle":"simple direct question — is this on your radar?","cta":"yes/no question","length":"1 short paragraph + 1 direct question"},
            4: {"tone":"breakup email — final outreach, no pressure","angle":"close the loop, leave the door open","cta":"resource link only","length":"2 very short paragraphs"},
        }
        c = configs.get(followup_num, configs[2])
        system = (
            f"You are writing follow-up #{followup_num} in a B2B email sequence for Treeni sustainability platform.\n"
            f"Tone: {c['tone']}. Angle: {c['angle']}. CTA: {c['cta']}. Length: {c['length']}.\n"
            f"Applicable regulation: {top_gap.get('framework','ESG')}. Return JSON only."
        )
        user = (
            f"Company: {firm.get('company_name')} | Industry: {firm.get('industry')}\n"
            f"Top compliance gap: {top_gap.get('label','')}\n"
            f"resustain™ module: {top_gap.get('module','')}\n\n"
            f"Return JSON: {{\"subject\":\"...\",\"body\":\"...\",\"cta\":\"...\"}}"
        )
        resp = await self.ai_client.aio.models.generate_content(
            model=settings.LLM_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=400,
                temperature=0.4,
                response_mime_type="application/json"
            )
        )
        content = self._parse_json_response(resp.text)
        content["followup_num"] = followup_num
        return content

    async def _score_content(self, content: dict, firm: dict, persona: str, tier: int) -> float:
        system = "Rate this B2B outreach 0-10 on each: personalization,relevance,compliance_urgency,solution_clarity,cta_quality,overall. Return ONLY JSON."
        user   = f"Subject: {content.get('subject','')}\nBody: {content.get('body','')}\nCTA: {content.get('cta','')}\nCompany: {firm.get('company_name')} | Persona: {persona} | Tier: {tier}\nReturn: {{\"personalization\":X,\"relevance\":X,\"compliance_urgency\":X,\"solution_clarity\":X,\"cta_quality\":X,\"overall\":X}}"
        try:
            resp = await self.ai_client.aio.models.generate_content(
                model=settings.LLM_MODEL,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=120,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            data = self._parse_json_response(resp.text)
            return round(data.get("overall", 7) / 10, 3)
        except Exception:
            return 0.70

    def _heuristic_personalization(self, content: dict, firm: dict, esg: dict) -> float:
        body  = (content.get("body","") + content.get("subject","")).lower()
        score = 0.0
        if firm.get("company_name","").lower() in body: score += 0.25
        for val in esg.values():
            if val and str(val)[:3] in body: score += 0.10
        for reg in ["csrd","tcfd","brsr","sbti","eudr","cdp","csddd"]:
            if reg in body: score += 0.08
        return round(min(score, 1.0), 3)

    def _percentile(self, s: float) -> int:
        if s >= 80: return 90
        if s >= 70: return 75
        if s >= 60: return 58
        if s >= 50: return 42
        if s >= 40: return 28
        return 12

    # ══════════════════════════════════════════════════════════
    # Persistence helpers
    # ══════════════════════════════════════════════════════════

    async def _persist(self, domain, company_name, firmographics, esg_data, scores,
                       gaps, tier, contact_result, embedding, data_quality) -> str:
        from app.integrations.encryption import encrypt
        contact = contact_result.get("contact", {})
        pid     = str(uuid.uuid4())
        await self.db.execute(text("""
            INSERT INTO prospects (
                id, domain, company_name, industry, sub_industry, hq_country,
                employee_count, revenue_usd, revenue_band, public_listed, operating_regions,
                esg_score_composite, esg_score_env, esg_score_social, esg_score_governance,
                esg_maturity, decarb_urgency, supply_chain_risk, icp_fit_score, prospect_tier,
                lead_status, lead_score,
                contact_name_enc, contact_title, contact_email_enc, contact_source,
                contact_verified, contact_persona,
                raw_esg_data, raw_firmographic_data, compliance_gaps, benchmark_delta,
                data_quality_score, enrichment_sources
            ) VALUES (
                :id,:domain,:company_name,:industry,:sub_industry,:hq_country,
                :employee_count,:revenue_usd,:revenue_band,:public_listed,:operating_regions,
                :esg_score_composite,:esg_score_env,:esg_score_social,:esg_score_governance,
                :esg_maturity,:decarb_urgency,:supply_chain_risk,:icp_fit_score,:prospect_tier,
                'qualified',:lead_score,
                :contact_name_enc,:contact_title,:contact_email_enc,:contact_source,
                :contact_verified,:contact_persona,
                :raw_esg_data,:raw_firmographic_data,:compliance_gaps,:benchmark_delta,
                :data_quality_score,:enrichment_sources
            )
            ON CONFLICT (domain) DO UPDATE SET
                esg_score_composite=EXCLUDED.esg_score_composite,
                decarb_urgency=EXCLUDED.decarb_urgency,
                supply_chain_risk=EXCLUDED.supply_chain_risk,
                prospect_tier=EXCLUDED.prospect_tier,
                raw_esg_data=EXCLUDED.raw_esg_data,
                compliance_gaps=EXCLUDED.compliance_gaps,
                data_quality_score=EXCLUDED.data_quality_score,
                updated_at=now()
        """), {
            "id":pid,"domain":domain,"company_name":company_name,
            "industry":firmographics.get("industry"),"sub_industry":firmographics.get("sub_industry"),
            "hq_country":firmographics.get("hq_country"),"employee_count":firmographics.get("employee_count"),
            "revenue_usd":firmographics.get("revenue_usd"),"revenue_band":firmographics.get("revenue_band"),
            "public_listed":firmographics.get("public_listed",False),
            "operating_regions":firmographics.get("operating_regions",[]),
            "esg_score_composite":scores["composite"],"esg_score_env":scores["environment"],
            "esg_score_social":scores["social"],"esg_score_governance":scores["governance"],
            "esg_maturity":"developing","decarb_urgency":scores["decarb_urgency"],
            "supply_chain_risk":scores["supply_chain_risk"],"icp_fit_score":scores["icp_fit"],
            "prospect_tier":tier,"lead_score":scores["treeni_fit"],
            "contact_name_enc":encrypt(contact.get("full_name")),
            "contact_title":contact.get("job_title"),
            "contact_email_enc":encrypt(contact.get("email")),
            "contact_source":contact.get("source"),
            "contact_verified":bool(contact_result.get("safe_to_send")),
            "contact_persona":contact.get("persona"),
            "raw_esg_data":json.dumps(esg_data),"raw_firmographic_data":json.dumps(firmographics),
            "compliance_gaps":json.dumps(gaps),"benchmark_delta":json.dumps({}),
            "data_quality_score":data_quality,"enrichment_sources":esg_data.get("_sources_used",[]),
        })
        row = await self.db.execute(text("SELECT id FROM prospects WHERE domain=:d"),{"d":domain})
        actual = row.scalar()
        return str(actual) if actual else pid

    async def _update_embedding(self, prospect_id: str, embedding: list[float]):
        if not any(embedding): return
        vec = "[" + ",".join(str(round(v,6)) for v in embedding) + "]"
        await self.db.execute(
            text("UPDATE prospects SET profile_embedding=:e::vector WHERE id=:id"),
            {"e":vec,"id":prospect_id},
        )

    async def _log_interaction(self, prospect_id, campaign_id, channel, variant, content, dispatched, persona, followup_num=1):
        await self.db.execute(text("""
            INSERT INTO interactions (id,prospect_id,campaign_id,channel,direction,event_type,
                subject,body_preview,ab_variant,persona,quality_score,confidence,
                personalization_score,hitl_reviewed,metadata)
            VALUES (:id,:pid,:cid,:ch,'outbound','sent',:subject,:body,:variant,:persona,
                :qs,:conf,:ps,false,:meta)
        """), {
            "id":str(uuid.uuid4()),"pid":prospect_id,"cid":campaign_id,"ch":channel,
            "subject":content.get("subject","")[:500],"body":content.get("body","")[:500],
            "variant":variant,"persona":persona,"qs":content.get("quality_score"),
            "conf":content.get("confidence"),"ps":content.get("personalization_score"),
            "meta":json.dumps({"dispatched":dispatched,"followup_num":followup_num}),
        })

    async def _queue_hitl(self, prospect_id, content, persona, channel, tier, gaps, competitor_info=None):
        top_gap = gaps[0] if gaps else {}
        tags    = [
            {"label":f"Tier {tier} prospect",                         "color":"red" if tier==3 else "amber"},
            {"label":f"Confidence {content.get('confidence',0):.0%}", "color":"amber"},
        ]
        if tier == 3: tags.append({"label":"Regulation-only messaging","color":"blue"})
        if competitor_info and competitor_info.get("detected"):
            tags.append({"label":f"Competitor: {competitor_info['tool']}","color":"purple"})
            tags.append({"label":f"Strategy: {competitor_info['strategy'].replace('_',' ')}","color":"purple"})

        reason = (
            f"AI confidence {content.get('confidence',0):.2f} below threshold. "
            + ("Tier 3 — no verified ESG data. " if tier==3 else "Human review recommended. ")
            + (f"Competitor detected: {competitor_info['tool']} — using {competitor_info['strategy'].replace('_',' ')}." if competitor_info and competitor_info.get("detected") else "")
        ).strip()

        await self.db.execute(text("""
            INSERT INTO hitl_items (id,prospect_id,workflow_run_id,channel,persona,
                esg_theme,subject,body,flag_reason,confidence,tier,tags,status)
            VALUES (:id,:pid,:run,:ch,:persona,:theme,:subj,:body,:reason,:conf,:tier,:tags,'pending')
        """), {
            "id":str(uuid.uuid4()),"pid":prospect_id,"run":self._run_id,"ch":channel,
            "persona":persona,"theme":top_gap.get("framework","ESG"),
            "subj":content.get("subject",""),"body":content.get("body",""),
            "reason":reason,"conf":content.get("confidence"),"tier":tier,
            "tags":json.dumps(tags),
        })

    @staticmethod
    def _wavg(pts: list) -> float:
        tw = sum(w for _,_,w in pts)
        if not tw: return 50.0
        return round(sum(s*w for _,s,w in pts)/tw, 1)

    @staticmethod
    def _parse_json_response(text_input: str) -> dict:
        import re
        t = text_input.strip()
        if t.startswith("```"):
            t = re.sub(r"```\w*","",t).strip()
        try: return json.loads(t)
        except Exception:
            m = re.search(r"\{.*\}",t,re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except Exception: pass
        return {"body":t,"subject":"","cta":"","opening_hook":"","ps_line":""}

    async def close(self):
        await self.http.aclose()
