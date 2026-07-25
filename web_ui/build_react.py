#!/usr/bin/env python3
"""Build a single-file React dashboard:
 - bundles TSX sources from web_ui_src/ (mirror of repo web_ui/src/)
 - prepends live panels (OLX/Android/Services/Subs) + API client
 - uses React/ReactDOM UMD globals
 - outputs index_react.html — NO in-browser Babel needed (precompiled by esbuild).
"""
from pathlib import Path
import subprocess, sys, os, textwrap, shutil

HERE = Path(__file__).resolve().parent                 # /home/user
SRC = HERE / "web_ui_src"                              # mirrored web_ui/src/
OUT_HTML = HERE / "index_react.html"
BUILD_DIR = HERE / "_build"
ESBUILD = BUILD_DIR / "node_modules" / ".bin" / "esbuild"

LIVE_PANELS = r"""
import React from 'react';

// IMPORTANT: all fetch() calls use plain root-relative string literals ('/...')
// so that nginx sub_filter rewrites them under /aios/.
// NO concatenation, NO template literals, NO base-url variables here.

async function fetchOLX() { try { return await (await fetch('/api/olx')).json(); } catch(e){ return {available:false}; } }
async function fetchOLXList(limit) { try { return await (await fetch('/api/olx/list?sort=new&limit=' + (limit||6))).json(); } catch(e){ return {ads:[]}; } }
async function fetchServices() { try { return await (await fetch('/api/services')).json(); } catch(e){ return {services:[]}; } }
async function fetchAndroidDevicesLive() { try { return await (await fetch('/api/android/devices')).json(); } catch(e){ return {devices:[]}; } }
async function fetchAndroidScreenshot(serial) { try { return await (await fetch('/api/android/screenshot?serial=' + encodeURIComponent(serial||'emulator-5554'))).json(); } catch(e){ return {ok:false}; } }
async function postAndroidAction(action, args) {
  try { return await (await fetch('/api/android/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(Object.assign({action:action}, args||{}))})).json(); }
  catch(e){ return {ok:false, error:String(e)}; }
}
async function fetchSubs() { try { return await (await fetch('/api/subs')).json(); } catch(e){ return {subscriptions:[], chats:0}; } }
async function postSvcAction(svc, act) {
  try { return await (await fetch('/api/services/' + svc + '/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({action:act})})).json(); }
  catch(e){ return {ok:false}; }
}

export function OLXPanel() {
  const [olx, setOlx] = React.useState({available:false});
  const [ads, setAds] = React.useState([]);
  React.useEffect(() => {
    const load = async () => { setOlx(await fetchOLX()); const l = await fetchOLXList(6); setAds(l.ads||[]); };
    load(); const i = setInterval(load, 30000); return () => clearInterval(i);
  }, []);
  if(!olx.available) return <div style={{padding:'24px',color:'#F8FAFC'}}>OLX data unavailable.</div>;
  const kpis = [
    ['Всего объявлений', olx.ads_total||0, '#3B82F6'],
    ['Активных', olx.ads_active||0, '#10B981'],
    ['Новых за 24ч', olx.new_24h||0, '#F59E0B'],
    ['Средняя цена', olx.price_avg?Math.round(olx.price_avg).toLocaleString()+' UAH':'—', '#8B5CF6'],
  ];
  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:16}}>🛒 OLX Collector — Live</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:16,marginBottom:20}}>
        {kpis.map(([t,v,c])=>(
          <div key={t} style={{background:'#1E293B',padding:18,borderRadius:12,borderLeft:'4px solid '+c}}>
            <div style={{fontSize:12,color:'#94A3B8',fontWeight:600}}>{t}</div>
            <div style={{fontSize:24,fontWeight:800,margin:'6px 0'}}>{v}</div>
          </div>
        ))}
      </div>
      <h3 style={{fontSize:15,fontWeight:700,marginBottom:10}}>Последние объявления</h3>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(260px,1fr))',gap:12}}>
        {ads.map(a=>(
          <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer"
             style={{background:'#1E293B',padding:12,borderRadius:10,color:'#F8FAFC',textDecoration:'none',border:'1px solid #334155',display:'block'}}>
            {a.photos&&a.photos[0]?<img src={a.photos[0]} alt="" style={{width:'100%',height:120,objectFit:'cover',borderRadius:6,marginBottom:8}}/>:null}
            <div style={{fontSize:13,fontWeight:600}}>{(a.title||'').substring(0,70)}</div>
            <div style={{fontSize:14,fontWeight:700,color:'#34D399',marginTop:4}}>{a.price_value?Math.round(a.price_value).toLocaleString()+' '+(a.price_currency||'грн'):'Договірна'}</div>
            <div style={{fontSize:12,color:'#94A3B8',marginTop:4}}>📍 {a.city||'?'} · {a.query} {a.business?'🏢':'👤'}</div>
          </a>
        ))}
      </div>
    </div>
  );
}

export function ServicesPanel() {
  const [svcs, setSvcs] = React.useState({services:[]});
  const [loading, setLoading] = React.useState({});
  const load = async () => setSvcs(await fetchServices());
  React.useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);
  const act = async (n, a) => { setLoading(s=>({...s,[n]:true})); await postSvcAction(n,a); setTimeout(load, 1500); };
  const pill = s => ({background:s.active?'#065F46':s.state==='activating'?'#78350F':'#7F1D1D',color:s.active?'#6EE7B7':s.state==='activating'?'#FCD34D':'#FCA5A5',padding:'4px 10px',borderRadius:999,fontSize:11,fontWeight:600});
  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:16}}>⚙️ System Services</h2>
      <div style={{background:'#1E293B',borderRadius:12,overflow:'hidden'}}>
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead><tr><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Service</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Port</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Status</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Since</th><th style={{padding:'10px 14px',textAlign:'right',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Actions</th></tr></thead>
          <tbody>
            {svcs.services.map(s=>(
              <tr key={s.name} style={{borderBottom:'1px solid #334155'}}>
                <td style={{padding:'10px 14px'}}><b>{s.label}</b><div style={{fontSize:12,color:'#94A3B8'}}>{s.name}</div></td>
                <td style={{padding:'10px 14px'}}>{s.port||'—'}</td>
                <td style={{padding:'10px 14px'}}><span style={pill(s)}>{s.state}</span></td>
                <td style={{padding:'10px 14px',fontSize:12,color:'#94A3B8'}}>{(s.since||'').substring(0,16)}</td>
                <td style={{padding:'10px 14px',textAlign:'right'}}>
                  <button disabled={loading[s.name]||!s.active} onClick={()=>act(s.name,'stop')} style={{background:'transparent',border:'1px solid #334155',color:'#CBD5E1',padding:'4px 10px',borderRadius:6,cursor:'pointer',fontSize:12}}>⏹</button>
                  <button disabled={loading[s.name]} onClick={()=>act(s.name,'restart')} style={{background:'#3B82F6',color:'#fff',border:'none',padding:'4px 10px',borderRadius:6,cursor:'pointer',fontSize:12,marginLeft:4}}>🔄</button>
                  <button disabled={loading[s.name]||s.active} onClick={()=>act(s.name,'start')} style={{background:'#10B981',color:'#fff',border:'none',padding:'4px 10px',borderRadius:6,cursor:'pointer',fontSize:12,marginLeft:4}}>▶</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AndroidPanel() {
  const [devices, setDevices] = React.useState([]);
  const [cur, setCur] = React.useState(null);
  const [shot, setShot] = React.useState(null);
  const imgRef = React.useRef(null);
  const [imgSize, setImgSize] = React.useState({w:0,h:0});
  const [auto, setAuto] = React.useState(false);
  const autoRef = React.useRef();
  const loadDevs = async () => { const d = await fetchAndroidDevicesLive(); setDevices(d.devices||[]); if((!cur)&&d.devices&&d.devices[0]) setCur(d.devices[0].serial); };
  const takeShot = async () => { if(!cur) return; const r = await fetchAndroidScreenshot(cur); if(r.ok) setShot(r.image); };
  React.useEffect(() => { loadDevs(); }, []);
  React.useEffect(() => { if(cur) takeShot(); }, [cur]);
  React.useEffect(() => {
    if(auto){ autoRef.current = setInterval(takeShot, 3000); } else { clearInterval(autoRef.current); }
    return () => clearInterval(autoRef.current);
  }, [auto, cur]);
  const onImgLoad = (e) => setImgSize({w:e.target.naturalWidth,h:e.target.naturalHeight});
  const tap = async (e) => {
    if(!cur||!imgSize.w) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.round((e.clientX-rect.left)/rect.width*imgSize.w);
    const y = Math.round((e.clientY-rect.top)/rect.height*imgSize.h);
    await postAndroidAction('tap',{serial:cur,x,y});
    setTimeout(takeShot, 600);
  };
  const swipe = async dir => {
    if(!cur) return;
    const w = imgSize.w || 1080;
    const h = imgSize.h || 2280;
    const cx=Math.round(w/2), cy=Math.round(h/2);
    let x1=cx,y1=cy,x2=cx,y2=cy;
    if(dir==='up'){y1=cy+400;y2=cy-400;} if(dir==='down'){y1=cy-400;y2=cy+400;}
    if(dir==='left'){x1=cx+300;x2=cx-300;} if(dir==='right'){x1=cx-300;x2=cx+300;}
    await postAndroidAction('swipe',{serial:cur,x1,y1,x2,y2,duration:300}); setTimeout(takeShot,700);
  };
  const btnStyle = (bg)=>({background:bg||'transparent',border:'1px solid #334155',color:'#CBD5E1',padding:'6px 10px',borderRadius:6,cursor:'pointer',fontSize:12});
  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:8}}>📱 Android Fleet — Remote Control</h2>
      <div style={{fontSize:13,color:'#94A3B8',marginBottom:16}}>Тап по экрану = клик на устройстве. Свайпы/клавиши/текст поддерживаются.</div>
      <div style={{display:'grid',gridTemplateColumns:'280px 1fr',gap:20}}>
        <div>
          <div style={{background:'#1E293B',borderRadius:12,padding:14,marginBottom:12}}>
            <h4 style={{margin:'0 0 10px 0'}}>Devices</h4>
            {devices.map(d=>(
              <button key={d.serial} onClick={()=>setCur(d.serial)} style={{width:'100%',textAlign:'left',marginBottom:6,background:cur===d.serial?'#3B82F6':'transparent',color:cur===d.serial?'#fff':'#CBD5E1',border:'1px solid #334155',padding:'8px 12px',borderRadius:8,cursor:'pointer',fontSize:13}}>
                📱 {d.serial}
                <span style={{float:'right',fontSize:11,padding:'2px 8px',borderRadius:10,background:d.status==='online'?'#065F46':'#7F1D1D',color:d.status==='online'?'#6EE7B7':'#FCA5A5'}}>{d.status}</span>
                {d.model?<div style={{fontSize:11,color:cur===d.serial?'#DBEAFE':'#94A3B8',marginTop:4}}>{d.model} · Android {d.android||'?'}</div>:null}
              </button>
            ))}
            <button onClick={loadDevs} style={{width:'100%',marginTop:8,background:'transparent',border:'1px solid #334155',color:'#CBD5E1',padding:'6px 12px',borderRadius:8,cursor:'pointer',fontSize:12}}>🔄 Refresh</button>
          </div>
          <div style={{background:'#1E293B',borderRadius:12,padding:14}}>
            <h4 style={{margin:'0 0 10px 0'}}>Quick Actions</h4>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:6}}>
              <button style={btnStyle()} onClick={async()=>{await postAndroidAction('key',{serial:cur,keycode:3});setTimeout(takeShot,500);}}>🏠 Home</button>
              <button style={btnStyle()} onClick={async()=>{await postAndroidAction('key',{serial:cur,keycode:4});setTimeout(takeShot,500);}}>⬅ Back</button>
              <button style={btnStyle()} onClick={()=>swipe('up')}>⬆ Up</button>
              <button style={btnStyle()} onClick={()=>swipe('down')}>⬇ Down</button>
              <button style={btnStyle()} onClick={()=>swipe('left')}>⬅ Left</button>
              <button style={btnStyle()} onClick={()=>swipe('right')}>➡ Right</button>
            </div>
            <hr style={{border:'none',borderTop:'1px solid #334155',margin:'12px 0'}}/>
            <button onClick={()=>setAuto(!auto)} style={{width:'100%',background:auto?'#EF4444':'#10B981',color:'#fff',border:'none',padding:'6px 12px',borderRadius:8,cursor:'pointer',fontSize:12,fontWeight:600}}>{auto?'⏹ Стоп':'▶ Auto (3s)'}</button>
            <button onClick={takeShot} style={{width:'100%',marginTop:6,background:'#3B82F6',color:'#fff',border:'none',padding:'6px 12px',borderRadius:8,cursor:'pointer',fontSize:12,fontWeight:600}}>📸 Screenshot</button>
            <button onClick={async()=>{await postAndroidAction('launch',{serial:cur,package:'ua.slando'});setTimeout(takeShot,2000);}} style={{width:'100%',marginTop:6,background:'transparent',border:'1px solid #334155',color:'#CBD5E1',padding:'6px 12px',borderRadius:8,cursor:'pointer',fontSize:12}}>🛒 Launch OLX</button>
          </div>
        </div>
        <div style={{background:'#1E293B',borderRadius:12,padding:20,textAlign:'center'}}>
          <div style={{position:'relative',display:'inline-block',maxWidth:280,width:'100%'}}>
            {shot
              ? <img ref={imgRef} src={shot} onLoad={onImgLoad} style={{width:'100%',borderRadius:10,display:'block'}}/>
              : <div style={{padding:60,textAlign:'center',color:'#94A3B8'}}><div style={{fontSize:48}}>🖼️</div><div style={{marginTop:10}}>Нет скриншота</div></div>}
            <div onClick={tap} style={{position:'absolute',top:0,left:0,width:'100%',height:'100%',cursor:'crosshair',borderRadius:10}}/>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SubsPanel() {
  const [subs, setSubs] = React.useState({subscriptions:[],chats:0});
  React.useEffect(() => { fetchSubs().then(setSubs); }, []);
  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:16}}>🔔 Telegram Subscribers</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:16,marginBottom:20}}>
        <div style={{background:'#1E293B',padding:18,borderRadius:12,borderLeft:'4px solid #EC4899'}}>
          <div style={{fontSize:12,color:'#94A3B8'}}>Подписанных чатов</div><div style={{fontSize:28,fontWeight:800}}>{subs.chats||0}</div>
        </div>
        <div style={{background:'#1E293B',padding:18,borderRadius:12,borderLeft:'4px solid #3B82F6'}}>
          <div style={{fontSize:12,color:'#94A3B8'}}>Активных подписок</div><div style={{fontSize:28,fontWeight:800}}>{(subs.subscriptions||[]).length}</div>
        </div>
        <div style={{background:'#1E293B',padding:18,borderRadius:12,borderLeft:'4px solid #10B981'}}>
          <a href="https://t.me/AIOScontrol_bot" target="_blank" rel="noopener noreferrer" style={{background:'#10B981',color:'#fff',padding:'8px 14px',borderRadius:8,textDecoration:'none',display:'inline-block',marginTop:8,fontWeight:600}}>✈️ Открыть бота</a>
        </div>
      </div>
      <div style={{background:'#1E293B',borderRadius:12,overflow:'hidden'}}>
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead><tr><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Chat</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>User</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Query</th><th style={{padding:'10px 14px',textAlign:'left',color:'#94A3B8',background:'#0F172A',borderBottom:'1px solid #334155'}}>Price filter</th></tr></thead>
          <tbody>
            {(subs.subscriptions||[]).map((s,i)=>(
              <tr key={i} style={{borderBottom:'1px solid #334155'}}>
                <td style={{padding:'10px 14px'}}><code style={{background:'#0F172A',padding:'2px 6px',borderRadius:4,fontSize:11}}>{s.chat_id}</code></td>
                <td style={{padding:'10px 14px'}}>{s.first_name||s.username||'—'}{s.username?' @'+s.username:''}</td>
                <td style={{padding:'10px 14px'}}><b>{s.query}</b></td>
                <td style={{padding:'10px 14px'}}>{s.min_price||s.max_price?(s.min_price?Math.round(s.min_price).toLocaleString():'0')+'–'+(s.max_price?Math.round(s.max_price).toLocaleString()+' UAH':'∞'):'any'}</td>
              </tr>
            ))}
            {(subs.subscriptions||[]).length===0 && <tr><td colSpan={4} style={{padding:20,textAlign:'center',color:'#94A3B8',fontStyle:'italic'}}>Пока нет подписок. Бот: @AIOScontrol_bot</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
"""

