/**
 * AIOS Web UI TypeScript Type Definitions
 */

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
  federation?: any;
  ml_scorer?: any;
}

export interface SystemHealth {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  timestamp: number;
}

export interface SafetyData {
  safety_score: number;
  status: 'healthy' | 'warning' | 'critical';
  metrics: Record<string, number>;
  recent_incidents: Array<{
    id?: string;
    severity: string;
    description: string;
    timestamp?: number;
  }>;
  thresholds: Record<string, number>;
}

export interface ArticleSummary {
  number: number;
  numeral: string;
  title: string;
  filename: string;
  status: string;
  level: string;
  scope: string;
  valid: boolean;
}

export interface KGNode {
  id: string;
  label: string;
  type: 'agent' | 'memory' | 'task' | 'rule' | 'model';
}

export interface KGEdge {
  source: string;
  target: string;
  relation: string;
}

export interface KnowledgeGraphData {
  nodes: KGNode[];
  edges: KGEdge[];
}

export interface AgentProfile {
  agent_id: string;
  name: string;
  role: string;
  autonomy_level: number;
  autonomy_label: string;
  current_task?: string;
  status: 'idle' | 'executing' | 'thinking' | 'blocked';
  completed_tasks: number;
}

export interface MLModelInfo {
  name: string;
  version: string;
  framework: string;
  stage: 'staging' | 'production' | 'archived';
  sha256: string;
  eval_metrics: Record<string, number>;
}
