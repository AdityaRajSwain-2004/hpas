import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, AlertTriangle, CheckCircle, XCircle, Edit3, ShieldAlert } from "lucide-react";
import { hitlService } from "../../services/api";
import { useAuthStore } from "../../store/auth";
import { Page, Skeleton } from "../ui";
import toast from "react-hot-toast";

// ── Confidence bar ─────────────────────────────────────────────
function ConfBar({ value }: { value: number }) {
  const pct   = Math.round(value * 100);
  const color = pct >= 70 ? "var(--accent-mint)" : pct >= 55 ? "var(--accent-amber)" : "var(--accent-red)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.07)", borderRadius: 99 }}>
        <motion.div style={{ height: 4, borderRadius: 99, background: color }}
          animate={{ width: `${pct}%` }} transition={{ duration: 0.5 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color, minWidth: 30 }}>{pct}%</span>
    </div>
  );
}

// ── P4: Age / Freshness indicator ──────────────────────────────
function AgeIndicator({ ageHours }: { ageHours: number }) {
  if (ageHours <= 48) return null;
  const days  = Math.floor(ageHours / 24);
  const hours = Math.round(ageHours % 24);
  const label = days >= 1 ? `${days}d ${hours}h old` : `${Math.round(ageHours)}h old`;
  const isStale = ageHours > 72;

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 4,
      padding: "3px 8px", borderRadius: 99, marginTop: 5,
      background: isStale ? "rgba(239,159,39,0.12)" : "rgba(92,99,112,0.15)",
      border: `0.5px solid ${isStale ? "rgba(239,159,39,0.4)" : "rgba(92,99,112,0.3)"}`,
    }}>
      <Clock size={11} color={isStale ? "var(--accent-amber)" : "var(--text-faint)"} />
      <span style={{ fontSize: 10, fontWeight: 600, color: isStale ? "var(--accent-amber)" : "var(--text-faint)" }}>
        {label} — verify data
      </span>
    </div>
  );
}

// ── P4: Freshness toast ────────────────────────────────────────
function FreshnessWarningToast({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <div style={{
      background: "rgba(239,159,39,0.12)",
      border: "0.5px solid rgba(239,159,39,0.5)",
      borderRadius: "12px",
      padding: "14px 16px",
      maxWidth: 420,
      boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <AlertTriangle size={16} color="var(--accent-amber)" />
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-amber)" }}>
          Data freshness warning
        </span>
        <button onClick={onClose}
          style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer",
                   color: "var(--text-faint)", fontSize: 16, lineHeight: 1 }}>×</button>
      </div>
      <p style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5, margin: 0 }}>{message}</p>
    </div>
  );
}

const CHANNEL_ICON: Record<string, string> = { email: "✉", linkedin: "in", whatsapp: "WA", slack: "#" };