ENTRY = BUILD_DIR / "entry.jsx"

def ensure_esbuild():
    if ESBUILD.exists():
        return
    BUILD_DIR.mkdir(exist_ok=True)
    (BUILD_DIR / "package.json").write_text(textwrap.dedent("""\
        {"name":"aios-build","private":true,"version":"1.0.0","devDependencies":{"esbuild":"^0.23.0"}}
    """), encoding="utf-8")
    subprocess.run(["npm","install","--no-audit","--no-fund","--loglevel=error"],
                   cwd=str(BUILD_DIR), check=True)
    assert ESBUILD.exists(), "esbuild install failed"

ensure_esbuild()

# Write live panels as a module
(BUILD_DIR / "live_panels.jsx").write_text(LIVE_PANELS, encoding="utf-8")

# Write the root App entry
entry_src = r"""
import React from 'react';
import { createRoot } from 'react-dom/client';
import { Header } from '../web_ui_src/components/Header';
import { OverviewView } from '../web_ui_src/components/OverviewView';
import { SafetyDashboardView } from '../web_ui_src/components/SafetyDashboardView';
import { AgentSwarmView } from '../web_ui_src/components/AgentSwarmView';
import { ConstitutionViewer } from '../web_ui_src/components/ConstitutionViewer';
import { KnowledgeGraphView } from '../web_ui_src/components/KnowledgeGraphView';
import { MLModelRegistryView } from '../web_ui_src/components/MLModelRegistryView';
import { AndroidFleetView } from '../web_ui_src/components/AndroidFleetView';
import { MarketplaceView } from '../web_ui_src/components/MarketplaceView';
import { fetchHealth as apiFetchHealth, fetchStats as apiFetchStats } from '../web_ui_src/services/aiosApi';
import { OLXPanel, ServicesPanel, AndroidPanel, SubsPanel } from './live_panels';

// NOTE: No runtime fetch() patching — nginx sub_filter rewrites inline `fetch("/...`
// literals (including minified ones) to `fetch("/aios/...` when served via reverse proxy,
// and direct :8580 access works fine as-is.

// Patch components from web_ui that originally fetched /api/v1/* (Bearer-protected)
// to use the new public dashboard endpoints: monkey-patch by aliasing in the entry
// is unnecessary — we patched services/aiosApi.ts to point at /api/safety, /api/models,
// /api/agents, /api/constitution, /api/knowledge-graph. MarketplaceView / AndroidFleetView
// still use /api/v1/marketplace/* and /api/v1/shards / /api/v1/android/devices, which
// don't exist on dashboard; their fetch() will 404 but they fall back to mock state.

function App() {
  const [activeTab, setActiveTab] = React.useState('overview');
  const [health, setHealth] = React.useState(null);
  const [stats, setStats] = React.useState(null);
  const [wsConnected] = React.useState(false);

  React.useEffect(() => {
    const loadData = () => {
      apiFetchHealth().then(setHealth).catch(()=>setHealth({status:'degraded',version:'9.0.0',timestamp:Date.now()}));
      apiFetchStats().then(setStats).catch(()=>{});
    };
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

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
  const extraTabs = [
    { id: 'olx',         label: '🛒 OLX Live',        render: () => <OLXPanel/> },
    { id: 'android_live',label: '📲 Android Remote',  render: () => <AndroidPanel/> },
    { id: 'services',    label: '⚙️ Services',       render: () => <ServicesPanel/> },
    { id: 'subs',        label: '🔔 Subscribers',    render: () => <SubsPanel/> },
  ];

  return (
    <div style={{backgroundColor:'#0F172A',minHeight:'100vh',fontFamily:'system-ui,-apple-system,sans-serif'}}>
      <Header health={health} activeTab={activeTab} setActiveTab={setActiveTab} wsConnected={wsConnected}/>
      <nav style={{maxWidth:'1400px',margin:'0 auto',padding:'8px 28px 0',display:'flex',gap:6,flexWrap:'wrap',borderBottom:'1px solid #1E293B'}}>
        {extraTabs.map(tab => (
          <button key={tab.id} onClick={()=>setActiveTab(tab.id)}
            style={{background:'transparent',border:'none',color:activeTab===tab.id?'#38BDF8':'#94A3B8',padding:'8px 12px',cursor:'pointer',fontSize:12,fontWeight:600,borderBottom:activeTab===tab.id?'2px solid #38BDF8':'2px solid transparent'}}>
            {tab.label}
          </button>
        ))}
      </nav>
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
      <footer style={{maxWidth:'1400px',margin:'0 auto',padding:'16px 28px',color:'#64748B',fontSize:12,display:'flex',gap:12,flexWrap:'wrap'}}>
        <span>AIOS v9.1 — React UI (из <code style={{background:'#0F172A',padding:'2px 6px',borderRadius:4,fontSize:11}}>web_ui/</code>, собран esbuild)</span>
        <span style={{marginLeft:'auto',display:'flex',gap:10}}>
          <a href="?">v4.1 simple</a>
          <a href="?v=adminlte">AdminLTE</a>
          <b style={{color:'#38BDF8'}}>React</b>
        </span>
      </footer>
    </div>
  );
}

var container = document.getElementById('root');
if (container) {
  createRoot(container).render(<App/>);
}
"""
ENTRY.write_text(entry_src, encoding="utf-8")
# ENTRY uses fetch('/api/...') etc as literals? We intentionally wrote it that way above.
# Double-check: any string-concat fetch remains? Strip the old runtime-patch code.
assert "LIVE_BASE" not in entry_src, "entry must not use LIVE_BASE; use plain '/...' literals"

