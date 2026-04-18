import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Page, Skeleton } from "../ui";
import { analyticsService } from "../../services/api";

const AGENTS = [
  { id: "esg_ingestion",        name: "ESG Ingestion",          status: "idle",      desc: "Fetches ESG data from 6 external sources simultaneously — resustain™, CDP, Bloomberg ESG, Refinitiv, GRI, and SEC EDGAR. Normalizes all data to a single standard schema. Uses AI to estimate missing fields when data is incomplete.", stats: [{ label: "Runs today", value: "38" }, { label: "Avg. latency", value: "3.2s" }, { label: "Avg. quality", value: "0.81" }] },
  { id: "firmographic",         name: "Firmographic Profiling", status: "idle",      desc: "Infers company name, industry, revenue band, employee count, and operating regions from the domain using LLM knowledge. Computes ICP fit score (0–1) against Treeni's target market criteria.", stats: [{ label: "Runs today", value: "38" }, { label: "Avg. latency", value: "0.8s" }, { label: "Avg. ICP fit", value: "0.79" }] },
  { id: "scoring",              name: "ESG Scoring",            status: "idle",      desc: "Calculates composite ESG score (0–100) from Environment, Social, and Governance sub-scores. Benchmarks each metric against industry-specific peer medians. Computes decarbonization urgency and supply chain risk.", stats: [{ label: "Runs today", value: "38" }, { label: "Avg. latency", value: "0.01s" }, { label: "Pure math", value: "no I/O" }] },
  { id: "compliance",           name: "Compliance Analysis",    status: "idle",      desc: "Maps each company against 9 ESG frameworks: CSRD, EUDR, CSDDD, BRSR, TCFD, CDP, SEC Climate, SBTi, ISO14001. Identifies specific gaps with severity, deadline countdown, penalty exposure, and resustain™ module mapping.", stats: [{ label: "Runs today", value: "38" }, { label: "Avg. latency", value: "0.01s" }, { label: "Pure logic", value: "no I/O" }] },
  { id: "contact",              name: "Contact Sourcing",       status: "idle",      desc: "Finds the right contact (CSO, CFO, VP Supply Chain) via Apollo.io as primary source and Hunter.io as fallback. Verifies every email via ZeroBounce before storing. Encrypts all PII with AES-256.", stats: [{ label: "Runs today", value: "36" }, { label: "Avg. latency", value: "2.1s" }, { label: "Verified rate", value: "82%" }] },
  { id: "embedding",            name: "Vector Embedding",       status: "idle",      desc: "Converts each company profile into a 1,536-dimension embedding using OpenAI text-embedding-3-small. Stores in PostgreSQL via pgvector. Queries for similar companies when generating content.", stats: [{ label: "Stored", value: "1,847" }, { label: "Avg. latency", value: "0.9s" }, { label: "DB", value: "pgvector" }] },
  { id: "content_generation",   name: "Content Generation",     status: "running",   desc: "Uses chain-of-thought prompting to write personalized outreach messages grounded in the company's own ESG data. Generates A/B variants. Scores quality with LLM-as-Judge across 5 dimensions. Routes low-confidence outputs to HITL.", stats: [{ label: "Messages today", value: "36" }, { label: "Avg. latency", value: "7.2s" }, { label: "Avg. quality", value: "0.84" }] },
  { id: "dispatch",             name: "Multi-Channel Dispatch", status: "waiting",   desc: "Runs 5 pre-send checks before any message goes out: opt-in status, email availability, suppression list, ZeroBounce verification, 7-day cooldown. Routes to SendGrid (email), LinkedIn, or WhatsApp. Sends at optimal local time.", stats: [{ label: "Sent today", value: "34" }, { label: "Bounce rate", value: "0.4%" }, { label: "Avg. latency", value: "1.1s" }] },
  { id: "optimization",         name: "RL Optimization",        status: "scheduled", desc: "Runs weekly. Analyzes reward signals from all engagement events. Runs z-test A/B analysis (95% confidence required). Updates prompt template scores via policy gradient. Scales winning variants to 100% traffic.", stats: [{ label: "Last run", value: "3d ago" }, { label: "Schedule", value: "Weekly Mon" }, { label: "Templates", value: "6 updated" }] },
];

const STATUS_DOT: Record<string, string> = {
  idle: "var(--accent-mint)", running: "var(--accent-blue)",
  waiting: "var(--accent-amber)", failed: "var(--accent-red)", scheduled: "var(--text-faint)",
};
const STATUS_PILL: Record<string, string> = {
  idle: "pill-mint", running: "pill-blue",
  waiting: "pill-amber", failed: "pill-red", scheduled: "pill-gray",
};

export default function AgentsView() {
  const { data: dashboard } = useQuery({ queryKey: ["dashboard"], queryFn: analyticsService.getDashboard });

  const statusCounts = AGENTS.reduce((a, ag) => { a[ag.status] = (a[ag.status] || 0) + 1; return a; }, {} as Record<string, number>);

  return (
    <Page title="AI agents">
      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        {[
          { label: "Total agents", value: "9",                              color: "var(--text-primary)" },
          { label: "Running",      value: String(statusCounts.running || 0), color: "var(--accent-blue)"  },
          { label: "Idle",         value: String(statusCounts.idle || 0),    color: "var(--accent-mint)"  },
          { label: "Scheduled",    value: String(statusCounts.scheduled || 0),color: "var(--text-faint)"  },
        ].map(s => (
          <div key={s.label} className="card-sm" style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-head)", fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
        <div className="card-sm" style={{ flex: 2, fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
          All 9 pipeline stages run inside a single Python process. No inter-service hops.
          Pure-function stages execute in microseconds. I/O stages run concurrently.
        </div>
      </div>

      <div className="grid-2">
        {AGENTS.map((agent, i) => (
          <motion.div key={agent.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }} className="card"
            style={{ border: `0.5px solid ${agent.status === "running" ? "rgba(55,138,221,0.25)" : "var(--border)"}`,
                     boxShadow: agent.status === "running" ? "var(--glow-blue)" : "none" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS_DOT[agent.status] || "gray" }}
                  className={agent.status === "running" ? "pulse-glow" : ""} />
                <div style={{ fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                  {agent.name}
                </div>
              </div>
              <span className={`pill ${STATUS_PILL[agent.status] || "pill-gray"}`}>
                {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
              </span>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.55, marginBottom: 12 }}>{agent.desc}</p>
            <div style={{ display: "flex", gap: 0, background: "rgba(255,255,255,0.03)",
                          border: "0.5px solid var(--border)", borderRadius: "0.75rem", overflow: "hidden" }}>
              {agent.stats.map((stat, j) => (
                <div key={j} style={{ flex: 1, padding: "9px 10px", textAlign: "center",
                                      borderRight: j < agent.stats.length - 1 ? "0.5px solid var(--border)" : "none" }}>
                  <div style={{ fontFamily: "var(--font-head)", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                    {stat.value}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </Page>
  );
}
