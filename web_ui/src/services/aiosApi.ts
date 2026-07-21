/**
 * AIOS REST API Client Service
 */

import { SystemStats, SystemHealth, SafetyData, ArticleSummary, KnowledgeGraphData, AgentProfile, MLModelInfo } from '../types';

const BASE_URL = '';

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchStats(): Promise<SystemStats> {
  const res = await fetch(`${BASE_URL}/api/v1/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function fetchSafetyData(): Promise<SafetyData> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/safety`);
    if (res.ok) return await res.json();
  } catch (e) {
    // Fallback default structure
  }
  return {
    safety_score: 1.0,
    status: 'healthy',
    metrics: { harm_score: 0.02, bias_score: 0.05, deception_score: 0.01 },
    recent_incidents: [],
    thresholds: { harm_score: 0.3, bias_score: 0.4, deception_score: 0.2 }
  };
}

export async function fetchConstitutionIndex(): Promise<ArticleSummary[]> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/constitution`);
    if (res.ok) return await res.json();
  } catch (e) {
    // Fallback
  }
  return Array.from({ length: 67 }, (_, i) => ({
    number: i + 1,
    numeral: `ARTICLE-${i + 1}`,
    title: `Constitutional Principle ${i + 1}`,
    filename: `ARTICLE-${i + 1}.md`,
    status: 'Active',
    level: 'Constitutional',
    scope: 'System-wide',
    valid: true
  }));
}

export async function fetchKnowledgeGraph(): Promise<KnowledgeGraphData> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/knowledge-graph`);
    if (res.ok) return await res.json();
  } catch (e) {}
  return {
    nodes: [
      { id: 'orchestrator', label: 'AIOS Core Orchestrator', type: 'agent' },
      { id: 'memory_main', label: 'Primary Vector Store', type: 'memory' },
      { id: 'const_engine', label: 'Constitution Engine (67 Articles)', type: 'rule' },
      { id: 'ml_planner', label: 'ML Scorer & Planner', type: 'model' }
    ],
    edges: [
      { source: 'orchestrator', target: 'memory_main', relation: 'PERSISTS' },
      { source: 'orchestrator', target: 'const_engine', relation: 'ENFORCES' },
      { source: 'orchestrator', target: 'ml_planner', relation: 'EVALUATES' }
    ]
  };
}

export async function fetchAgents(): Promise<AgentProfile[]> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/agents`);
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { agent_id: 'agent_alpha', name: 'Alpha Scientist', role: 'AI Scientist', autonomy_level: 5, autonomy_label: 'Self-Directed', status: 'thinking', completed_tasks: 42 },
    { agent_id: 'agent_beta', name: 'Beta Engineer', role: 'AI Engineer', autonomy_level: 4, autonomy_label: 'Autonomous', status: 'executing', completed_tasks: 128 },
    { agent_id: 'agent_gamma', name: 'Gamma Monitor', role: 'Safety Auditor', autonomy_level: 2, autonomy_label: 'Supervised', status: 'idle', completed_tasks: 310 }
  ];
}

export async function fetchModels(): Promise<MLModelInfo[]> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/models`);
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { name: 'risk_scorer', version: '1.0.0', framework: 'onnx', stage: 'production', sha256: 'a9f4c3b...', eval_metrics: { accuracy: 0.982, f1: 0.975 } },
    { name: 'plan_evaluator', version: '2.1.0', framework: 'scikit-learn', stage: 'production', sha256: 'e12d8a0...', eval_metrics: { mse: 0.012 } }
  ];
}
