// ─────────────────────────────────────────────
// Prospects page
// ─────────────────────────────────────────────
import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Plus, ChevronRight, X } from "lucide-react";
import { apiService } from "../../services/api";
import { Page, Avatar, Pill, Meter, GapBadge, Modal, Skeleton } from "../ui";
import toast from "react-hot-toast";

function AddProspectModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [domain, setDomain]   = useState("");
  const [persona, setPersona] = useState("cso");
  const [channel, setChannel] = useState("email");

  const mut = useMutation({
    mutationFn: () => apiService.runProspect(domain.trim(), persona, channel),
    onSuccess: () => { toast.success(`Workflow started for ${domain}`); qc.invalidateQueries({queryKey:["prospects"]}); onClose(); setDomain(""); },
    onError:   () => toast.error("Failed to start workflow"),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add new prospect">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Company domain</label>
          <input className="field" placeholder="e.g. bosch.com" value={domain} onChange={e => setDomain(e.target.value)} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Target persona</label>
            <select className="field" value={persona} onChange={e => setPersona(e.target.value)}>
              <option value="cso">CSO / Sustainability</option>
              <option value="cfo">CFO / Finance</option>
              <option value="head_supply_chain">Head of Supply Chain</option>
              <option value="sustainability_manager">Sustainability Manager</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Channel</label>
            <select className="field" value={channel} onChange={e => setChannel(e.target.value)}>
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", padding: "9px 11px", background: "rgba(115,207,168,0.06)", border: "0.5px solid rgba(115,207,168,0.15)", borderRadius: 8 }}>
          Triggers the full AI pipeline: ESG fetch → scoring → compliance → content → dispatch (~10s)
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={() => mut.mutate()} disabled={!domain.trim() || mut.isPending}>
            {mut.isPending ? "Starting…" : "Start AI pipeline"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

function ProspectDrawer({ p, onClose }: { p: any; onClose: () => void }) {
  if (!p) return null;
  const sc = (v: number) => v >= 60 ? "var(--accent-mint)" : v >= 40 ? "var(--accent-amber)" : "var(--accent-red)";
  return (
    <AnimatePresence>
      <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 28, stiffness: 300 }}
        style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 360, zIndex: 40, background: "var(--bg-card)", borderLeft: "0.5px solid var(--border)", overflowY: "auto", padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Avatar initials={p.initials} bg={p.avatarBg} color={p.avatarColor} size={34} />
            <div>
              <div style={{ fontFamily: "var(--font-head)", fontWeight: 600, fontSize: 13 }}>{p.company}</div>
              <div style={{ fontSize: 10, color: "var(--text-faint)" }}>{p.industry} · {p.country}</div>
            </div>
          </div>
          <button className="btn-ghost" style={{ padding: "4px 9px" }} onClick={onClose}><X size={13} /></button>
        </div>

        <div style={{ textAlign: "center", margin: "18px 0" }}>
          <div style={{ fontFamily: "var(--font-head)", fontSize: 44, fontWeight: 800, color: sc(p.esgScore), lineHeight: 1 }}>{p.esgScore}</div>
          <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 3 }}>ESG Score / 100</div>
        </div>

        <div className="card-sm" style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text-faint)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>ESG Metrics</div>
          {(p.esgMetrics || []).map((m: any, i: number) => <Meter key={i} label={m.label} value={m.value} pct={m.pct} color={m.color} />)}
        </div>

        {(p.complianceGaps || []).length > 0 && (
          <div className="card-sm" style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text-faint)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>Compliance Gaps</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {p.complianceGaps.map((g: any, i: number) => <GapBadge key={i} label={g.label} severity={g.severity} />)}
            </div>
          </div>
        )}

        {p.contactName && (
          <div className="card-sm">
            <div style={{ fontSize: 10, fontWeight: 600, color: "var(--text-faint)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>Contact</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{p.contactName}</div>
            <div style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 8 }}>{p.contactTitle}</div>
            {p.emailVerified && <span className="pill pill-mint">✓ Email verified</span>}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

export default function Prospects() {
  const { data: prospects = [], isLoading } = useQuery({ queryKey: ["prospects"], queryFn: apiService.getProspects });
  const [search, setSearch]   = useState("");
  const [industry, setIndustry] = useState("All");
  const [tier, setTier]       = useState("All");
  const [selected, setSelected] = useState<any>(null);
  const [addOpen, setAddOpen] = useState(false);

  const filtered = useMemo(() => prospects.filter((p: any) => {
    const ms = p.company?.toLowerCase().includes(search.toLowerCase()) || p.industry?.toLowerCase().includes(search.toLowerCase());
    const mi = industry === "All" || p.industry === industry;
    const mt = tier === "All" || String(p.tier) === tier.replace("Tier ","");
    return ms && mi && mt;
  }), [prospects, search, industry, tier]);

  const sc = (v: number) => v >= 60 ? "var(--accent-mint)" : v >= 40 ? "var(--accent-amber)" : "var(--accent-red)";

  return (
    <Page title="All prospects" action={<button className="btn-primary" onClick={() => setAddOpen(true)}><Plus size={13} /> Add prospect</button>}>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 160 }}>
          <Search size={12} color="var(--text-faint)" style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }} />
          <input className="field" style={{ paddingLeft: 28 }} placeholder="Search…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        {["All","Automotive","Manufacturing","Chemicals","Steel","Food & Beverage"].map(i => (
          <button key={i} onClick={() => setIndustry(i)}
            style={{ fontSize: 11, padding: "6px 12px", borderRadius: 20, border: `0.5px solid ${industry===i ? "var(--accent-mint)" : "var(--border)"}`, background: industry===i ? "rgba(115,207,168,0.1)" : "transparent", color: industry===i ? "var(--accent-mint)" : "var(--text-faint)", cursor: "pointer" }}>
            {i}
          </button>
        ))}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table" style={{ tableLayout: "fixed", width: "100%" }}>
          <colgroup>
            <col style={{ width: "30%" }} /><col style={{ width: "12%" }} />
            <col style={{ width: "15%" }} /><col style={{ width: "9%" }} />
            <col style={{ width: "20%" }} /><col style={{ width: "14%" }} />
          </colgroup>
          <thead>
            <tr>
              <th style={{ paddingLeft: 18 }}>Company</th>
              <th>Industry</th><th>ESG score</th><th>Tier</th>
              <th>Top gap</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? [0,1,2,3,4].map(i => (
              <tr key={i}>{[0,1,2,3,4,5].map(j => <td key={j}><Skeleton h={11} /></td>)}</tr>
            )) : filtered.map((p: any, idx: number) => (
              <motion.tr key={p.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.025 }} style={{ cursor: "pointer" }}
                onClick={() => setSelected(p)}>
                <td style={{ paddingLeft: 18 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                    <Avatar initials={p.initials} bg={p.avatarBg} color={p.avatarColor} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>{p.company}</div>
                      <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 1 }}>{p.sub}</div>
                    </div>
                  </div>
                </td>
                <td style={{ fontSize: 11 }}>{p.industry}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                    <div style={{ flex: 1 }}>
                      <div className="meter-track"><div className="meter-fill" style={{ width: `${p.esgScore}%`, background: sc(p.esgScore) }} /></div>
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 600, color: sc(p.esgScore), minWidth: 24 }}>{p.esgScore}</span>
                  </div>
                </td>
                <td><Pill label={p.tier} color="blue" /></td>
                <td style={{ fontSize: 11, color: "var(--text-muted)" }}>{p.topGap}</td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Pill label={p.statusLabel} color={p.statusColor as any} />
                    <ChevronRight size={11} color="var(--text-faint)" />
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <AddProspectModal open={addOpen} onClose={() => setAddOpen(false)} />
      <ProspectDrawer p={selected} onClose={() => setSelected(null)} />
    </Page>
  );
}
