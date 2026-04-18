import { motion, AnimatePresence } from "framer-motion";
import type { ReactNode } from "react";

// ── Pill ──────────────────────────────────────────────────────
const PILL_COLOR_MAP: Record<string, string> = {
  mint:"p-mint", blue:"p-blue", amber:"p-amber", red:"p-red", purple:"p-purple", gray:"p-gray",
  green:"p-mint", warning:"p-amber", error:"p-red", info:"p-blue",
  raw:"p-gray", qualified:"p-blue", engaged:"p-mint", demo_scheduled:"p-mint",
  proposal_sent:"p-amber", converted:"p-mint", churned:"p-red",
  active:"p-mint", draft:"p-gray", paused:"p-amber", completed:"p-blue",
  idle:"p-mint", running:"p-blue", waiting:"p-amber", scheduled:"p-gray", failed:"p-red",
};

export function Pill({ label, color = "gray" }: { label: string; color?: string }) {
  const cls = PILL_COLOR_MAP[color] || PILL_COLOR_MAP[label.toLowerCase()] || "p-gray";
  return <span className={`pill ${cls}`}>{label}</span>;
}

export function StatusPill({ status }: { status: string }) {
  const labels: Record<string, string> = {
    raw:"Raw", qualified:"Qualified", engaged:"Engaged", demo_scheduled:"Demo set",
    proposal_sent:"Proposal", converted:"Converted", churned:"Churned",
    active:"Active", draft:"Draft", idle:"Idle", running:"Running",
    waiting:"Waiting", scheduled:"Scheduled", failed:"Failed",
  };
  return <Pill label={labels[status] || status} color={status} />;
}

// ── Avatar ────────────────────────────────────────────────────
export function Av({ initials, bg, color, size = 30 }: { initials: string; bg: string; color: string; size?: number }) {
  return (
    <div className="av" style={{ background: bg, color, width: size, height: size, fontSize: size * 0.34 }}>
      {initials}
    </div>
  );
}

const AV_COLORS = [
  { bg:"#EAF3DE",color:"#27500A" }, { bg:"#E6F1FB",color:"#0C447C" },
  { bg:"#E1F5EE",color:"#085041" }, { bg:"#FAEEDA",color:"#633806" },
  { bg:"#EEEDFE",color:"#3C3489" }, { bg:"#FCEBEB",color:"#791F1F" },
];
export function CompanyAv({ name, size = 30 }: { name: string; size?: number }) {
  const idx = name.charCodeAt(0) % AV_COLORS.length;
  const { bg, color } = AV_COLORS[idx];
  return <Av initials={name.slice(0, 2).toUpperCase()} bg={bg} color={color} size={size} />;
}

// ── Meter ─────────────────────────────────────────────────────
export function Meter({ label, value, pct, color }: { label: string; value: string; pct: number; color: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4, fontSize:12 }}>
        <span style={{ color:"var(--muted)" }}>{label}</span>
        <span style={{ color, fontWeight:600 }}>{value}</span>
      </div>
      <div className="meter-track">
        <motion.div className="meter-fill" style={{ background: color }}
          initial={{ width: 0 }} animate={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }} />
      </div>
    </div>
  );
}

// ── Score bar ─────────────────────────────────────────────────
export function ScoreBar({ score }: { score: number }) {
  const color = score >= 60 ? "var(--mint)" : score >= 40 ? "var(--amber)" : "var(--red)";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <div style={{ flex:1 }}>
        <div className="meter-track">
          <div className="meter-fill" style={{ width:`${score}%`, background:color }} />
        </div>
      </div>
      <span style={{ fontSize:12, fontWeight:700, color, minWidth:28 }}>{score}</span>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────
export function Sk({ h = 16, w = "100%", mb = 0 }: { h?: number; w?: string | number; mb?: number }) {
  return <div className="skeleton" style={{ height: h, width: w, marginBottom: mb }} />;
}
export function CardSk() {
  return <div className="card" style={{ display:"flex", flexDirection:"column", gap:10 }}>
    <Sk h={12} w="55%" /><Sk h={28} w="40%" /><Sk h={10} w="75%" />
  </div>;
}

// ── Stat card ─────────────────────────────────────────────────
export function StatCard({ label, value, delta, positive = true, glow = false }:
  { label: string; value: string; delta: string; positive?: boolean; glow?: boolean }) {
  return (
    <motion.div className="card" initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }}
      style={{ boxShadow: glow ? "var(--glow-mint)" : "none" }}>
      <div style={{ fontSize:10, color:"var(--faint)", marginBottom:8, textTransform:"uppercase", letterSpacing:"0.5px", fontWeight:600 }}>{label}</div>
      <div style={{ fontFamily:"var(--font-h)", fontSize:26, fontWeight:700, color:"var(--text)", lineHeight:1 }}>{value}</div>
      <div style={{ fontSize:11, marginTop:8, color: positive ? "var(--mint)" : "var(--red)", fontWeight:500 }}>
        {positive ? "↑" : "↓"} {delta}
      </div>
    </motion.div>
  );
}

// ── Page wrapper ──────────────────────────────────────────────
export function Page({ children, title, action }: { children: ReactNode; title: string; action?: ReactNode }) {
  return (
    <motion.div initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.22 }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
        <h1 style={{ fontFamily:"var(--font-h)", fontSize:18, fontWeight:700, color:"var(--text)" }}>{title}</h1>
        {action}
      </div>
      {children}
    </motion.div>
  );
}

// ── Modal ─────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, maxWidth = 520 }:
  { open: boolean; onClose: () => void; title: string; children: ReactNode; maxWidth?: number }) {
  if (!open) return null;
  return (
    <div className="modal-bg" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <motion.div className="modal-box" style={{ maxWidth }}
        initial={{ opacity:0, scale:0.95, y:18 }} animate={{ opacity:1, scale:1, y:0 }}
        exit={{ opacity:0, scale:0.95 }} transition={{ duration:0.18 }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
          <h2 style={{ fontFamily:"var(--font-h)", fontSize:15, fontWeight:600 }}>{title}</h2>
          <button className="btn btn-ghost" style={{ padding:"3px 10px", fontSize:18, lineHeight:1 }} onClick={onClose}>×</button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────
export function Empty({ msg }: { msg: string }) {
  return <div style={{ textAlign:"center", padding:"48px 24px", color:"var(--faint)", fontSize:13 }}>{msg}</div>;
}

// ── Gap badge ─────────────────────────────────────────────────
export function GapBadge({ label, severity }: { label: string; severity: string }) {
  const c = severity === "critical" ? "red" : severity === "high" ? "amber" : "blue";
  return <Pill label={label} color={c} />;
}

// ── Confidence bar ────────────────────────────────────────────
export function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "var(--mint)" : pct >= 55 ? "var(--amber)" : "var(--red)";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <div style={{ flex:1, height:4, background:"rgba(255,255,255,0.07)", borderRadius:99 }}>
        <motion.div style={{ height:4, borderRadius:99, background:color }}
          animate={{ width:`${pct}%` }} transition={{ duration:0.5 }} />
      </div>
      <span style={{ fontSize:11, fontWeight:700, color, minWidth:30 }}>{pct}%</span>
    </div>
  );
}