# ---------- Bundle ----------
SHIM_DIR = BUILD_DIR / "shims"
R_SHIM = SHIM_DIR / "react"
RD_SHIM = SHIM_DIR / "react-dom"
R_SHIM.mkdir(parents=True, exist_ok=True)
RD_SHIM.mkdir(parents=True, exist_ok=True)
(R_SHIM / "index.js").write_text(
    "var r = window.React;\n"
    "for (var k in r) if (Object.prototype.hasOwnProperty.call(r,k)) exports[k] = r[k];\n"
    "exports.default = r;\n",
    encoding="utf-8",
)
(R_SHIM / "jsx-runtime.js").write_text(
    "var r = window.React;\n"
    "exports.Fragment = r.Fragment;\n"
    "exports.jsx = r.createElement;\n"
    "exports.jsxs = r.createElement;\n",
    encoding="utf-8",
)
(R_SHIM / "jsx-dev-runtime.js").write_text(
    "var r = window.React;\n"
    "exports.Fragment = r.Fragment;\n"
    "exports.jsxDEV = r.createElement;\n",
    encoding="utf-8",
)
(RD_SHIM / "index.js").write_text(
    "var d = window.ReactDOM;\n"
    "for (var k in d) if (Object.prototype.hasOwnProperty.call(d,k)) exports[k] = d[k];\n"
    "exports.default = d;\n",
    encoding="utf-8",
)
(RD_SHIM / "client.js").write_text(
    "var d = window.ReactDOM;\n"
    "exports.createRoot = d.createRoot || function(container){ return { render: function(el){ d.render(el, container); }, unmount: function(){} } };\n"
    "exports.hydrateRoot = d.hydrateRoot || function(c){ return { render: function(el){ d.render(el, c); } } };\n",
    encoding="utf-8",
)

