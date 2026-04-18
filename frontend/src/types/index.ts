export type LeadStatus = "raw"|"qualified"|"engaged"|"demo_scheduled"|"proposal_sent"|"converted"|"churned";
export type Channel = "email"|"linkedin"|"whatsapp"|"slack";
export type CampaignStatus = "draft"|"active"|"paused"|"completed";

export interface Prospect {
  id: string;
  domain: string;
  company_name: string;
  industry: string;
  hq_country: string;
  employee_count: number;
  revenue_band: string;
  esg_score_composite: number;
  esg_score_env: number;
  esg_score_social: number;
  esg_score_governance: number;
  decarb_urgency: number;
  supply_chain_risk: number;
  icp_fit_score: number;
  prospect_tier: 1|2|3;
  lead_status: LeadStatus;
  data_quality_score: number;
  contact_title: string;
  contact_source: string;
  contact_verified: boolean;
  compliance_gaps: ComplianceGap[];
  raw_esg_data: Record<string,any>;
  created_at: string;
  updated_at: string;
}

export interface ComplianceGap {
  framework: string;
  severity: "critical"|"high"|"medium"|"low";
  label: string;
  deadline_days: number|null;
  penalty_usd: number;
  module: string;
}

export interface HITLItem {
  id: string;
  prospect_id: string;
  company_name: string;
  domain: string;
  industry: string;
  prospect_tier: number;
  channel: string;
  persona: string;
  esg_theme: string;
  subject: string;
  body: string;
  flag_reason: string;
  confidence: number;
  tier: number;
  tags: Array<{label:string;color:string}>;
  status: "pending"|"approved"|"rejected"|"edited";
  created_at: string;
  age_hours?: number;                // P4: hours since created — annotated by API
  esg_updated_at?: string;           // P4: when ESG data was last fetched
}

export interface SuppressionDomain {
  id: string;
  domain: string;
  reason: "existing_customer"|"active_opportunity"|"manual"|"hard_bounce"|"spam_report";
  notes?: string;
  added_by: string;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  description?: string;
  channels: Channel[];
  esg_theme?: string;
  persona: string;
  status: CampaignStatus;
  ab_test_enabled: boolean;
  total_sent: number;
  total_opened: number;
  total_replied: number;
  total_demos: number;
  created_at: string;
}

export interface DashboardData {
  kpis: {
    total_prospects: number;
    demos_booked: number;
    converted: number;
    engaged: number;
    avg_esg_score: number;
    tier_breakdown: {tier1:number;tier2:number;tier3:number};
  };
  outreach: {
    sent_30d: number;
    open_rate: number;
    click_rate: number;
    reply_rate: number;
    avg_quality: number;
    avg_confidence: number;
  };
  esg_themes: Array<{esg_theme:string;count:number;avg_reward:number}>;
  hitl_pending: number;
}

export interface PipelineData {
  stages: Record<LeadStatus, number>;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin"|"reviewer"|"viewer";
  avatar: string;
}