// ══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════
export default function HITLQueue() {
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const [selected,     setSelected]   = useState<any>(null);
  const [editSubject,  setEditSubject] = useState("");
  const [editBody,     setEditBody]   = useState("");
  const [editMode,     setEditMode]   = useState(false);
  const [dismissed,    setDismissed]  = useState<Set<string>>(new Set());

  const { data: queue = [], isLoading } = useQuery({
    queryKey: ["hitl"],
    queryFn:  hitlService.getQueue,
    refetchInterval: 15_000,
  });

  const reviewMutation = useMutation({
    mutationFn: (vars: { id: string; decision: string; subject?: string; body?: string }) =>
      hitlService.submitReview(vars.id, vars.decision as any, vars.subject, vars.body, user?.name || "reviewer"),

    onSuccess: (data, vars) => {
      // P4: Show freshness warning toast if server returned one
      if (data?.freshness_warning) {
        toast.custom(
          (t) => (
            <FreshnessWarningToast
              message={data.freshness_warning}
              onClose={() => toast.dismiss(t.id)}
            />
          ),
          { duration: 10_000, position: "top-right" }
        );
      }

      const msg = { approve: "✓ Approved & sent", reject: "Rejected", edit: "✓ Edited & approved" }[vars.decision] || "Done";
      toast.success(msg);
      setDismissed(prev => new Set([...prev, vars.id]));
      setSelected(null);
      setEditMode(false);
      qc.invalidateQueries({ queryKey: ["hitl"] });
    },
    onError: () => toast.error("Action failed — try again"),
  });

  const visible = (queue as any[]).filter((q: any) => !dismissed.has(q.id));

  const handleSelect = (item: any) => {
    setSelected(item);
    setEditSubject(item.subject || "");
    setEditBody(item.body || "");
    setEditMode(false);
  };

  const handleAction = (decision: string) =>
    selected && reviewMutation.mutate({
      id: selected.id, decision,
      subject: editSubject, body: editBody,
    });

  // Compute freshness info for selected item
  const selectedAge    = selected?.age_hours ?? 0;
  const selectedStale  = selectedAge > 48;

  return (
    <Page title="Review queue">
      {/* Stats bar */}
      <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
        {[
          { label: "Pending review",  value: visible.length,   color: "var(--accent-amber)" },
          { label: "Reviewed today",  value: dismissed.size,   color: "var(--accent-mint)"  },
          { label: "Confidence gate", value: "75%",            color: "var(--accent-blue)"  },
        ].map(s => (
          <div key={s.label} className="card-sm" style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-head)", fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
        <div className="card-sm" style={{ flex: 2, fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center" }}>
          Messages below 75% confidence are held here for human review.
          Items older than 48h show a <Clock size={11} style={{ display:"inline",margin:"0 3px" }} color="var(--accent-amber)" /> freshness warning.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 14, alignItems: "start" }}>

        {/* ── LEFT: Queue list ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {isLoading
            ? [0,1,2].map(i => <Skeleton key={i} h={110} />)
            : visible.length === 0
              ? (
                <div className="card" style={{ textAlign: "center", padding: 32, color: "var(--text-faint)", fontSize: 12 }}>
                  All items reviewed ✓
                </div>
              )
              : visible.map((item: any) => {
                  const ageHours = item.age_hours ?? 0;
                  const isStale  = ageHours > 48;
                  const isActive = selected?.id === item.id;

                  return (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      onClick={() => handleSelect(item)}
                      style={{
                        background: "var(--bg-card)",
                        border: `0.5px solid ${
                          isActive
                            ? "rgba(115,207,168,0.4)"
                            : isStale
                              ? "rgba(239,159,39,0.2)"
                              : "var(--border)"
                        }`,
                        borderRadius: "1rem",
                        padding: "12px 14px",
                        cursor: "pointer",
                        boxShadow: isActive ? "var(--glow-mint)" : isStale ? "0 0 12px -4px rgba(239,159,39,0.15)" : "none",
                        transition: "all 0.15s",
                      }}
                    >
                      {/* Header row */}
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                          {item.company_name || item.company}
                        </div>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 99,
                                       background: "rgba(255,255,255,0.05)", color: "var(--text-faint)" }}>
                          {CHANNEL_ICON[item.channel] || item.channel}
                        </span>
                      </div>

                      {/* Meta */}
                      <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 7 }}>
                        {item.persona} · {item.esg_theme} · Tier {item.tier}
                      </div>

                      {/* Confidence bar */}
                      <ConfBar value={item.confidence || 0.6} />

                      {/* P4: Age indicator — shown if > 48h old */}
                      <AgeIndicator ageHours={ageHours} />

                      {/* Competitor tag if present */}
                      {item.tags?.find((t: any) => t.label?.startsWith("Competitor:")) && (
                        <div style={{ marginTop: 5, display: "flex", alignItems: "center", gap: 4 }}>
                          <ShieldAlert size={11} color="var(--accent-purple, #8B7FDD)" />
                          <span style={{ fontSize: 10, color: "var(--accent-purple, #8B7FDD)", fontWeight: 600 }}>
                            {item.tags.find((t:any) => t.label?.startsWith("Competitor:")).label}
                          </span>
                        </div>
                      )}
                    </motion.div>
                  );
                })
          }
        </div>

        {/* ── RIGHT: Detail pane ── */}
        <AnimatePresence mode="wait">
          {selected ? (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="card"
            >
              {/* Company header */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <div style={{ fontFamily: "var(--font-head)", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                    {selected.company_name || selected.company}
                  </div>
                  {selectedStale && (
                    <div style={{
                      display: "flex", alignItems: "center", gap: 5,
                      padding: "4px 10px", borderRadius: 99,
                      background: "rgba(239,159,39,0.1)", border: "0.5px solid rgba(239,159,39,0.4)",
                    }}>
                      <Clock size={12} color="var(--accent-amber)" />
                      <span style={{ fontSize: 10, fontWeight: 700, color: "var(--accent-amber)" }}>
                        {Math.floor(selectedAge / 24)}d {Math.round(selectedAge % 24)}h old — verify ESG data
                      </span>
                    </div>
                  )}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 4 }}>
                  {selected.channel} · {selected.persona} · {selected.esg_theme} · Tier {selected.tier}
                </div>
              </div>

              {/* Confidence */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 5 }}>AI confidence</div>
                <ConfBar value={selected.confidence || 0.6} />
              </div>

              {/* P4: Freshness warning panel (always visible in detail if stale) */}
              {selectedStale && (
                <div style={{
                  padding: "10px 12px", borderRadius: "0.75rem", marginBottom: 12,
                  background: "rgba(239,159,39,0.07)", border: "0.5px solid rgba(239,159,39,0.3)",
                  display: "flex", alignItems: "flex-start", gap: 8,
                }}>
                  <AlertTriangle size={14} color="var(--accent-amber)" style={{ marginTop: 2, flexShrink: 0 }} />
                  <div style={{ fontSize: 11, color: "var(--accent-amber)", lineHeight: 1.5 }}>
                    <strong>Stale ESG data ({Math.floor(selectedAge / 24)}d {Math.round(selectedAge % 24)}h old)</strong>
                    <br />
                    Key facts may have changed since this message was generated.
                    Verify: SBTi status, sustainability report publication, recent ESG announcements
                    before approving.
                  </div>
                </div>
              )}

              {/* Flag reason */}
              <div style={{ padding: "10px 12px", borderRadius: "0.75rem", marginBottom: 12,
                            background: "rgba(239,159,39,0.07)", border: "0.5px solid rgba(239,159,39,0.2)",
                            fontSize: 12, color: "var(--accent-amber)", lineHeight: 1.5 }}>
                <strong>Why flagged: </strong>{selected.flag_reason}
              </div>

              {/* Tags */}
              {(selected.tags || []).length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
                  {selected.tags.map((t: any, i: number) => (
                    <span key={i} className={`pill pill-${t.color || "amber"}`}>{t.label}</span>
                  ))}
                </div>
              )}

              <div style={{ height: 0.5, background: "var(--border)", marginBottom: 12 }} />

              {/* Message editor toggle */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)" }}>Message content</div>
                <button className="btn-ghost" style={{ fontSize: 11, padding: "4px 10px" }}
                  onClick={() => setEditMode(!editMode)}>
                  <Edit3 size={12} style={{ marginRight: 4 }} />
                  {editMode ? "Preview" : "Edit"}
                </button>
              </div>

              {editMode ? (
                <>
                  <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 4 }}>Subject</div>
                  <input className="field" value={editSubject} onChange={e => setEditSubject(e.target.value)} style={{ marginBottom: 10 }} />
                  <div style={{ fontSize: 11, color: "var(--text-faint)", marginBottom: 4 }}>Body</div>
                  <textarea className="field" rows={8} value={editBody} onChange={e => setEditBody(e.target.value)}
                    style={{ width: "100%", resize: "vertical", lineHeight: 1.6 }} />
                </>
              ) : (
                <div style={{ padding: "14px", background: "rgba(255,255,255,0.03)", border: "0.5px solid var(--border)",
                              borderRadius: "0.75rem", fontSize: 12, lineHeight: 1.7, color: "var(--text-muted)" }}>
                  {selected.subject && (
                    <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 8, fontSize: 12 }}>
                      {selected.subject}
                    </div>
                  )}
                  {selected.body}
                </div>
              )}

              {/* Action buttons */}
              <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
                <button className="btn-approve" disabled={reviewMutation.isPending}
                  onClick={() => handleAction(editMode ? "edit" : "approve")}
                  style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <CheckCircle size={14} />
                  {reviewMutation.isPending ? "Processing…" : editMode ? "Save & approve" : "Approve & send"}
                </button>
                {!editMode && (
                  <button className="btn-edit" onClick={() => setEditMode(true)}
                    style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Edit3 size={14} /> Edit message
                  </button>
                )}
                <button className="btn-reject" disabled={reviewMutation.isPending}
                  onClick={() => handleAction("reject")}
                  style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <XCircle size={14} /> Reject
                </button>
              </div>

            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card"
              style={{ textAlign: "center", padding: "60px 40px" }}
            >
              <div style={{ fontSize: 32, marginBottom: 12 }}>←</div>
              <div style={{ fontSize: 13, color: "var(--text-faint)" }}>
                Select an item from the queue to review it
              </div>
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 6 }}>
                Items with <Clock size={11} style={{ display:"inline",margin:"0 2px" }} color="var(--accent-amber)" />
                have ESG data older than 48h — verify before approving
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Page>
  );
}
