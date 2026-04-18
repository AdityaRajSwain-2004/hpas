import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Leaf, Mail, Lock, Eye, EyeOff, AlertCircle } from "lucide-react";
import { useAuthStore } from "../../store/auth";
import { USE_MOCK_DATA } from "../../config";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [email,    setEmail]    = useState(USE_MOCK_DATA ? "demo@treeni.com" : "");
  const [password, setPassword] = useState(USE_MOCK_DATA ? "demo123" : "");
  const [showPw,   setShowPw]   = useState(false);

  useEffect(() => { if (isAuthenticated) navigate("/dashboard"); }, [isAuthenticated, navigate]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await login(email, password);
  };

  return (
    <div style={{
      minHeight: "100vh", background: "var(--bg-page)",
      display: "flex", alignItems: "center", justifyContent: "center", padding: 24,
    }}>
      {/* Grid background */}
      <div style={{
        position: "absolute", inset: 0, opacity: 0.035,
        backgroundImage: "radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)",
        backgroundSize: "28px 28px",
      }} />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        style={{ width: "100%", maxWidth: 400, position: "relative" }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{
            width: 50, height: 50, borderRadius: 14,
            background: "rgba(115,207,168,0.12)",
            border: "0.5px solid rgba(115,207,168,0.25)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 14px",
          }}>
            <Leaf size={22} color="var(--accent-mint)" />
          </div>
          <h1 style={{ fontFamily: "var(--font-head)", fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            resustain™ AI
          </h1>
          <p style={{ fontSize: 12, color: "var(--text-faint)", margin: "4px 0 0" }}>
            Sustainability Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: "rgba(255,255,255,0.03)",
          border: "0.5px solid rgba(255,255,255,0.08)",
          borderRadius: 16, padding: 28,
        }}>
          <h2 style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)", marginBottom: 18 }}>
            Sign in to your workspace
          </h2>

          {USE_MOCK_DATA && (
            <div style={{
              background: "rgba(115,207,168,0.08)", border: "0.5px solid rgba(115,207,168,0.2)",
              borderRadius: 8, padding: "9px 12px", marginBottom: 16,
              fontSize: 11, color: "var(--accent-mint)", lineHeight: 1.5,
            }}>
              <strong>Demo mode — no API needed.</strong> Credentials are pre-filled.
            </div>
          )}

          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{
                display: "flex", alignItems: "center", gap: 7,
                background: "rgba(226,75,74,0.08)", border: "0.5px solid rgba(226,75,74,0.3)",
                borderRadius: 8, padding: "9px 12px", marginBottom: 14,
                fontSize: 12, color: "#f08080",
              }}>
              <AlertCircle size={13} />{error}
            </motion.div>
          )}

          <form onSubmit={submit}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>
                Email address
              </label>
              <div style={{ position: "relative" }}>
                <Mail size={13} color="var(--text-faint)"
                  style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }} />
                <input type="email" value={email} required
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="field" style={{ paddingLeft: 32 }} />
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 11, color: "var(--text-faint)", display: "block", marginBottom: 5 }}>
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={13} color="var(--text-faint)"
                  style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }} />
                <input type={showPw ? "text" : "password"} value={password} required
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="field" style={{ paddingLeft: 32, paddingRight: 36 }} />
                <button type="button" onClick={() => setShowPw(s => !s)}
                  style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer" }}>
                  {showPw ? <EyeOff size={13} color="var(--text-faint)" /> : <Eye size={13} color="var(--text-faint)" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={isLoading}
              className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "10px" }}>
              {isLoading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p style={{ textAlign: "center", fontSize: 10, color: "var(--text-faint)", marginTop: 18 }}>
          © 2025 Treeni Sustainability Solutions · v2.0.0
        </p>
      </motion.div>
    </div>
  );
}
