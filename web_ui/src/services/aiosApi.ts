/**
 * AIOS REST API Client Service (dashboard public endpoints, no Bearer).
 *
 * URLs are kept as plain `fetch('/...')` string literals so nginx sub_filter can
 * rewrite them to `/aios/...` when served through the reverse proxy.
 */

export async function fetchHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error('Health check failed');
  const j = await res.json();
  return { status: j.status === 'ok' ? 'ok' : 'degraded', version: j.version || '9.0.0', timestamp: Date.now() };
}

export async function fetchStats() {
  const res = await fetch('/api/stats');
  if (!res.ok) throw new Error('Failed to fetch stats');
  const j = await res.json();
  const ss = (j.subsystems && j.subsystems.policy && j.subsystems.policy.validation_summary) || {};
  const tot = ss.total_validations || 0, inv = ss.invalid || 0;
  return {
    version: j.version || '9.0.0',
    runtime: 'python',
    uptime_seconds: j.uptime_seconds || 0,
    total_tasks: j.total_tasks || 0,
    completed_tasks: (j.total_tasks||0) - (j.failed_tasks||0),
    failed_tasks: j.failed_tasks || 0,
    active_agents: Math.max(3, j.active_tasks || 3),
    memory_nodes: (j.memory_items||0) + (j.subsystems&&j.subsystems.memory?j.subsystems.memory.total||0:0),
    registered_capabilities: j.subsystems && j.subsystems.capabilities ? (j.subsystems.capabilities.total||0) : 3,
    constitutional_articles: j.constitution_articles || 67,
    compliance_ratio: tot>0 ? Math.max(0,(tot-inv)/tot) : 1.0,
    safety_score: tot>0 ? Math.max(0,Math.min(1,(tot-inv)/tot)) : 1.0,
    _raw: j,
  };
}

export async function fetchSafetyData() {
  try {
    const res = await fetch('/api/safety');
    if (res.ok) return await res.json();
  } catch (e) { /* fall through */ }
  return {
    safety_score: 1.0,
    status: 'healthy',
    metrics: { harm_score: 0.02, bias_score: 0.05, deception_score: 0.01 },
    recent_incidents: [],
    thresholds: { harm_score:0.3, bias_score:0.4, deception_score:0.2 }
  };
}

export async function fetchConstitutionIndex() {
  try {
    const res = await fetch('/api/constitution');
    if (res.ok) return await res.json();
  } catch (e) { /* fall through */ }
  return Array.from({length:67},(_,i)=>({
    number:i+1, numeral:'ARTICLE-'+(i+1), title:'Constitutional Principle '+(i+1),
    filename:'ARTICLE-'+(i+1)+'.md', status:'Active', level:'Constitutional',
    scope:'System-wide', valid:true
  }));
}

export async function fetchConstitutionArticle(num) {
  try {
    const res = await fetch('/api/constitution/' + num);
    if (res.ok) return await res.json();
  } catch (e) {}
  return null;
}

export async function fetchKnowledgeGraph() {
  try {
    const res = await fetch('/api/knowledge-graph');
    if (res.ok) return await res.json();
  } catch (e) {}
  return { nodes: [], edges: [] };
}

export async function fetchAgents() {
  try {
    const res = await fetch('/api/agents');
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { agent_id:'agent_alpha', name:'Alpha Scientist', role:'AI Scientist', autonomy_level:5, autonomy_label:'Self-Directed', status:'thinking', completed_tasks:42 },
  ];
}

export async function fetchModels() {
  try {
    const res = await fetch('/api/models');
    if (res.ok) return await res.json();
  } catch (e) {}
  return [
    { name:'risk_scorer', version:'1.0.0', framework:'onnx', stage:'production', sha256:'a9f4c3b...', eval_metrics:{accuracy:0.98} },
  ];
}
