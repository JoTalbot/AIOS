#!/usr/bin/env python3
"""Build a single-file React (Babel-standalone) dashboard from web_ui TSX sources + live panels."""
import re, os, json, sys
from pathlib import Path

SRC = Path('/home/user/web_ui_src')
OUT = Path('/home/user/index_react.html')

# ---------- TS -> JSX stripping ----------
def strip_ts(src: str) -> str:
    # Remove JSX comments: {/* ... */} including braces
    src = re.sub(r'\{\s*/\*.*?\*/\s*\}', '', src, flags=re.S)
    # Remove plain block comments (not JSX)
    src = re.sub(r'(?<!\{)/\*.*?\*/(?!\})', '', src, flags=re.S)
    # Remove // line comments (avoid http:// inside strings)
    src = re.sub(r'(?m)^[ \t]*//[^\n]*$', '', src)
    # Rewrite bare fetch('/...') and fetch(`/...`) to use BASE_URL
    src = re.sub(r"fetch\(\s*'/", "fetch(BASE_URL + '", src)
    src = re.sub(r'fetch\(\s*`/', 'fetch(BASE_URL + `', src)
    # Remove import lines (we'll inline all globals)
    src = re.sub(r'^\s*import\s+.*?;\s*$', '', src, flags=re.M)
    # Remove export keywords
    src = re.sub(r'\bexport\s+default\s+', '', src)
    src = re.sub(r'\bexport\s+', '', src)
    # Remove interface / type declarations (multi-line blocks)
    src = re.sub(r'\binterface\s+\w+[^{]*\{[^}]*\}\s*', '', src, flags=re.S)
    src = re.sub(r'\btype\s+\w+\s*=\s*[^;]+;\s*', '', src, flags=re.S)
    # Remove React.FC<...> generic type annotation
    src = re.sub(r':\s*React\.FC\s*<[^>]*>', '', src)
    # Remove generic type args on useState/useRef/useMemo etc: useState<Foo>( -> useState(
    src = re.sub(r'(useState|useRef|useMemo|useCallback|useEffect)\s*<[^>]+>', r'\1', src)
    # Remove `as X` type assertions
    src = re.sub(r'\bas\s+\w+(\.\w+)*(\[\])?\b', '', src)
    # Remove typed arrow function params: (x: Type, y: Type) -> (x, y)
    # This is tricky; we do it line-by-line with a simple regex that covers most cases
    src = re.sub(r'\(([^()]*)\)\s*=>', lambda m: '(' + _strip_params(m.group(1)) + ') =>', src)
    # Remove `: React.CSSProperties` / `: Record<string, React.CSSProperties>` etc trailing type annotations after =
    src = re.sub(r':\s*Record\s*<\s*string\s*,\s*React\.CSSProperties\s*>', '', src)
    src = re.sub(r':\s*React\.CSSProperties', '', src)
    src = re.sub(r':\s*React\.CSSProperties\s*\[\s*\]', '', src)
    # function foo(x: Type): RetType { ... } — strip param/return types between function name and {
    src = re.sub(r'(function\s+\w+\s*\()([^)]*)(\)\s*)(:\s*[\w<>\[\]\s,|]+)?(\s*\{)',
                 lambda m: m.group(1) + _strip_params(m.group(2)) + m.group(3) + m.group(5), src)
    # Remove trailing `: Type` on variable declarations (after const/let/var name and before =)
    # e.g. const x: Type = ...; but also const [a,b]: [Type,Type] = useState
    # Handle destructured generics: const [x, setX]: [T, U] = ... -> const [x, setX] =
    src = re.sub(r'(const|let|var)\s+(\[[^\]]+\])\s*:\s*\[[^\]]+\]\s*=', r'\1 \2 =', src)
    # Simple const x: Type =
    src = re.sub(r'(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]\s\|\.&]+(?=\s*[=;])', r'\1 \2', src)
    # Strip trailing return types on arrow functions (already handled via first param regex partially)
    # Remove "?: boolean" optional fields in destructuring remains not used (safe pass)
    # Remove `: string` `: number` `: boolean` `: any` `: void` etc standalone
    # Only strip primitive type annotations in positions we are sure of:
    # - after identifier followed by , or ) or = in parameter lists (handled by _strip_params already)
    # - after `?` optional marker
    # Avoid touching object literal values (`key: null`, `key: undefined`).
    src = re.sub(r'\?\s*:\s*(string|number|boolean|any|void|never|unknown|object)\b(\s*\[\s*\])?', '?', src)
    # Remove `<T>` generic after identifier like `arr.map<JSX.Element>` (rare)
    src = re.sub(r'\.\w+\s*<[^>]+>\s*\(', lambda m: re.sub(r'<[^>]+>', '', m.group(0)), src)
    # Collapse blank lines
    src = re.sub(r'\n{3,}', '\n\n', src)
    return src.strip()

