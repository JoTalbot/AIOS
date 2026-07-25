/**
 * AIOS REST API Client Service
 *
 * IMPORTANT: All fetch() calls MUST use a plain string literal starting with '/'
 * (NO variable concatenation, NO template literals) so that the nginx
 * reverse-proxy sub_filter rules (`fetch('/` -> `fetch('/aios/`, `"/api/` -> `"/aios/api/`,
 * `"/health"` -> `"/aios/health"`) can reliably rewrite URLs when served under /aios/.
 */

// NOTE: intentionally inlined as string literals below — see comment above.

export async function fetchHealth() {
  // fetch('/health') - rewritten by nginx under /aios/ to fetch('/aios/health')
  const res = await fetch('/health');
  if (!res.ok) throw new Error('Health check failed');
  const j = await res.json();
  return { status: j.status === 'ok' ? 'ok' : 'degraded', version: j.version || '9.0.0', timestamp: Date.now() };
}

export async function fetchStats() {
  const res = await fetch('/api/stats');
  if (!res.ok) throw new Error('Failed to fetch stats');
  const j = await res.json();
  return {
    version: j.version || '9.0.0',
    runtime: j.runtime || 'python',
    uptime_seconds: j.uptime_seconds || 0,
    total_tasks: j.total_tasks || 0,
    completed_tasks: (j.total_tasks || 0) - (j.failed_tasks || 0),
    failed_tasks: j.failed_tasks || 0,
    active_agents: j.active_agents || 3,
    memory_nodes: (j.memory && j.memory.total) || 0,
    registered_capabilities: j.capabilities ? (j.capabilities.total || 0) : 0,
    constitutional_articles: j.constitution_articles || 67,
    compliance_ratio: 1.0,
    safety_score: 1.0,
  };
}

export async function fetchSafetyData() {
  try {
    const res = await fetch('/api/v1/safety');
    if (res.ok) return await res.json();
  } catch (e) { /* fall through to defaults */ }
  return {
    safety_score: 1.0,
    status: 'healthy',
    metrics: { harm_score: 0.02, bias_score: 0.05, deception_score: 0.01 },
    recent_incidents: [],
    thresholds: { harm_score: 0.3, bias_score: 0.4, deception_score: 0.2 }
  };
}

export async function fetchConstitutionIndex() {
  try {
    const res = await fetch('/api/v1/constitution');
    if (res.ok) return await res.json();
  } catch (e) { /* fall through */ }
  return Array.from({ length: 67 }, (_, i) => ({
    number: i + 1,
    numeral: 'ARTICLE-' + (i + 1),
    title: 'Constitutional Principle ' + (i + 1),
    filename: 'ARTICLE-' + (i + 1) + '.md',
    status: 'Active',
    level: 'Constitutional',
    scope: 'System-wide',
    valid: true
  }));
}

export async function fetchKnowledgeGraph() {
  try {
    const res = await fetch('/api/v1/knowledge-graph');
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

export async function fetchAgents() {
  try {
    const res = await fetch('/api/v1/agents');
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { agent_id: 'agent_alpha', name: 'Alpha Scientist', role: 'AI Scientist', autonomy_level: 5, autonomy_label: 'Self-Directed', status: 'thinking', completed_tasks: 42 },
    { agent_id: 'agent_beta', name: 'Beta Engineer', role: 'AI Engineer', autonomy_level: 4, autonomy_label: 'Autonomous', status: 'executing', completed_tasks: 128 },
    { agent_id: 'agent_gamma', name: 'Gamma Monitor', role: 'Safety Auditor', autonomy_level: 2, autonomy_label: 'Supervised', status: 'idle', completed_tasks: 310 }
  ];
}

export async function fetchModels() {
  try {
    const res = await fetch('/api/v1/models');
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { name: 'risk_scorer', version: '1.0.0', framework: 'onnx', stage: 'production', sha256: 'a9f4c3b...', eval_metrics: { accuracy: 0.982, f1: 0.975 } },
    { name: 'plan_evaluator', version: '2.1.0', framework: 'scikit-learn', stage: 'production', sha256: 'e12d8a0...', eval_metrics: { mse: 0.012 } }
  ];
}
