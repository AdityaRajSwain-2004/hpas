import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { apiService } from "../../services/api";
import { Page, StatCard, SectionHead, Skeleton, Avatar, Pill } from "../ui";
import { CONFIG } from "../../config";

const AREA_DATA = [
  { m: "Aug", prospects: 80, demos: 3 },
  { m: "Sep", prospects: 210, demos: 7 },
  { m: "Oct", prospects: 480, demos: 14 },
  { m: "Nov", prospects: 890, demos: 19 },
  { m: "Dec", prospects: 1420, demos: 24 },
  { m: "Jan", prospects: 1847, demos: 27 },
];

const Tip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "var(--bg-card2)", border: "0.5px solid var(--border)", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      <div style={{ color: "var(--text-faint)", marginBottom: 3 }}>{label}</div>
      {payload.map((p: any) => <div key={p.name} style={{ color: p.color, fontWeight: 600 }}>{p.name}: {p.value}</div>)}
    </div>
  );
};

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: apiService.getDashboard,
    refetchInterval: CONFIG.DASHBOARD_POLL_MS,
  });

  return (
    <Page title="Dashboard" subtitle="Real-time sustainability intelligence">
      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: 10, marginBottom: 18 }}>
        {isLoading ? [0,1,2,3].map(i => <Skeleton key={i} h={90} />) : data?.kpis.map((k: any, i: number) => (
          <StatCard key={i} label={k.label} value={k.value} delta={k.delta} deltaPositive={k.deltaPositive} glow={i===3} />
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
        {/* Area chart */}
        <div className="card">
          <SectionHead>Pipeline growth</SectionHead>
          <ResponsiveContainer width="100%" height={170}>
            <AreaChart data={AREA_DATA} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="gm" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#73cfa8" stopOpacity={0.22} />
                  <stop offset="95%" stopColor="#73cfa8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gb" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#378ADD" stopOpacity={0.22} />
                  <stop offset="95%" stopColor="#378ADD" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="m" tick={{ fontSize: 10, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} />
              <Tooltip content={<Tip />} />
              <Area type="monotone" dataKey="prospects" name="Prospects" stroke="#73cfa8" strokeWidth={2} fill="url(#gm)" />
              <Area type="monotone" dataKey="demos"     name="Demos"     stroke="#378ADD" strokeWidth={2} fill="url(#gb)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* ESG themes pie */}
        <div className="card">
          <SectionHead>Top ESG themes driving replies</SectionHead>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie data={data?.esgThemes || []} cx="50%" cy="50%" innerRadius={38} outerRadius={64} dataKey="pct" strokeWidth={0}>
                  {(data?.esgThemes || []).map((t: any, i: number) => <Cell key={i} fill={t.color} opacity={0.85} />)}
                </Pie>
                <Tooltip content={<Tip />} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {(data?.esgThemes || []).map((t: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 7 }}>
                  <div style={{ width: 7, height: 7, borderRadius: "50%", background: t.color, flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: "var(--text-muted)", flex: 1 }}>{t.label}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: t.color }}>{t.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {/* A/B test */}
        <div className="card">
          <SectionHead>A/B test — current campaign</SectionHead>
          {data?.abTest && (
            <>
              <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                {[data.abTest.variantA, data.abTest.variantB].map((v: any, i: number) => (
                  <div key={i} style={{
                    flex: 1, padding: "10px 12px",
                    background: "rgba(255,255,255,0.03)",
                    border: `0.5px solid ${v.winner ? "rgba(115,207,168,0.35)" : "var(--border)"}`,
                    borderRadius: "0.9rem",
                    boxShadow: v.winner ? "var(--glow-mint)" : "none",
                  }}>
                    <div style={{ fontSize: 10, color: v.winner ? "var(--accent-mint)" : "var(--text-faint)", fontWeight: 600, marginBottom: 5 }}>
                      {v.name} {v.winner && "✓"}
                    </div>
                    <div style={{ fontFamily: "var(--font-head)", fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{v.openRate}</div>
                    <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>{v.sends} sends</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", padding: "7px 10px", background: "rgba(115,207,168,0.06)", borderRadius: 8, border: "0.5px solid rgba(115,207,168,0.12)" }}>
                <strong style={{ color: "var(--accent-mint)" }}>{data.abTest.confidence}</strong> confidence — {data.abTest.conclusion}
              </div>
            </>
          )}
        </div>

        {/* Activity */}
        <div className="card">
          <SectionHead>Recent activity</SectionHead>
          {(data?.recentActivity || []).map((item: any) => (
            <motion.div key={item.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
              style={{ display: "flex", alignItems: "center", gap: 9, padding: "8px 0", borderBottom: "0.5px solid var(--border)" }}>
              <Avatar initials={item.initials} bg={item.avatarBg} color={item.avatarColor} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>{item.company}</div>
                <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.event}</div>
              </div>
              <Pill label={item.status} color={item.statusColor as any} />
            </motion.div>
          ))}
        </div>
      </div>
    </Page>
  );
}