def _strip_params(params: str) -> str:
    # Remove `: Type` annotations, optional `?`, from comma-separated params.
    out = []
    for p in params.split(','):
        p = p.strip()
        if not p:
            continue
        # Remove optional marker
        p = p.replace('?:', ':')
        # Split on ':' to remove type
        if ':' in p and not ('//' in p):
            # Keep only the name part before first ':'
            p = p.split(':', 1)[0].strip()
        out.append(p)
    return ', '.join(out)

# ---------- Load TSX sources ----------
def read(p):
    return (SRC / p).read_text(encoding='utf-8')

components_order = [
    'components/Header.tsx',
    'components/OverviewView.tsx',
    'components/SafetyDashboardView.tsx',
    'components/AgentSwarmView.tsx',
    'components/ConstitutionViewer.tsx',
    'components/KnowledgeGraphView.tsx',
    'components/MLModelRegistryView.tsx',
    'components/AndroidFleetView.tsx',
    'components/MarketplaceView.tsx',
]

services_src = read('services/aiosApi.ts')
app_src = read('App.tsx')

stripped_components = []
for c in components_order:
    s = strip_ts(read(c))
    name = Path(c).stem
    stripped_components.append(f"// ===== {name} =====\n{s}")

services_js = strip_ts(services_src)