out_tmp = BUILD_DIR / "bundle.min.js"
cmd = [
    str(ESBUILD),
    str(ENTRY),
    "--bundle",
    "--format=iife",
    "--global-name=AIOSApp",
    "--jsx=automatic",
    "--target=es2018",
    "--minify",
    "--define:process.env.NODE_ENV=\"production\"",
    f"--alias:react={R_SHIM}",
    f"--alias:react-dom={RD_SHIM}",
    f"--outfile={out_tmp}",
]
res = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True)
if res.returncode != 0:
    sys.stderr.write("ESBUILD STDERR:\n" + res.stderr + "\n")
    sys.stderr.write("ESBUILD STDOUT:\n" + res.stdout + "\n")
    raise SystemExit("esbuild failed")
bundled = out_tmp.read_text(encoding="utf-8")

HTML = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AIOS — React Hub</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.1/css/all.min.css">
<style>
  body{{margin:0;background:#0F172A;color:#F8FAFC;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}}
  *{{box-sizing:border-box;}}
  a{{color:#60A5FA;}}
  code{{background:#0F172A;padding:2px 6px;border-radius:4px;font-size:11px;}}
  button{{font-family:inherit;}}
  table{{font-size:13px;}}
  img{{max-width:100%;}}
</style>
</head>
<body>
<div id="root"></div>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script>
{bundled}
</script>
</body>
</html>
"""

OUT_HTML.write_text(HTML, encoding="utf-8")
print(f"[build] wrote {OUT_HTML} ({len(HTML)} bytes, JS {len(bundled)} bytes)")
