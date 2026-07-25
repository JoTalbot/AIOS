export type HealthStatus = "ok" | "degraded" | "error";
export type ServiceState = "active" | "activating" | "failed" | "inactive";
export type Severity = "info" | "success" | "warning" | "critical";

export interface SystemStats {
  version: string;
  runtime: string;
  uptime_seconds: number;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  active_agents: number;
  memory_nodes: number;
  registered_capabilities: number;
  constitutional_articles: number;
  compliance_ratio: number;
  safety_score: number;
  api_routes: number;
  tests_passed: number;
  platforms: number;
  tasks_per_min: number;
  p95_latency_ms: number;
}

export interface PlatformInfo {
  id: string;
  name: string;
  package: string;
  status: "full" | "collector" | "messaging" | "scaffold";
  emoji: string;
  color: string;
  profiles: number;
  actionsToday: number;
  successRate: number;
  region: string;
  trend: number[];
}

export interface AgentProfile {
  agent_id: string;
  name: string;
  role: string;
  autonomy: number;
  autonomy_label: string;
  status: "idle" | "executing" | "thinking" | "blocked";
  current_task?: string;
  completed_tasks: number;
  platform?: string;
  load: number;
  trend: number[];
}

export interface ConstitutionArticle {
  number: number;
  numeral: string;
  title: string;
  category: string;
  status: string;
  level: string;
  scope: string;
  valid: boolean;
}

export interface AndroidDevice {
  serial: string;
  model: string;
  host: string;
  status: "online" | "busy" | "offline";
  profile: string;
  battery: number;
  platform: string;
  uptime: number;
}

export interface ServiceInfo {
  name: string;
  label: string;
  port?: number;
  state: ServiceState;
  active: boolean;
  since: string;
  cpu: number;
  mem: number;
}

export interface OlxAd {
  id: string;
  title: string;
  price_value?: number;
  price_currency?: string;
  city?: string;
  query: string;
  business: boolean;
  url: string;
  photos?: string[];
  published?: number;
}

export interface OlxSummary {
  available: boolean;
  ads_total: number;
  ads_active: number;
  new_24h: number;
  price_avg: number;
}

export interface AuditEvent {
  id: string;
  ts: number;
  type: "compliance" | "agent" | "platform" | "security" | "system" | "approval";
  actor: string;
  action: string;
  detail: string;
  severity: Severity;
}

export interface SafetyData {
  safety_score: number;
  status: "healthy" | "warning" | "critical";
  metrics: Record<string, number>;
  thresholds: Record<string, number>;
  incidents: Array<{ id: string; severity: string; description: string; timestamp: number; resolved: boolean }>;
}

export interface MLModelInfo {
  name: string;
  version: string;
  framework: string;
  stage: "staging" | "production" | "archived";
  sha256: string;
  eval_metrics: Record<string, number>;
  size_mb: number;
}

export interface KgNode {
  id: string;
  label: string;
  type: "agent" | "memory" | "task" | "rule" | "model";
}
export interface KgEdge {
  source: string;
  target: string;
  relation: string;
}
export interface KnowledgeGraphData {
  nodes: KgNode[];
  edges: KgEdge[];
}

export interface ApiKey {
  id: string;
  subject: string;
  prefix: string;
  roles: string[];
  created: string;
  ttl_days: number;
  status: "active" | "expired" | "revoked";
  uses: number;
}

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  status: "active" | "paused";
  delivered: number;
  failed: number;
}

export interface Backup {
  id: string;
  label: string;
  created: string;
  size_mb: number;
  verified: boolean;
  kind: "auto" | "manual";
}

export interface Subscription {
  id: string;
  chat_id?: string | number;
  query: string;
  min: number;
  max: number;
  matches: number;
  active: boolean;
}

export interface Series {
  tasks: number[];
  compliance: number[];
  latency: number[];
  throughput: number[];
}

export interface LiveData {
  stats: SystemStats;
  series: Series;
  services: ServiceInfo[];
  olx: OlxSummary;
  audit: AuditEvent[];
  agents: AgentProfile[];
  devices: AndroidDevice[];
  safety: SafetyData;
  subscriptions: Subscription[];
  health: HealthStatus;
  wsConnected: boolean;
  tick: number;
}
