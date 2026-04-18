import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Mail, Linkedin, MessageCircle, Play, BarChart2 } from "lucide-react";
import { campaignService } from "../../services/api";
import { Page, Skeleton, Modal } from "../ui";
import toast from "react-hot-toast";

const CH_ICON: Record<string, any> = { email: Mail, linkedin: Linkedin, whatsapp: MessageCircle };
const CH_COLOR: Record<string, string> = { email: "var(--accent-mint)", linkedin: "var(--accent-blue)", whatsapp: "var(--accent-mint)" };
const STEPS = ["Details", "Targeting", "Channels", "Review"];

function NewCampaignModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({ name: "", description: "", target: "", angle: "", channels: [] as string[], ab: true, persona: "cso" });

  const mutation = useMutation({
    mutationFn: () => campaignService.create({ name: form.name, description: form.description, channels: form.channels as any, ab_test_enabled: form.ab, persona: form.persona }),
    onSuccess: () => { toast.success("Campaign created"); qc.invalidateQueries({ queryKey: ["campaigns"] }); onClose(); setStep(0); setForm({ name: "", description: "", target: "", angle: "", channels: [], ab: true, persona: "cso" }); },
    onError: () => toast.error("Failed to create campaign"),
  });

  const toggleCh = (ch: string) => setForm(f => ({ ...f, channels: f.channels.includes(ch) ? f.channels.filter(c => c !== ch) : [...f.channels, ch] }));
  const canNext = [form.name.trim().length > 0, form.target.trim().length > 0, form.channels.length > 0, true][step];

  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <motion.div className="modal-box" style={{ maxWidth: 520 }} initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-head)", fontSize: 15, fontWeight: 600 }}>New campaign</h2>
          <button className="btn-ghost" style={{ padding: "4px 10px", fontSize: 18 }} onClick={onClose}>×</button>
        </div>
        <div style={{ display: "flex", gap: 6, marginBottom: 22 }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{ flex: 1, textAlign: "center" }}>
              <div style={{ height: 3, borderRadius: 99, marginBottom: 4, background: i <= step ? "var(--accent-mint)" : "var(--border)", transition: "background 0.3s" }} />
              <div style={{ fontSize: 10, color: i === step ? "var(--accent-mint)" : "var(--text-faint)" }}>{s}</div>
            </div>
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.15 }}>
            {step === 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div><label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Campaign name</label>
                  <input className="field" placeholder="e.g. CSRD Compliance Drive Q1 2025" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} /></div>
                <div><label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Target persona</label>
                  <select className="field" value={form.persona} onChange={e => setForm(f => ({ ...f, persona: e.target.value }))}>
                    <option value="cso">CSO / Chief Sustainability Officer</option>
                    <option value="cfo">CFO / Chief Financial Officer</option>
                    <option value="head_supply_chain">Head of Supply Chain</option>
                    <option value="sustainability_manager">Sustainability Manager</option>
                  </select></div>
              </div>
            )}
            {step === 1 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div><label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Target description</label>
                  <textarea className="field" rows={3} placeholder="Describe the companies this campaign targets — industry, geography, size, ESG gap type…" value={form.target} onChange={e => setForm(f => ({ ...f, target: e.target.value }))} style={{ width: "100%", resize: "none" }} /></div>
                <div><label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Message angle</label>
                  <textarea className="field" rows={2} placeholder="What ESG theme will this campaign focus on?" value={form.angle} onChange={e => setForm(f => ({ ...f, angle: e.target.value }))} style={{ width: "100%", resize: "none" }} /></div>
              </div>
            )}
            {step === 2 && (
              <div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>Select outreach channels</div>
                <div className="grid-2" style={{ marginBottom: 14 }}>
                  {["email","linkedin","whatsapp"].map(ch => {
                    const Icon = CH_ICON[ch];
                    const active = form.channels.includes(ch);
                    return (
                      <div key={ch} onClick={() => toggleCh(ch)} style={{ padding: "14px", borderRadius: "0.9rem", cursor: "pointer",
                        border: `0.5px solid ${active ? CH_COLOR[ch] : "var(--border)"}`,
                        background: active ? `${CH_COLOR[ch]}12` : "var(--bg-card2)",
                        display: "flex", alignItems: "center", gap: 10, transition: "all 0.15s",
                        boxShadow: active ? `0 0 14px -5px ${CH_COLOR[ch]}60` : "none" }}>
                        <Icon size={16} color={active ? CH_COLOR[ch] : "var(--text-faint)"} />
                        <span style={{ fontSize: 13, color: active ? "var(--text-primary)" : "var(--text-faint)" }}>
                          {ch.charAt(0).toUpperCase() + ch.slice(1)}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" id="ab" checked={form.ab} onChange={e => setForm(f => ({ ...f, ab: e.target.checked }))} />
                  <label htmlFor="ab" style={{ fontSize: 12, color: "var(--text-muted)", cursor: "pointer" }}>
                    Enable A/B testing (data-led vs narrative-led variants)
                  </label>
                </div>
              </div>
            )}
            {step === 3 && (
              <div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>Review before creating</div>
                {[["Name", form.name], ["Persona", form.persona.replace(/_/g," ")], ["Target", form.target], ["Channels", form.channels.join(", ") || "None"], ["A/B Testing", form.ab ? "Enabled" : "Disabled"]].map(([l,v]) => (
                  <div key={l} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "0.5px solid var(--border)", fontSize: 12 }}>
                    <span style={{ color: "var(--text-faint)", minWidth: 80 }}>{l}</span>
                    <span style={{ color: "var(--text-primary)", flex: 1 }}>{v}</span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 22 }}>
          <button className="btn-ghost" onClick={() => step > 0 ? setStep(s => s - 1) : onClose()}>{step === 0 ? "Cancel" : "Back"}</button>
          <button className="btn-primary" disabled={!canNext || mutation.isPending}
            onClick={() => step < 3 ? setStep(s => s + 1) : mutation.mutate()}>
            {step < 3 ? "Continue →" : mutation.isPending ? "Creating…" : "Create campaign"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function CampaignCard({ c, idx }: { c: any; idx: number }) {
  const qc = useQueryClient();
  const launch = useMutation({
    mutationFn: () => campaignService.launch(c.id),
    onSuccess: () => { toast.success(`${c.name} launched`); qc.invalidateQueries({ queryKey: ["campaigns"] }); },
  });
  const isActive = c.status === "active";
  const channels: string[] = c.channels || [];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }} className="card">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <span style={{ fontFamily: "var(--font-head)", fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{c.name}</span>
            <span className={`pill ${isActive ? "pill-mint" : "pill-gray"}`}>{isActive ? "Active" : "Draft"}</span>
            {c.ab_test_enabled && <span className="pill pill-purple">A/B</span>}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {channels.map(ch => { const Icon = CH_ICON[ch]; return Icon ? (
              <div key={ch} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Icon size={11} color={CH_COLOR[ch]} />
                <span style={{ fontSize: 11, color: CH_COLOR[ch], fontWeight: 500 }}>{ch.charAt(0).toUpperCase() + ch.slice(1)}</span>
              </div>
            ) : null; })}
          </div>
        </div>
        {!isActive && (
          <button className="btn-primary" style={{ fontSize: 11, padding: "5px 12px" }}
            onClick={() => launch.mutate()} disabled={launch.isPending}>
            <Play size={11} /> {launch.isPending ? "Launching…" : "Launch"}
          </button>
        )}
      </div>
      {c.description && (
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 10, lineHeight: 1.5 }}>{c.description}</div>
      )}
      {isActive ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0,
                      background: "rgba(255,255,255,0.03)", border: "0.5px solid var(--border)",
                      borderRadius: "0.75rem", overflow: "hidden" }}>
          {[["Sent", c.total_sent || 0, null], ["Open rate", c.total_sent ? `${Math.round((c.total_opened||0)/(c.total_sent||1)*100)}%` : "—", "var(--accent-mint)"],
            ["Reply rate", c.total_sent ? `${Math.round((c.total_replied||0)/(c.total_sent||1)*100)}%` : "—", "var(--accent-blue)"],
            ["Demos", c.total_demos || 0, "var(--accent-mint)"]].map(([l,v,clr], j) => (
            <div key={j} style={{ padding: "10px", textAlign: "center", borderRight: j < 3 ? "0.5px solid var(--border)" : "none" }}>
              <div style={{ fontFamily: "var(--font-head)", fontSize: 16, fontWeight: 700, color: (clr as string) || "var(--text-primary)" }}>{String(v)}</div>
              <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>{String(l)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ padding: "10px", background: "rgba(255,255,255,0.02)", border: "0.5px dashed var(--border)",
                      borderRadius: "0.75rem", textAlign: "center", fontSize: 12, color: "var(--text-faint)",
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
          <BarChart2 size={13} /> Launch to start collecting metrics
        </div>
      )}
    </motion.div>
  );
}

export default function Campaigns() {
  const { data: campaigns = [], isLoading } = useQuery({ queryKey: ["campaigns"], queryFn: campaignService.getAll });
  const [modalOpen, setModalOpen] = useState(false);
  const active = campaigns.filter((c: any) => c.status === "active");
  const drafts  = campaigns.filter((c: any) => c.status !== "active");

  return (
    <Page title="Campaigns" action={<button className="btn-primary" onClick={() => setModalOpen(true)}><Plus size={14} /> New campaign</button>}>
      {isLoading ? [0,1,2].map(i => <Skeleton key={i} h={140} />) : (
        <>
          {active.length > 0 && (
            <><div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 10 }}>Active · {active.length}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 22 }}>{active.map((c: any, i: number) => <CampaignCard key={c.id} c={c} idx={i} />)}</div></>
          )}
          {drafts.length > 0 && (
            <><div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 10 }}>Drafts · {drafts.length}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>{drafts.map((c: any, i: number) => <CampaignCard key={c.id} c={c} idx={active.length + i} />)}</div></>
          )}
          {campaigns.length === 0 && (
            <div className="card" style={{ textAlign: "center", padding: "60px 20px" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📣</div>
              <div style={{ fontSize: 13, color: "var(--text-faint)" }}>No campaigns yet — create your first one</div>
            </div>
          )}
        </>
      )}
      <AnimatePresence>{modalOpen && <NewCampaignModal open={modalOpen} onClose={() => setModalOpen(false)} />}</AnimatePresence>
    </Page>
  );
}
