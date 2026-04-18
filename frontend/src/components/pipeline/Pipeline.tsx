// Pipeline.tsx
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { apiService } from "../../services/api";
import { Page, Skeleton } from "../ui";
import toast from "react-hot-toast";

export default function Pipeline() {
  const { data: stages = [], isLoading } = useQuery({ queryKey: ["pipeline"], queryFn: apiService.getPipeline });
  const COLORS: Record<string, string> = { qualified:"var(--accent-blue)", engaged:"var(--accent-mint)", demo_scheduled:"var(--accent-mint)", proposal_sent:"var(--accent-amber)", converted:"var(--accent-mint)" };
  const TAG_COLORS: Record<string, string> = { green:"var(--accent-mint)", amber:"var(--accent-amber)", blue:"var(--accent-blue)", red:"var(--accent-red)" };

  return (
    <Page title="Revenue pipeline">
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        {[{label:"Total potential ARR",value:"€5.4M",color:"var(--text-primary)"},{label:"At proposal",value:"€1.4M",color:"var(--accent-blue)"},{label:"Closed this quarter",value:"€480K",color:"var(--accent-mint)"}].map((s,i) => (
          <div key={i} className="card-sm" style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontFamily: "var(--font-head)", fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 10, color: "var(--text-faint)", marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {isLoading ? <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 8 }}>{[0,1,2,3,4].map(i=><Skeleton key={i} h={180}/>)}</div> : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,minmax(0,1fr))", gap: 8 }}>
          {stages.map((stage: any) => (
            <div key={stage.id}
              onDragOver={e => e.preventDefault()}
              onDrop={() => toast.success(`Moved to ${stage.title}`)}
              style={{ background: "var(--bg-card2)", border: "0.5px solid var(--border)", borderRadius: "1.1rem", padding: 9, minHeight: 160 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: COLORS[stage.id] || "var(--text-faint)" }} />
                  <span style={{ fontSize: 10, fontWeight: 600, color: COLORS[stage.id] || "var(--text-faint)", textTransform: "uppercase", letterSpacing: "0.4px" }}>{stage.title}</span>
                </div>
                <span style={{ fontSize: 9, padding: "1px 6px", background: "rgba(255,255,255,0.05)", color: "var(--text-faint)", borderRadius: 99 }}>{stage.count}</span>
              </div>
              {stage.cards.map((card: any) => (
                <motion.div key={card.id} draggable whileHover={{ scale: 1.01 }}
                  style={{ background: "var(--bg-page)", border: "0.5px solid var(--border)", borderRadius: 9, padding: "8px 10px", marginBottom: 6, cursor: "grab" }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-primary)", marginBottom: 2 }}>{card.name}</div>
                  <div style={{ fontSize: 10, color: "var(--text-faint)", marginBottom: 5 }}>{card.sub}</div>
                  <span style={{ fontSize: 10, fontWeight: 600, padding: "1px 7px", borderRadius: 99, background: `${TAG_COLORS[card.tagColor]}18`, color: TAG_COLORS[card.tagColor] }}>{card.tag}</span>
                </motion.div>
              ))}
            </div>
          ))}
        </div>
      )}
      <div style={{ marginTop: 10, fontSize: 10, color: "var(--text-faint)", textAlign: "center" }}>Drag cards to update pipeline stage</div>
    </Page>
  );
}
