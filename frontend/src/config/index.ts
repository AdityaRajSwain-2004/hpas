// ═══════════════════════════════════════════════════════
// TREENI AI — CONFIG
// Toggle between demo mode and live API with one line.
// ═══════════════════════════════════════════════════════

export const USE_MOCK_DATA = true; // ← set false to connect real API

export const CONFIG = {
  API_BASE: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  MOCK_DELAY_MS: 500,
  POLL_INTERVAL_MS: 5000,
  APP_NAME: "resustain™ AI",
  APP_SUBTITLE: "Sustainability Intelligence Platform",
};
