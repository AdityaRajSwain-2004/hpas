import axios from "axios";
import type { AxiosInstance } from "axios";
import { USE_MOCK_DATA, CONFIG } from "../config";
import { MOCK_DASHBOARD, MOCK_PROSPECTS, MOCK_PIPELINE, MOCK_WORKFLOW, MOCK_HITL, MOCK_CAMPAIGNS } from "../mock/data";

const delay = (ms = CONFIG.MOCK_DELAY_MS) => new Promise(r => setTimeout(r, ms));

let _client: AxiosInstance | null = null;
function getClient(): AxiosInstance {
  if (!_client) {
    _client = axios.create({ baseURL: CONFIG.API_BASE_URL, timeout: CONFIG.API_TIMEOUT_MS, headers: { "Content-Type": "application/json" } });
    _client.interceptors.request.use(cfg => { const t = localStorage.getItem(CONFIG.JWT_STORAGE_KEY); if (t) cfg.headers.Authorization = `Bearer ${t}`; return cfg; });
    _client.interceptors.response.use(r => r, err => { if (err.response?.status === 401) { localStorage.removeItem(CONFIG.JWT_STORAGE_KEY); window.location.href = "/login"; } return Promise.reject(err); });
  }
  return _client;
}

export const authService = {
  async login(email: string, password: string): Promise<{ user: any; token: string }> {
    if (USE_MOCK_DATA) { await delay(700); if (email === "demo@treeni.com" && password === "demo123") { const user = { id: "u1", name: "Arjun Mehta", email, role: "admin", tenantId: "treeni", avatar: "AM" }; const token = "mock-jwt"; localStorage.setItem(CONFIG.JWT_STORAGE_KEY, token); return { user, token }; } throw new Error("Invalid credentials"); }
    const { data } = await getClient().post("/api/auth/login", { email, password }); localStorage.setItem(CONFIG.JWT_STORAGE_KEY, data.token); return data;
  },
  async logout() { localStorage.removeItem(CONFIG.JWT_STORAGE_KEY); if (!USE_MOCK_DATA) await getClient().post("/api/auth/logout").catch(() => {}); },
  async getCurrentUser(): Promise<any> { const token = localStorage.getItem(CONFIG.JWT_STORAGE_KEY); if (!token) return null; if (USE_MOCK_DATA) return { id: "u1", name: "Arjun Mehta", email: "demo@treeni.com", role: "admin", avatar: "AM" }; const { data } = await getClient().get("/api/auth/me"); return data; },
};

export const analyticsService = {
  async getDashboard() { if (USE_MOCK_DATA) { await delay(); return MOCK_DASHBOARD; } const { data } = await getClient().get("/api/analytics/dashboard"); return data; },
  async getPipeline() { if (USE_MOCK_DATA) { await delay(300); return { stages: { raw: 12, qualified: 8, engaged: 6, demo_scheduled: 5, proposal_sent: 5, converted: 3, churned: 2 } }; } const { data } = await getClient().get("/api/analytics/pipeline"); return data; },
};

export const prospectService = {
  async getAll(filters?: Record<string, any>) { if (USE_MOCK_DATA) { await delay(); return { total: MOCK_PROSPECTS.length, data: MOCK_PROSPECTS }; } const { data } = await getClient().get("/api/prospects", { params: filters }); return data; },
  async getById(id: string) { if (USE_MOCK_DATA) { await delay(300); return MOCK_PROSPECTS.find(p => p.id === id) || MOCK_PROSPECTS[0]; } const { data } = await getClient().get(`/api/prospects/${id}`); return data; },
  async run(domain: string, persona = "cso", channel = "email") { if (USE_MOCK_DATA) { await delay(800); return { job_id: `mock-${Date.now()}`, domain, status: "queued" }; } const { data } = await getClient().post("/api/prospects/run", { domain, persona, channel }); return data; },
  async runSync(domain: string, persona = "cso", channel = "email") {
    if (USE_MOCK_DATA) { await delay(2500); return { success: true, prospect_id: "mock-id", domain, company_name: domain.split(".")[0].replace(/-/g," ").replace(/\b\w/g, (c: string) => c.toUpperCase()), esg_score: Math.floor(Math.random()*50)+30, prospect_tier: 2, confidence: 0.78, quality_score: 0.82, requires_hitl: false, dispatched: true, latency_ms: 10842, compliance_gaps: [{ framework: "CSRD", severity: "critical", label: "Scope 1 emissions not reported" }], content: { subject: "ESG compliance insight for your operations", body: "Based on your current sustainability disclosure profile, there are several areas where resustain\u2122 can create immediate value \u2014 particularly around your Scope 3 emissions tracking and supply chain audit coverage.\n\nResustain\u2122 SCSM helps companies like yours close supplier ESG gaps in under 90 days.", cta: "Would a 20-minute walkthrough make sense this week?", variant: "A" }, steps: [{ num: 1, state: "done", name: "ESG data ingestion", detail: "3 sources returned data", time: "2.8s" },{ num: 2, state: "done", name: "Firmographic profiling", detail: "LLM inference complete", time: "0.7s" },{ num: 3, state: "done", name: "ESG scoring", detail: "Score computed", time: "0.01s" },{ num: 4, state: "done", name: "Compliance analysis", detail: "CSRD critical gap detected", time: "0.01s" },{ num: 5, state: "done", name: "Contact sourcing", detail: "Apollo.io · ZeroBounce verified", time: "1.9s" },{ num: 6, state: "done", name: "Vector embedding", detail: "Stored in pgvector", time: "0.8s" },{ num: 7, state: "done", name: "Content generation", detail: "Quality: 0.82 · auto-approved", time: "6.1s" },{ num: 8, state: "done", name: "Dispatch", detail: "Sent via email", time: "1.2s" }] }; }
    const { data } = await getClient().post("/api/prospects/run/sync", { domain, persona, channel }); return data;
  },
  async runBulk(domains: string[], persona = "cso", channel = "email") { if (USE_MOCK_DATA) { await delay(500); return { queued: domains.length }; } const { data } = await getClient().post("/api/prospects/bulk", { domains, persona, channel }); return data; },
  async getJob(jobId: string) { if (USE_MOCK_DATA) { await delay(300); return { job_id: jobId, status: "complete" }; } const { data } = await getClient().get(`/api/jobs/${jobId}`); return data; },
};