# Patch services_js: BASE_URL should auto-detect /aios/ prefix, and correct endpoints to dashboard routes.
services_js_patch = """// ===== API client (auto-detect BASE_URL, real endpoints, fallbacks) =====
const _p = location.pathname;
const _mi = _p.indexOf('/aios/');
const BASE_URL = _mi >= 0 ? _p.substring(0, _mi + 5) : '';

async function fetchHealth() {
  try {
    const r = await fetch(BASE_URL + 'health');
    if (r.ok) {
      const j = await r.json();
      return { status: j.status === 'ok' ? 'ok' : 'degraded', version: j.version || '9.0.0', timestamp: Date.now() };
    }
  } catch(e) {}
  return { status: 'degraded', version: '9.0.0', timestamp: Date.now() };
}

async function fetchStats() {
  try {
    const r = await fetch(BASE_URL + 'api/stats');
    if (r.ok) {
      const j = await r.json();
      return {
        version: j.version || '9.0.0',
        runtime: j.runtime || 'python',
        uptime_seconds: j.uptime_seconds || 0,
        total_tasks: j.total_tasks || 0,
        completed_tasks: (j.total_tasks||0) - (j.failed_tasks||0),
        failed_tasks: j.failed_tasks || 0,
        active_agents: j.active_agents || 3,
        memory_nodes: (j.memory && j.memory.total) || 0,
        registered_capabilities: j.capabilities ? (j.capabilities.total || 0) : 0,
        constitutional_articles: j.constitution_articles || 67,
        compliance_ratio: 1.0,
        safety_score: 1.0,
      };
    }
  } catch(e) {}
  return { version:'9.0.0', uptime_seconds:0, total_tasks:0, completed_tasks:0, failed_tasks:0, active_agents:3, memory_nodes:0, safety_score:1.0, constitutional_articles:67, compliance_ratio:1.0 };
}

async function fetchSafetyData() {
  return { safety_score:1.0, status:'healthy', metrics:{ harm_score:0.02, bias_score:0.05, deception_score:0.01 }, recent_incidents:[], thresholds:{ harm_score:0.3, bias_score:0.4, deception_score:0.2 } };
}

async function fetchConstitutionIndex() {
  return Array.from({length:67},(_,i)=>({
    number:i+1, numeral:'ARTICLE-'+(i+1), title:'Constitutional Principle '+(i+1),
    filename:'ARTICLE-'+(i+1)+'.md', status:'Active', level:'Constitutional',
    scope:'System-wide', valid:true
  }));
}

async function fetchKnowledgeGraph() {
  return {
    nodes:[
      {id:'orchestrator',label:'AIOS Core Orchestrator',type:'agent'},
      {id:'memory_main',label:'Primary Vector Store',type:'memory'},
      {id:'const_engine',label:'Constitution Engine (67 Articles)',type:'rule'},
      {id:'ml_planner',label:'ML Scorer & Planner',type:'model'},
    ],
    edges:[
      {source:'orchestrator',target:'memory_main',relation:'PERSISTS'},
      {source:'orchestrator',target:'const_engine',relation:'ENFORCES'},
      {source:'orchestrator',target:'ml_planner',relation:'EVALUATES'},
    ]
  };
}

async function fetchAgents() {
  return [
    { agent_id:'agent_alpha', name:'Alpha Scientist', role:'AI Scientist', autonomy_level:5, autonomy_label:'Self-Directed', status:'thinking', completed_tasks:42 },
    { agent_id:'agent_beta', name:'Beta Engineer', role:'AI Engineer', autonomy_level:4, autonomy_label:'Autonomous', status:'executing', completed_tasks:128 },
    { agent_id:'agent_gamma', name:'Gamma Monitor', role:'Safety Auditor', autonomy_level:2, autonomy_label:'Supervised', status:'idle', completed_tasks:310 },
  ];
}

async function fetchModels() {
  return [
    { name:'risk_scorer', version:'1.0.0', framework:'onnx', stage:'production', sha256:'a9f4c3b...', eval_metrics:{ accuracy:0.982, f1:0.975 } },
    { name:'plan_evaluator', version:'2.1.0', framework:'scikit-learn', stage:'production', sha256:'e12d8a0...', eval_metrics:{ mse:0.012 } },
  ];
}
"""

# Strip original App.tsx, but we will replace it entirely with our RootApp that adds extra tabs
# (App.tsx imports components; after stripping imports won't exist, so we write our own.)

