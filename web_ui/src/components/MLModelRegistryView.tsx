import React, { useEffect, useState } from 'react';
import { fetchModels } from '../services/aiosApi';

const STAGE_COLORS = {
  production: {bg:'#065F46', fg:'#34D399'},
  staging:    {bg:'#1E40AF', fg:'#93C5FD'},
  archived:   {bg:'#374151', fg:'#9CA3AF'},
};

function stageStyle(stage) {
  const c = STAGE_COLORS[stage] || STAGE_COLORS.staging;
  return { backgroundColor:c.bg, color:c.fg, padding:'4px 10px', borderRadius:12, fontSize:11, fontWeight:700 };
}

export function MLModelRegistryView() {
  const [models, setModels] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => { fetchModels().then(setModels); }, []);

  const visible = models.filter(m => filter==='all' || m.stage===filter);

  const stats = {
    total: models.length,
    production: models.filter(m=>m.stage==='production').length,
    staging: models.filter(m=>m.stage==='staging').length,
  };

  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:8}}>🧠 ML Model Registry & Serving Platform</h2>
      <div style={{fontSize:13,color:'#94A3B8',marginBottom:20}}>
        ONNX, rule-based и статистические модели, stage promotion, контрольные суммы и метрики
      </div>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:12,marginBottom:20}}>
        <div style={{background:'#1E293B',padding:16,borderRadius:12,borderLeft:'4px solid #3B82F6'}}>
          <div style={{fontSize:12,color:'#94A3B8'}}>Всего моделей</div>
          <div style={{fontSize:26,fontWeight:800,marginTop:4}}>{stats.total}</div>
        </div>
        <div style={{background:'#1E293B',padding:16,borderRadius:12,borderLeft:'4px solid #10B981'}}>
          <div style={{fontSize:12,color:'#94A3B8'}}>В production</div>
          <div style={{fontSize:26,fontWeight:800,marginTop:4}}>{stats.production}</div>
        </div>
        <div style={{background:'#1E293B',padding:16,borderRadius:12,borderLeft:'4px solid #F59E0B'}}>
          <div style={{fontSize:12,color:'#94A3B8'}}>В staging</div>
          <div style={{fontSize:26,fontWeight:800,marginTop:4}}>{stats.staging}</div>
        </div>
      </div>

      <div style={{display:'flex',gap:6,marginBottom:12,flexWrap:'wrap'}}>
        {[['all','Все'],['production','Production'],['staging','Staging'],['archived','Archived']].map(([k,v])=>(
          <button key={k} onClick={()=>setFilter(k)}
            style={{background:filter===k?'#3B82F6':'#1E293B',color:filter===k?'#fff':'#CBD5E1',border:'1px solid #334155',padding:'6px 12px',borderRadius:8,cursor:'pointer',fontSize:12,fontWeight:600}}>
            {v}
          </button>
        ))}
      </div>

      <div style={{backgroundColor:'#1E293B',borderRadius:12,overflow:'hidden'}}>
        <div style={{overflowX:'auto'}}>
        <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
          <thead>
            <tr style={{backgroundColor:'#0F172A',color:'#94A3B8',borderBottom:'1px solid #334155'}}>
              <th style={{padding:'12px 16px',textAlign:'left'}}>Model</th>
              <th style={{padding:'12px 16px',textAlign:'left'}}>Version</th>
              <th style={{padding:'12px 16px',textAlign:'left'}}>Framework</th>
              <th style={{padding:'12px 16px',textAlign:'left'}}>Stage</th>
              <th style={{padding:'12px 16px',textAlign:'left'}}>SHA256</th>
              <th style={{padding:'12px 16px',textAlign:'left'}}>Metrics</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((m,idx)=>(
              <tr key={idx} style={{borderBottom:'1px solid #334155'}}>
                <td style={{padding:'12px 16px',fontWeight:700,color:'#38BDF8'}}>{m.name}</td>
                <td style={{padding:'12px 16px',fontWeight:600}}>{m.version}</td>
                <td style={{padding:'12px 16px',color:'#A855F7',textTransform:'uppercase',fontSize:12,fontWeight:700}}>{m.framework}</td>
                <td style={{padding:'12px 16px'}}><span style={stageStyle(m.stage)}>{(m.stage||'staging').toUpperCase()}</span></td>
                <td style={{padding:'12px 16px',fontFamily:'monospace',color:'#94A3B8',fontSize:11}}>{m.sha256}</td>
                <td style={{padding:'12px 16px',color:'#CBD5E1',fontSize:12}}>
                  {Object.entries(m.eval_metrics||{}).map(([k,v]) => (
                    <span key={k} style={{display:'inline-block',marginRight:10}}>
                      <b style={{color:'#94A3B8',fontWeight:500}}>{k}:</b> {typeof v==='number' ? (v<1?v.toFixed(3):v):v}
                    </span>
                  ))}
                  {(!m.eval_metrics || Object.keys(m.eval_metrics).length===0) && <span style={{color:'#64748B',fontStyle:'italic'}}>без метрик</span>}
                </td>
              </tr>
            ))}
            {visible.length===0 && <tr><td colSpan={6} style={{padding:30,textAlign:'center',color:'#94A3B8',fontStyle:'italic'}}>Нет моделей в этой стадии</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