export const pipelineService = {
  async getStages() {
    if (USE_MOCK_DATA) { await delay(); return MOCK_PIPELINE; }
    const { data } = await getClient().get("/api/analytics/pipeline");
    return [{ id:"qualified", title:"Qualified", count:data.stages.qualified||0, cards:[] },{ id:"engaged", title:"Engaged", count:data.stages.engaged||0, cards:[] },{ id:"demo_scheduled", title:"Demo set", count:data.stages.demo_scheduled||0, cards:[] },{ id:"proposal_sent", title:"Proposal", count:data.stages.proposal_sent||0, cards:[] },{ id:"converted", title:"Converted", count:data.stages.converted||0, cards:[] }];
  },
};

export const workflowService = {
  async getActive() { if (USE_MOCK_DATA) { await delay(300); return MOCK_WORKFLOW; } const { data } = await getClient().get("/api/workflows/active"); return data; },
};

export const hitlService = {
  async getQueue() { if (USE_MOCK_DATA) { await delay(); return MOCK_HITL; } const { data } = await getClient().get("/api/hitl"); return data.items || []; },
  async submitReview(id: string, decision: "approve"|"reject"|"edit", subject?: string, body?: string, reviewer = "reviewer") {
    if (USE_MOCK_DATA) {
      await delay(600);
      const item = MOCK_HITL.find((h: any) => h.id === id);
      const age = (item as any)?.age_hours ?? 0;
      return { success: true, freshness_warning: age > 48 && decision !== "reject" ? `ESG data is ${age}h old. Verify before sending: SBTi status, sustainability report, recent announcements.` : null };
    }
    const { data } = await getClient().post(`/api/hitl/${id}/review`, { decision, edited_subject: subject, edited_body: body, reviewer });
    return data;
  },
};

export const campaignService = {
  async getAll() { if (USE_MOCK_DATA) { await delay(); return MOCK_CAMPAIGNS; } const { data } = await getClient().get("/api/campaigns"); return data.data || []; },
  async create(payload: any) { if (USE_MOCK_DATA) { await delay(700); return { id: `c-${Date.now()}`, status: "draft", ...payload }; } const { data } = await getClient().post("/api/campaigns", payload); return data; },
  async launch(id: string) { if (USE_MOCK_DATA) { await delay(500); return { status: "active" }; } const { data } = await getClient().post(`/api/campaigns/${id}/launch`); return data; },
};


export const suppressionService = {
  async getAll() { if (USE_MOCK_DATA) { await delay(300); return { domains: [] }; } const { data } = await getClient().get("/api/suppression"); return data; },
  async add(domain: string, reason = "manual", notes = "", added_by = "admin") { if (USE_MOCK_DATA) { await delay(400); return { domain, reason, suppressed: true }; } const { data } = await getClient().post("/api/suppression", { domain, reason, notes, added_by }); return data; },
  async remove(domain: string) { if (USE_MOCK_DATA) { await delay(400); return { domain, suppressed: false }; } const { data } = await getClient().delete(`/api/suppression/${domain}`); return data; },
  async check(domain: string) { if (USE_MOCK_DATA) { await delay(200); return { domain, suppressed: false }; } const { data } = await getClient().get(`/api/suppression/${domain}`); return data; },
};

export const feedbackService = {
  async sendSignal(signal: Record<string, any>) { if (USE_MOCK_DATA) { await delay(200); return { received: true }; } const { data } = await getClient().post("/api/feedback/webhook", signal); return data; },
};