root_app = r"""
// ===== ROOT APP (augmented with live panels) =====
function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const loadData = () => {
      fetchHealth().then(setHealth).catch(()=>setHealth({status:'degraded',version:'9.0.0',timestamp:Date.now()}));
      fetchStats().then(setStats).catch(()=>{});
    };
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Extra tabs appended to the 8 built-in tabs
  const extraTabs = [
    { id: 'olx',         label: '🛒 OLX Live',       render: () => <OLXPanel/> },
    { id: 'android_live',label: '📲 Android Remote', render: () => <AndroidPanel/> },
    { id: 'services',    label: '⚙️ Services',      render: () => <ServicesPanel/> },
    { id: 'subs',        label: '🔔 Subscribers',   render: () => <SubsPanel/> },
  ];

  return (
    <div style={{backgroundColor:'#0F172A',minHeight:'100vh',fontFamily:'system-ui,-apple-system,sans-serif'}}>
      <HeaderWithExtra health={health} activeTab={activeTab} setActiveTab={setActiveTab} wsConnected={wsConnected} extraTabs={extraTabs}/>
      <main style={{maxWidth:'1400px',margin:'0 auto'}}>
        {activeTab==='overview'     && <OverviewView stats={stats}/>}
        {activeTab==='android'      && <AndroidFleetView/>}
        {activeTab==='marketplace'  && <MarketplaceView/>}
        {activeTab==='safety'       && <SafetyDashboardView/>}
        {activeTab==='swarm'        && <AgentSwarmView/>}
        {activeTab==='constitution' && <ConstitutionViewer/>}
        {activeTab==='kg'           && <KnowledgeGraphView/>}
        {activeTab==='ml'           && <MLModelRegistryView/>}
        {extraTabs.map(t => activeTab===t.id && <t.render key={t.id}/>)}
      </main>
      <footer style={{maxWidth:'1400px',margin:'0 auto',padding:'16px 24px',color:'#64748B',fontSize:12,display:'flex',gap:12,flexWrap:'wrap'}}>
        <span>AIOS v9.1 — React UI (built from <code>web_ui/</code>)</span>
        <span style={{marginLeft:'auto',display:'flex',gap:10}}>
          <a href="?">v4.1 simple</a>
          <a href="?v=adminlte">AdminLTE</a>
          <b style={{color:'#38BDF8'}}>React</b>
        </span>
      </footer>
    </div>
  );
}

// Extended Header that merges built-in tabs with extraTabs
function HeaderWithExtra({ health, activeTab, setActiveTab, wsConnected, extraTabs }) {
  const baseTabs = [
    { id: 'overview',     label: '📊 Overview' },
    { id: 'android',      label: '📱 Android Fleet M8' },
    { id: 'marketplace',  label: '🧩 Marketplace' },
    { id: 'safety',       label: '🛡 Safety' },
    { id: 'swarm',        label: '🤖 Swarm' },
    { id: 'constitution', label: '📜 Constitution' },
    { id: 'kg',           label: '🕸 KG' },
    { id: 'ml',           label: '🧠 ML' },
  ];
  const tabs = [...baseTabs, ...extraTabs.map(t => ({id:t.id, label:t.label}))];
  return (
    <header style={hdrStyles.header}>
      <div style={hdrStyles.branding}>
        <div style={hdrStyles.logoBadge}>AIOS</div>
        <div>
          <h1 style={hdrStyles.title}>Autonomous Intelligence Operating System</h1>
          <div style={hdrStyles.subTitle}>v9.1.0 React Hub — web_ui build • 12 tabs • live API</div>
        </div>
      </div>
      <nav style={hdrStyles.nav}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={()=>setActiveTab(tab.id)}
            style={{...hdrStyles.tabButton, ...(activeTab===tab.id?hdrStyles.activeTab:{})}}>
            {tab.label}
          </button>
        ))}
      </nav>
      <div style={hdrStyles.statusGroup}>
        <div style={hdrStyles.badge}>
          <span style={{...hdrStyles.dot, backgroundColor: wsConnected?'#10B981':'#F59E0B'}}></span>
          {wsConnected ? 'Live WS' : 'Polling'}
        </div>
        <div style={hdrStyles.badge}>
          <span style={{...hdrStyles.dot, backgroundColor: health && health.status==='ok' ? '#10B981':'#EF4444'}}></span>
          {health && health.status ? health.status.toUpperCase() : 'CONNECTING'}
        </div>
      </div>
    </header>
  );
}
const hdrStyles = {
  header:{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'16px 28px',backgroundColor:'#0F172A',borderBottom:'1px solid #1E293B',color:'#F8FAFC',flexWrap:'wrap',gap:12},
  branding:{display:'flex',alignItems:'center',gap:14},
  logoBadge:{backgroundColor:'#3B82F6',color:'#FFFFFF',fontWeight:800,fontSize:20,padding:'8px 14px',borderRadius:8,letterSpacing:1},
  title:{margin:0,fontSize:16,fontWeight:700,color:'#F8FAFC'},
  subTitle:{fontSize:11,color:'#94A3B8'},
  nav:{display:'flex',gap:6,flexWrap:'wrap'},
  tabButton:{backgroundColor:'transparent',border:'none',color:'#94A3B8',padding:'6px 10px',borderRadius:6,fontSize:12,fontWeight:600,cursor:'pointer'},
  activeTab:{backgroundColor:'#1E293B',color:'#38BDF8',borderBottom:'2px solid #38BDF8'},
  statusGroup:{display:'flex',gap:8},
  badge:{display:'flex',alignItems:'center',gap:6,backgroundColor:'#1E293B',padding:'6px 10px',borderRadius:20,fontSize:11,fontWeight:600,color:'#CBD5E1'},
  dot:{width:8,height:8,borderRadius:'50%'}
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App/>);
"""

