import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Leaf, LayoutDashboard, Users, GitBranch, Activity,
  ClipboardCheck, Bot, Megaphone, LogOut, Bell, Menu, X,
} from "lucide-react";
import { useAuthStore } from "../../store/auth";
import { USE_MOCK_DATA } from "../../config";

const NAV = [
  { group: "Overview",  items: [{ to: "/dashboard",  label: "Dashboard",    icon: LayoutDashboard }] },
  { group: "Prospects", items: [
    { to: "/prospects", label: "All prospects", icon: Users       },
    { to: "/pipeline",  label: "Pipeline",      icon: GitBranch   },
  ]},
  { group: "AI Engine", items: [
    { to: "/workflow",  label: "Live workflow",  icon: Activity    },
    { to: "/hitl",      label: "Review queue",  icon: ClipboardCheck, badge: true },
    { to: "/agents",    label: "Agents",         icon: Bot         },
  ]},
  { group: "Outreach",  items: [{ to: "/campaigns", label: "Campaigns", icon: Megaphone }] },
];

export default function AppLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [open, setOpen] = useState(true);

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-page)" }}>

      <AnimatePresence initial={false}>
        {open && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 200, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            style={{
              width: 200, minWidth: 200, flexShrink: 0, overflow: "hidden",
              background: "var(--bg-card)", borderRight: "0.5px solid var(--border)",
              display: "flex", flexDirection: "column",
            }}
          >
            {/* Logo */}
            <div style={{ padding: "15px 13px 13px", borderBottom: "0.5px solid var(--border)", display: "flex", alignItems: "center", gap: 9 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: "rgba(115,207,168,0.12)", border: "0.5px solid rgba(115,207,168,0.25)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Leaf size={14} color="var(--accent-mint)" />
              </div>
              <div>
                <div style={{ fontFamily: "var(--font-head)", fontSize: 12, fontWeight: 700, color: "var(--accent-mint)" }}>resustain™ AI</div>
                <div style={{ fontSize: 9, color: "var(--text-faint)", marginTop: 1 }}>{USE_MOCK_DATA ? "Demo mode" : "Enterprise"}</div>
              </div>
            </div>

            {/* Nav */}
            <nav style={{ padding: "8px 6px", flex: 1, overflowY: "auto" }}>
              {NAV.map(group => (
                <div key={group.group} style={{ marginBottom: 4 }}>
                  <div style={{ fontSize: 9, fontWeight: 700, color: "var(--text-faint)", padding: "7px 8px 3px", textTransform: "uppercase", letterSpacing: "0.6px" }}>
                    {group.group}
                  </div>
                  {(group.items as any[]).map((item: any) => (
                    <NavLink key={item.to} to={item.to} style={{ textDecoration: "none" }}>
                      {({ isActive }) => (
                        <div style={{
                          display: "flex", alignItems: "center", gap: 7,
                          padding: "6px 8px", borderRadius: 7, marginBottom: 1,
                          background: isActive ? "rgba(115,207,168,0.1)" : "transparent",
                          color: isActive ? "var(--accent-mint)" : "var(--text-faint)",
                          fontWeight: isActive ? 500 : 400, fontSize: 12,
                          cursor: "pointer",
                          border: `0.5px solid ${isActive ? "rgba(115,207,168,0.2)" : "transparent"}`,
                          boxShadow: isActive ? "0 0 10px -3px rgba(115,207,168,0.25)" : "none",
                        }}>
                          <item.icon size={13} />
                          <span style={{ flex: 1 }}>{item.label}</span>
                          {item.badge && (
                            <span style={{ fontSize: 9, padding: "1px 5px", background: "rgba(226,75,74,0.15)", color: "var(--accent-red)", borderRadius: 99, fontWeight: 700 }}>
                              •
                            </span>
                          )}
                        </div>
                      )}
                    </NavLink>
                  ))}
                </div>
              ))}
            </nav>

            {/* User */}
            <div style={{ padding: "10px 12px", borderTop: "0.5px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 26, height: 26, borderRadius: "50%", background: "rgba(55,138,221,0.15)", color: "var(--accent-blue)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, fontFamily: "var(--font-head)", flexShrink: 0 }}>
                {user?.name?.slice(0, 2) || "U"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.name}</div>
                <div style={{ fontSize: 9, color: "var(--text-faint)" }}>{user?.role}</div>
              </div>
              <button onClick={async () => { await logout(); navigate("/login"); }}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-faint)", display: "flex", padding: 3 }}>
                <LogOut size={12} />
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* Topbar */}
        <header style={{
          height: 46, flexShrink: 0,
          background: "rgba(22,25,30,0.85)", backdropFilter: "blur(20px)",
          borderBottom: "0.5px solid var(--border)",
          display: "flex", alignItems: "center", padding: "0 16px", gap: 10,
          position: "sticky", top: 0, zIndex: 10,
        }}>
          <button onClick={() => setOpen(s => !s)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-faint)", display: "flex", padding: 4 }}>
            {open ? <X size={14} /> : <Menu size={14} />}
          </button>
          <div style={{ flex: 1 }} />
          {USE_MOCK_DATA && (
            <div style={{ fontSize: 10, padding: "2px 9px", background: "rgba(239,159,39,0.1)", color: "var(--accent-amber)", border: "0.5px solid rgba(239,159,39,0.25)", borderRadius: 99, fontWeight: 600 }}>
              Demo mode
            </div>
          )}
          <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-faint)", display: "flex", padding: 5, position: "relative" }}>
            <Bell size={14} />
            <span style={{ position: "absolute", top: 4, right: 4, width: 5, height: 5, background: "var(--accent-red)", borderRadius: "50%" }} />
          </button>
        </header>

        <main style={{ flex: 1, overflowY: "auto", padding: "22px 26px" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
