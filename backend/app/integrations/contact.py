"""Contact sourcing: Apollo → Hunter → ZeroBounce verification"""
from __future__ import annotations
import logging
from typing import Optional
import httpx
from app.core.settings import settings

log = logging.getLogger(__name__)

PERSONA_FILTERS = {
    "cso": {
        "person_titles": ["Chief Sustainability Officer","VP Sustainability","Head of ESG","Director Sustainability"],
        "person_seniority": ["c_suite","vp","director"],
    },
    "cfo": {
        "person_titles": ["Chief Financial Officer","VP Finance","Finance Director"],
        "person_seniority": ["c_suite","vp"],
    },
    "head_supply_chain": {
        "person_titles": ["Head of Supply Chain","VP Supply Chain","Chief Supply Chain Officer","VP Procurement"],
        "person_seniority": ["c_suite","vp","director"],
    },
    "sustainability_manager": {
        "person_titles": ["Sustainability Manager","ESG Manager","CSR Manager","Environmental Manager"],
        "person_seniority": ["manager","senior"],
    },
}

SUSTAINABILITY_KEYWORDS = ["sustainability","esg","environment","climate","carbon","csr"]
SUPPLY_CHAIN_KEYWORDS   = ["supply chain","procurement","sourcing","logistics"]
FINANCE_KEYWORDS        = ["cfo","finance","financial","chief financial"]

SENDABLE = {"valid","catch-all"}


class ContactIntelligenceService:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def find_and_verify(self, domain: str, company_name: str, persona: str = "cso") -> dict:
        contact = await self._apollo(domain, persona)
        source  = "apollo"

        if not contact:
            contact = await self._hunter(domain, persona)
            source  = "hunter"

        if not contact:
            return {
                "contact": {"found": False, "requires_manual": True, "persona": persona,
                            "manual_hint": f"Search LinkedIn: {company_name} {persona.replace('_',' ')}"},
                "verification": None, "safe_to_send": False, "sources_tried": ["apollo","hunter"],
            }

        contact["source"]  = source
        contact["persona"] = persona
        contact["found"]   = True

        verification = None
        safe = False
        if contact.get("email"):
            verification = await self._zerobounce(contact["email"])
            safe = verification.get("valid", False)
            if not safe and source == "apollo":
                alt = await self._hunter(domain, persona)
                if alt and alt.get("email") and alt["email"] != contact["email"]:
                    alt_v = await self._zerobounce(alt["email"])
                    if alt_v.get("valid"):
                        contact["email"] = alt["email"]
                        verification = alt_v
                        safe = True

        return {"contact": contact, "verification": verification,
                "safe_to_send": safe, "sources_tried": [source]}

    async def _apollo(self, domain: str, persona: str) -> Optional[dict]:
        if not settings.APOLLO_API_KEY:
            return None
        filters = PERSONA_FILTERS.get(persona, PERSONA_FILTERS["cso"])
        try:
            resp = await self.http.post(
                "https://api.apollo.io/v1/mixed_people/search",
                headers={"X-Api-Key": settings.APOLLO_API_KEY, "Content-Type": "application/json"},
                json={"q_organization_domains": domain, "page": 1, "per_page": 5, **filters},
            )
            if resp.status_code == 200:
                people = resp.json().get("people", [])
                if people:
                    p = max(people, key=lambda x: {"c_suite":4,"vp":3,"director":2,"manager":1}.get(x.get("seniority",""),0))
                    email = p.get("email")
                    if not email and p.get("id"):
                        email = await self._apollo_reveal(p["id"])
                    return {
                        "full_name": p.get("name"), "first_name": p.get("first_name"),
                        "email": email, "job_title": p.get("title"),
                        "linkedin_url": p.get("linkedin_url"), "seniority": p.get("seniority"),
                        "confidence": 0.87 if email else 0.55,
                    }
        except Exception as e:
            log.debug("Apollo failed for %s: %s", domain, e)
        return None

    async def _apollo_reveal(self, person_id: str) -> Optional[str]:
        try:
            resp = await self.http.post(
                "https://api.apollo.io/v1/people/match",
                headers={"X-Api-Key": settings.APOLLO_API_KEY},
                json={"id": person_id, "reveal_personal_emails": False},
            )
            if resp.status_code == 200:
                return resp.json().get("person", {}).get("email")
        except Exception:
            pass
        return None

    async def _hunter(self, domain: str, persona: str) -> Optional[dict]:
        if not settings.HUNTER_API_KEY:
            return None
        try:
            resp = await self.http.get(
                "https://api.hunter.io/v2/domain-search",
                params={"domain": domain, "api_key": settings.HUNTER_API_KEY, "limit": 10},
            )
            if resp.status_code == 200:
                emails = resp.json().get("data", {}).get("emails", [])
                if emails:
                    def score(e):
                        t = (e.get("position") or "").lower()
                        if any(k in t for k in SUSTAINABILITY_KEYWORDS): return 100
                        if any(k in t for k in SUPPLY_CHAIN_KEYWORDS):   return 80
                        if any(k in t for k in FINANCE_KEYWORDS):        return 60
                        return e.get("confidence", 0)
                    best = max(emails, key=score)
                    name = f"{best.get('first_name','')} {best.get('last_name','')}".strip()
                    return {
                        "full_name": name or None, "first_name": best.get("first_name"),
                        "email": best.get("value"), "job_title": best.get("position"),
                        "linkedin_url": best.get("linkedin"),
                        "confidence": min((best.get("confidence", 50)) / 100, 0.90),
                    }
        except Exception as e:
            log.debug("Hunter failed for %s: %s", domain, e)
        return None

    async def _zerobounce(self, email: str) -> dict:
        if not settings.ZEROBOUNCE_API_KEY:
            return {"valid": True, "status": "unknown", "verified": False}
        try:
            resp = await self.http.get(
                "https://api.zerobounce.net/v2/validate",
                params={"api_key": settings.ZEROBOUNCE_API_KEY, "email": email, "ip_address": ""},
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown").lower()
                return {
                    "valid": status in SENDABLE, "status": status,
                    "verified": True, "smtp_provider": data.get("smtp_provider"),
                }
        except Exception as e:
            log.debug("ZeroBounce failed for %s: %s", email, e)
        return {"valid": True, "status": "unknown", "verified": False}