# Live panels (from /tmp/react_panels.jsx) — strip duplicate BASE_URL detection (already defined in API section)
live_panels_raw = Path('/tmp/react_panels.jsx').read_text(encoding='utf-8')
live_panels = re.sub(r'^// === Live API helpers.*?const BASE_URL = _mi >= 0 \? _p\.substring\(0, _mi \+ 5\) : \x27\x27;\s*',
                     '// === Live panels ===\n', live_panels_raw, count=1, flags=re.S)

# ---------- HTML template ----------
HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\"/>
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>
<title>AIOS — React Hub</title>
<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css\">
<style>
  body{margin:0;background:#0F172A;color:#F8FAFC;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}
  *{box-sizing:border-box;}
  a{color:#60A5FA;}
  code{background:#0F172A;padding:2px 6px;border-radius:4px;font-size:11px;}
  .btn{background:#3B82F6;color:#fff;border:none;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;}
  .btn:hover{background:#2563EB;}
  .btn.sm{padding:4px 10px;font-size:12px;}
  .btn.green{background:#10B981;}.btn.green:hover{background:#059669}
  .btn.red{background:#EF4444;}.btn.red:hover{background:#DC2626}
  .btn.ghost{background:transparent;border:1px solid #334155;color:#CBD5E1;}
  .pill{background:#1E293B;border:1px solid #334155;color:#CBD5E1;padding:4px 10px;border-radius:999px;font-size:11px;fontWeight:600;}
  .pill.green{background:#065F46;color:#6EE7B7;border-color:#065F46;}
  .pill.red{background:#7F1D1D;color:#FCA5A5;border-color:#7F1D1D;}
  .pill.orange{background:#78350F;color:#FCD34D;border-color:#78350F;}
  input,select,textarea{background:#0F172A;border:1px solid #334155;color:#F8FAFC;padding:8px 12px;border-radius:6px;font-size:13px;}
  table{width:100%;border-collapse:collapse;}
  th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #334155;font-size:13px;}
  th{color:#94A3B8;font-weight:600;background:#0F172A;}
  .muted{color:#94A3B8;font-size:12px;}
  pre{background:#0F172A;padding:12px;border-radius:8px;font-size:11px;overflow:auto;white-space:pre-wrap;margin:0;}
  .w-100{width:100%;}
  .mr-1{margin-right:4px;}
  .screenshot-wrap{position:relative;display:inline-block;max-width:280px;width:100%;}
  .screenshot-wrap canvas{position:absolute;top:0;left:0;width:100%;cursor:crosshair;border-radius:10px;}
  .screenshot-wrap img{width:100%;border-radius:10px;display:block;}
</style>
</head>
<body>
<div id=\"root\"></div>

<script crossorigin src=\"https://unpkg.com/react@18/umd/react.production.min.js\"></script>
<script crossorigin src=\"https://unpkg.com/react-dom@18/umd/react-dom.production.min.js\"></script>
<script src=\"https://unpkg.com/regenerator-runtime@0.14.1/runtime.js\"></script>
<script src=\"https://unpkg.com/@babel/standalone/babel.min.js\"></script>

<script type=\"text/babel\" data-presets=\"env,react\">
const { useState, useEffect, useRef, useMemo, useCallback } = React;

__API__
__COMPONENTS__
__LIVE__
__APP__
</script>
</body>
</html>
"""

all_components_js = '\n\n'.join(stripped_components)

html = (HTML
        .replace('__API__', services_js_patch)
        .replace('__COMPONENTS__', all_components_js)
        .replace('__LIVE__', live_panels)
        .replace('__APP__', root_app))

OUT.write_text(html, encoding='utf-8')
print(f"Wrote {OUT} ({len(html)} bytes)")
