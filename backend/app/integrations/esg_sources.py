"""
ESG Source Aggregator
Fetches from 6 sources in parallel, merges by quality priority.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Optional
import httpx
from app.core.settings import settings

log = logging.getLogger(__name__)

FIELD_MAP = {
    "resustain": {
        "carbon.scope1_tco2e":          "scope1_emissions_tco2e",
        "carbon.scope2_tco2e":          "scope2_emissions_tco2e",
        "carbon.scope3_tco2e":          "scope3_emissions_tco2e",
        "carbon.intensity":             "carbon_intensity",
        "energy.renewable_pct":         "renewable_energy_pct",
        "water.consumption_m3":         "water_consumption_m3",
        "water.recycled_pct":           "water_recycled_pct",
        "waste.total_tonnes":           "waste_generated_tonnes",
        "waste.recycled_pct":           "waste_recycled_pct",
        "supply_chain.audit_pct":       "supplier_esg_audit_pct",
        "social.ltir":                  "lost_time_injury_rate",
        "governance.board_committee":   "esg_board_committee",
        "governance.3p_verified":       "third_party_verified",
        "governance.report_published":  "sustainability_report_published",
    },
    "cdp": {
        "C6.1": "scope1_emissions_tco2e",
        "C6.3": "scope2_emissions_tco2e",
        "C6.5": "scope3_emissions_tco2e",
        "W1.2a": "water_consumption_m3",
    },
}

CRITICAL_FIELDS = [
    "scope1_emissions_tco2e","scope3_emissions_tco2e",
    "renewable_energy_pct","supplier_esg_audit_pct",
    "water_consumption_m3","sustainability_report_published",
    "sbti_committed",
]


class ESGSourceAggregator:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def fetch_all(self, domain: str) -> dict:
        if settings.USE_MOCK_ESG_DATA:
            return self._mock_data(domain)

        tasks = [
            self._fetch_resustain(domain),
            self._fetch_cdp(domain),
            self._fetch_sec_edgar(domain),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [(r, q) for r, q in results if isinstance(r, dict) and r]

        if not valid:
            log.warning("No ESG data found for %s — using LLM inference", domain)
            return {"_quality_score": 0.0, "_sources_used": [], "_all_inferred": True}

        merged = {}
        quality_by_field = {}
        sources_used = []

        for data, quality in sorted(valid, key=lambda x: -x[1]):
            sources_used.append(data.pop("_source", "unknown"))
            for k, v in data.items():
                if k.startswith("_"): continue
                if v is not None and quality > quality_by_field.get(k, 0):
                    merged[k] = v
                    quality_by_field[k] = quality

        present = sum(1 for f in CRITICAL_FIELDS if merged.get(f) is not None)
        merged["_quality_score"] = round(present / len(CRITICAL_FIELDS), 3)
        merged["_sources_used"] = sources_used
        return merged

    async def _fetch_resustain(self, domain: str) -> tuple[dict, float]:
        if not settings.RESUSTAIN_API_KEY:
            return {}, 0.0
        try:
            resp = await self.http.get(
                f"{settings.RESUSTAIN_API_BASE}/enterprises/{domain}/esg-metrics",
                headers={"X-API-Key": settings.RESUSTAIN_API_KEY},
                params={"include_supply_chain": True}
            )
            if resp.status_code == 200:
                raw = resp.json()
                data = self._map_fields(raw, "resustain")
                data["_source"] = "resustain"
                return data, 0.90
        except Exception as e:
            log.debug("resustain™ fetch failed for %s: %s", domain, e)
        return {}, 0.0

    async def _fetch_cdp(self, domain: str) -> tuple[dict, float]:
        if not settings.CDP_API_KEY:
            return {}, 0.0
        try:
            resp = await self.http.get(
                "https://api.cdp.net/v1/organizations",
                headers={"Authorization": f"Bearer {settings.CDP_API_KEY}"},
                params={"q": domain, "year": "2023"}
            )
            if resp.status_code == 200 and resp.json().get("organizations"):
                org_id = resp.json()["organizations"][0]["id"]
                data_resp = await self.http.get(
                    f"https://api.cdp.net/v1/organizations/{org_id}/responses",
                    headers={"Authorization": f"Bearer {settings.CDP_API_KEY}"},
                )
                if data_resp.status_code == 200:
                    raw = data_resp.json()
                    data = self._map_fields(raw, "cdp")
                    data["_source"] = "cdp"
                    return data, 0.85
        except Exception as e:
            log.debug("CDP fetch failed for %s: %s", domain, e)
        return {}, 0.0

    async def _fetch_sec_edgar(self, domain: str) -> tuple[dict, float]:
        company = domain.split(".")[0]
        try:
            resp = await self.http.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={"q": f'"{company}" emissions sustainability climate',
                        "forms": "10-K,20-F", "dateRange": "custom",
                        "startdt": "2023-01-01", "enddt": "2024-12-31"},
            )
            if resp.status_code == 200 and resp.json().get("hits", {}).get("hits"):
                return {"sustainability_report_published": True, "_source": "sec_edgar"}, 0.50
        except Exception as e:
            log.debug("SEC EDGAR fetch failed for %s: %s", domain, e)
        return {}, 0.0

    def _map_fields(self, raw: dict, source: str) -> dict:
        mapping = FIELD_MAP.get(source, {})
        result = {}
        for src_key, canonical_key in mapping.items():
            val = self._nested_get(raw, src_key)
            if val is not None:
                result[canonical_key] = val
        return result

    @staticmethod
    def _nested_get(data: dict, dotted_key: str):
        keys = dotted_key.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current

    @staticmethod
    def _mock_data(domain: str) -> dict:
        """Realistic mock data for development when USE_MOCK_ESG_DATA=true"""
        import hashlib
        seed = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16) % 100
        return {
            "scope1_emissions_tco2e":       seed * 12000,
            "scope2_emissions_tco2e":       seed * 8000,
            "scope3_emissions_tco2e":       seed * 120000,
            "total_carbon_footprint_tco2e": seed * 140000,
            "carbon_intensity":             round(seed * 0.15, 1),
            "renewable_energy_pct":         round(30 + seed * 0.4, 1),
            "water_consumption_m3":         seed * 180000,
            "water_recycled_pct":           round(35 + seed * 0.3, 1),
            "waste_generated_tonnes":       seed * 2200,
            "waste_recycled_pct":           round(60 + seed * 0.2, 1),
            "supplier_esg_audit_pct":       round(20 + seed * 0.5, 1),
            "sbti_committed":               seed > 60,
            "net_zero_target_year":         2040 if seed > 50 else None,
            "sustainability_report_published": seed > 30,
            "third_party_verified":         seed > 70,
            "esg_board_committee":          seed > 55,
            "lost_time_injury_rate":        round(0.1 + seed * 0.02, 2),
            "gender_pay_gap_pct":           round(5 + seed * 0.1, 1),
            "board_diversity_pct":          round(25 + seed * 0.3, 1),
            "_quality_score":               0.85,
            "_sources_used":               ["mock_data"],
        }
