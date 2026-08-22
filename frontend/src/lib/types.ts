export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type FindingStatus =
  | "OPEN"
  | "ACKNOWLEDGED"
  | "IN_PROGRESS"
  | "FIXED"
  | "VERIFIED"
  | "DISMISSED";
export type Priority = "P0" | "P1" | "P2" | "P3";
export type ScanStatus =
  | "QUEUED"
  | "CRAWLING"
  | "ANALYZING"
  | "AI_PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";
export type Category =
  | "SECURITY"
  | "PERFORMANCE"
  | "ACCESSIBILITY"
  | "PRIVACY"
  | "SEO"
  | "CONTENT"
  | "UX"
  | "ARCHITECTURE";

export const CATEGORIES: Category[] = [
  "SECURITY",
  "PERFORMANCE",
  "ACCESSIBILITY",
  "PRIVACY",
  "SEO",
  "CONTENT",
  "UX",
  "ARCHITECTURE",
];

export const CATEGORY_LABELS: Record<Category, string> = {
  SECURITY: "Security",
  PERFORMANCE: "Performance",
  ACCESSIBILITY: "Accessibility",
  PRIVACY: "Privacy",
  SEO: "SEO",
  CONTENT: "Content",
  UX: "UX",
  ARCHITECTURE: "Architecture",
};

export const SEVERITIES: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
export const FINDING_STATUSES: FindingStatus[] = [
  "OPEN",
  "ACKNOWLEDGED",
  "IN_PROGRESS",
  "FIXED",
  "VERIFIED",
  "DISMISSED",
];
export const PRIORITIES: Priority[] = ["P0", "P1", "P2", "P3"];
export const RECOMMENDATION_STATUSES = ["OPEN", "IN_PROGRESS", "COMPLETED", "DISMISSED"];
export const WEBSITE_TYPES = [
  "portfolio",
  "ecommerce",
  "blog",
  "saas",
  "corporate",
  "news",
  "other",
];
export const SCAN_STATUSES: ScanStatus[] = [
  "QUEUED",
  "CRAWLING",
  "ANALYZING",
  "AI_PROCESSING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

export const RUNNING_SCAN_STATUSES: ScanStatus[] = [
  "QUEUED",
  "CRAWLING",
  "ANALYZING",
  "AI_PROCESSING",
];

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Website {
  id: number;
  user_id: number;
  name: string;
  url: string;
  normalized_url: string;
  website_type: string;
  industry: string | null;
  target_audience: string | null;
  description: string | null;
  monitoring_enabled: boolean;
  last_scanned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebsiteCreate {
  name: string;
  url: string;
  website_type: string;
  industry?: string | null;
  target_audience?: string | null;
  description?: string | null;
}

export interface Competitor {
  id: number;
  website_id: number;
  name: string;
  url: string;
  normalized_url: string;
  created_at: string;
}

export interface Scan {
  id: number;
  website_id: number;
  status: ScanStatus;
  stage: string;
  progress_percent: number;
  error_message: string | null;
  crawl_depth: number;
  page_limit: number;
  started_at: string | null;
  completed_at: string | null;
  pages_discovered: number;
  pages_analyzed: number;
  overall_score: number | null;
  security_score: number | null;
  performance_score: number | null;
  accessibility_score: number | null;
  privacy_score: number | null;
  seo_score: number | null;
  content_score: number | null;
  ux_score: number | null;
  architecture_score: number | null;
  analyzer_status: Record<string, string> | null;
}

export interface ScanProgress {
  id: number;
  website_id: number;
  status: ScanStatus;
  stage: string;
  progress_percent: number;
  error_message: string | null;
  pages_discovered: number;
  pages_analyzed: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface Finding {
  id: number;
  scan_id: number;
  category: Category;
  rule_id: string;
  title: string;
  description: string | null;
  severity: Severity;
  confidence: number;
  impact: string;
  effort: string;
  status: FindingStatus;
  affected_url: string | null;
  created_at: string;
  evidence: Evidence[];
}

export interface Evidence {
  id: number;
  finding_id: number;
  evidence_type: string;
  source: string | null;
  value: string | null;
  metadata: Record<string, unknown> | null;
  confidence: number;
}

export interface Recommendation {
  id: number;
  scan_id: number;
  title: string;
  description: string | null;
  priority: Priority;
  priority_score: number;
  impact: string;
  effort: string;
  confidence: number;
  category: Category;
  root_cause: string | null;
  implementation_guidance: string | null;
  finding_ids: number[];
  status: string;
  created_at: string;
}

export interface ArchitectureNode {
  id: number;
  node_type: string;
  name: string;
  label: string | null;
  metadata: Record<string, unknown> | null;
}

export interface ArchitectureEdge {
  id: number;
  source_node_id: number;
  target_node_id: number;
  relationship: string;
  metadata: Record<string, unknown> | null;
}

export interface Architecture {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export interface SiteComparison {
  website_id: number | null;
  name: string;
  url: string;
  is_self: boolean;
  is_demo: boolean;
  scores: Record<string, number | null>;
  scan_id: number | null;
  scanned_at: string | null;
}

export interface CompetitiveGap {
  you: number | null;
  competitor: number | null;
  gap: number | null;
  explanation: string | null;
}

export interface Comparison {
  sites: SiteComparison[];
  ai_explanation: string | null;
  gaps: Record<string, CompetitiveGap> | null;
}

export interface ScanComparison {
  id: number;
  website_id: number;
  base_scan_id: number;
  compare_scan_id: number;
  changes: Record<string, unknown> | null;
  summary: string | null;
  created_at: string;
}

export interface UserStats {
  websites_count: number;
  scans_count: number;
  user_id: number;
}

export interface ExecutiveReport {
  website: { name: string; url: string };
  scan: { id: number; status: string; completed_at: string | null };
  overall_score: number | null;
  scores: Record<string, number | null>;
  summary: {
    headline: string | null;
    executive_summary: string | null;
    top_risks: string[];
    biggest_opportunities: string[];
    roadmap: string[];
  };
  top_risks: { title: string; severity: Severity }[];
  top_recommendations: {
    title: string;
    priority: string;
    impact: string;
    effort: string;
    confidence: number;
  }[];
}

export interface DeveloperReport {
  website: { name: string; url: string };
  scan: { id: number; status: string };
  findings_count: number;
  findings: {
    id: number;
    category: string;
    rule_id: string;
    title: string;
    severity: Severity;
    confidence: number;
    impact: string;
    effort: string;
    affected_url: string | null;
    description: string | null;
    evidence: { type: string; source: string | null; value: string | null }[];
  }[];
  technologies: { name: string; category: string; confidence: number }[];
  metrics: { pages_discovered: number; pages_analyzed: number };
}

export interface ApiErrorDetail {
  msg?: string;
  loc?: unknown[];
  type?: string;
}

export interface ApiError {
  status: number;
  detail: string | ApiErrorDetail[];
  raw: unknown;
}
