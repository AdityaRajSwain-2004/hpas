import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Loader, Clock, AlertCircle, Play } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { prospectService, workflowService } from "../../services/api";
import { Page, Meter, Skeleton } from "../ui";
import toast from "react-hot-toast";

function StepIcon({ state }: { state: string }) {
  if (state === "done") return <CheckCircle size={16} color="var(--accent-mint)" />;
  if (state === "running") return (
    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}>
      <Loader size={16} color="var(--accent-blue)" />
    </motion.div>
  );
  if (state === "failed") return <AlertCircle size={16} color="var(--accent-red)" />;
  return <Clock size={16} color="var(--text-faint)" />;
}

export default function WorkflowView() {
  const [domain, setDomain] = useState("");
  const [persona, setPersona] = useState("cso");
  const [channel, setChannel] = useState("email");
  const [activeJob, setActiveJob] = useState<any>(null);

  const runMutation = useMutation({
    mutationFn: (d: string) => prospectService.runSync(d, persona, channel),
    onSuccess: (data) => {
      setActiveJob(data);
      toast.success(`Pipeline complete for ${data.domain || domain}`);
    },
    onError: () => toast.error("Pipeline failed — check API keys and try again"),
  });

  const { data: workflow } = useQuery({
    queryKey: ["workflow-mock"],
    queryFn: workflowService.getActive,
    enabled: !activeJob,
  });

  const display = activeJob || workflow;

  const DEMO_STEPS = [
    { num: 1, state: "done",    name: "ESG data ingestion",     detail: "6 sources queried in parallel · quality score computed", time: "3.2s" },
    { num: 2, state: "done",    name: "Firmographic profiling",  detail: "Industry, revenue, regions inferred · ICP fit scored",   time: "0.8s" },
    { num: 3, state: "done",    name: "ESG scoring",             detail: "E/S/G sub-scores · benchmarked vs industry peers",       time: "0.01s" },
    { num: 4, state: "done",    name: "Compliance analysis",     detail: "9 frameworks checked · gaps detected · penalties mapped", time: "0.01s" },
    { num: 5, state: "done",    name: "Contact sourcing",        detail: "Apollo.io → Hunter.io → ZeroBounce verification",        time: "2.1s" },
    { num: 6, state: "done",    name: "Vector embedding",        detail: "1536-dim profile embedding · pgvector similarity search", time: "0.9s" },
    { num: 7, state: "running", name: "Content generation",      detail: "Chain-of-thought · A/B variants · LLM-as-Judge scoring", time: "running…" },
    { num: 8, state: "pending", name: "Dispatch / HITL gate",    detail: "Confidence threshold check · send or queue for review",  time: "—" },
  ];

  const steps = display?.steps || DEMO_STEPS;
  const completed = steps.filter((s: any) => s.state === "done").length;

  return (
    <Page title="Live workflow">
      {/* Run form */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12 }}>
          Run pipeline for a new prospect
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 2, minWidth: 200 }}>
            <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Company domain</label>
            <input className="field" placeholder="e.g. bosch.com" value={domain} onChange={e => setDomain(e.target.value)}
              onKeyDown={e => e.key === "Enter" && domain && runMutation.mutate(domain)} />
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Target persona</label>
            <select className="field" value={persona} onChange={e => setPersona(e.target.value)}>
              <option value="cso">CSO / Sustainability</option>
              <option value="cfo">CFO / Finance</option>
              <option value="head_supply_chain">Head of Supply Chain</option>
              <option value="sustainability_manager">Sustainability Manager</option>
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 120 }}>
            <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>Channel</label>
            <select className="field" value={channel} onChange={e => setChannel(e.target.value)}>
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>
          <button className="btn-primary" style={{ height: 38 }}
            onClick={() => domain && runMutation.mutate(domain)}
            disabled={runMutation.isPending || !domain}>
            <Play size={13} />
            {runMutation.isPending ? "Running…" : "Run pipeline"}
          </button>
        </div>
      </div>

      {/* Status bar */}
      {(runMutation.isPending || display) && (
        <div className="card-sm" style={{ marginBottom: 14, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>
              {display?.company_name || domain || "Pipeline"}
            </span>
            <span style={{ fontSize: 11, color: "var(--text-faint)", marginLeft: 10 }}>
              {runMutation.isPending ? "Processing…" : `ESG score: ${display?.esg_score || "—"}/100 · Tier ${display?.prospect_tier || "—"}`}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 100 }}>
              <div className="meter-track">
                <motion.div className="meter-fill" style={{ background: "var(--accent-mint)" }}
                  animate={{ width: `${(completed / steps.length) * 100}%` }}
                  transition={{ duration: 0.6 }} />
              </div>
            </div>
            <span style={{ fontSize: 11, color: "var(--accent-mint)", fontWeight: 600 }}>
              {completed}/{steps.length}
            </span>
          </div>
          {display?.dispatched && <span className="pill pill-mint">✓ Dispatched</span>}
          {display?.requires_hitl && <span className="pill pill-amber">Review needed</span>}
        </div>
      )}

      <div className="grid-2">
        {/* Timeline */}
        <div className="card">
          <div style={{ fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 600, marginBottom: 18 }}>
            Agent execution trace
          </div>
          {steps.map((step: any, i: number) => (
            <motion.div key={step.num} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              style={{ display: "flex", alignItems: "flex-start", gap: 12, paddingBottom: 16,
                       position: "relative", opacity: step.state === "pending" ? 0.4 : 1 }}>
              {i < steps.length - 1 && (
                <div style={{ position: "absolute", left: 7, top: 20, bottom: 0, width: 2,
                              background: step.state === "done" ? "rgba(115,207,168,0.3)" : "var(--border)" }} />
              )}
              <div style={{ zIndex: 1, marginTop: 2 }} className={step.state === "running" ? "pulse-glow" : ""}>
                <StepIcon state={step.state} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: step.state === "running" ? "var(--accent-blue)" : "var(--text-primary)", fontFamily: "var(--font-head)" }}>
                    {step.name}
                  </div>
                  <span style={{ fontSize: 10, color: step.state === "running" ? "var(--accent-blue)" : "var(--text-faint)", fontWeight: 600 }}>
                    {step.time}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>
                  {step.detail}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Right panel */}
        <div>
          {/* Result card */}
          {activeJob && (
            <div className="card" style={{ marginBottom: 14, boxShadow: "var(--glow-mint)" }}>
              <div style={{ fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 600, marginBottom: 14 }}>
                Pipeline result — {activeJob.company_name}
              </div>
              {[
                ["ESG Score",       `${activeJob.esg_score}/100`],
                ["Prospect Tier",   `Tier ${activeJob.prospect_tier}`],
                ["Confidence",      `${Math.round((activeJob.confidence || 0) * 100)}%`],
                ["Quality Score",   `${Math.round((activeJob.quality_score || 0) * 100)}%`],
                ["Dispatched",      activeJob.dispatched ? "Yes" : "No"],
                ["HITL Required",   activeJob.requires_hitl ? "Yes — review queue" : "No"],
                ["Latency",         `${activeJob.latency_ms}ms`],
              ].map(([label, value]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 6 }}>
                  <span style={{ color: "var(--text-faint)" }}>{label}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
                </div>
              ))}
              {activeJob.compliance_gaps?.length > 0 && (
                <>
                  <div style={{ height: 0.5, background: "var(--border)", margin: "10px 0" }} />
                  <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-faint)", marginBottom: 6 }}>
                    Compliance gaps detected
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                    {activeJob.compliance_gaps.slice(0, 3).map((g: any, i: number) => (
                      <span key={i} className={`pill ${g.severity === "critical" ? "pill-red" : "pill-amber"}`}>
                        {g.framework} — {g.severity}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Content preview */}
          {activeJob?.content && (
            <div className="card">
              <div style={{ fontFamily: "var(--font-head)", fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
                Generated message — Variant {activeJob.content.variant}
              </div>
              {activeJob.content.subject && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 3 }}>SUBJECT</div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>
                    {activeJob.content.subject}
                  </div>
                </div>
              )}
              <div style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.6,
                            padding: "10px 12px", background: "rgba(255,255,255,0.03)",
                            borderRadius: "0.6rem", border: "0.5px solid var(--border)", maxHeight: 180, overflow: "auto" }}>
                {activeJob.content.body}
              </div>
              {activeJob.content.cta && (
                <div style={{ marginTop: 8, fontSize: 11, color: "var(--accent-mint)", fontWeight: 500 }}>
                  CTA: {activeJob.content.cta}
                </div>
              )}
            </div>
          )}

          {/* Default info when no job running */}
          {!activeJob && !runMutation.isPending && (
            <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>↑</div>
              <div style={{ fontSize: 13, color: "var(--text-faint)" }}>
                Enter a company domain above to run the full AI pipeline
              </div>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 6 }}>
                ESG ingestion → scoring → compliance → content → dispatch
              </div>
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}
