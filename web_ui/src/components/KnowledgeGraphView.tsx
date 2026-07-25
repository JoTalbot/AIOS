import React, { useEffect, useState, useRef } from 'react';
import { fetchKnowledgeGraph } from '../services/aiosApi';

// ---------- Interactive Knowledge Graph ----------
const KG_NODE_COLORS = { agent:'#3B82F6', rule:'#10B981', memory:'#A855F7', model:'#F59E0B', resource:'#EC4899' };
const KG_NODE_ICONS  = { agent:'🤖', rule:'📜', memory:'💾', model:'🧠', resource:'📦' };

function InteractiveKnowledgeGraph({ data }) {
  const nodes = (data && data.nodes) || [];
  const edges = (data && data.edges) || [];
  const W = 900, H = 480;
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [positions, setPositions] = useState({});
  const dragRef = useRef(null);
  const svgRef = useRef(null);

  useEffect(() => {
    const cx = W/2, cy = H/2;
    const pos = {};
    const n = nodes.length;
    if (n === 0) { setPositions({}); return; }
    const radius = Math.min(W,H)/2 - 80;
    const others = nodes.filter(x => x.id !== 'orchestrator');
    const m = others.length;
    nodes.forEach(nd => {
      if (nd.id === 'orchestrator') pos[nd.id] = {x:cx,y:cy};
      else {
        const idx = others.indexOf(nd);
        const angle = (idx/M)*Math.PI*2 - Math.PI/2;
        pos[nd.id] = { x: cx+Math.cos(angle)*radius, y: cy+Math.sin(angle)*radius };
      }
    });
    setPositions(pos);
    setSelected(nodes.find(x=>x.id==='orchestrator') || nodes[0] || null);
  }, [nodes.map(n=>n.id).join(',')]);

  const onNodeDown = (e,id) => {
    e.stopPropagation();
    dragRef.current = { id, sx:e.clientX, sy:e.clientY, ox:positions[id].x, oy:positions[id].y };
  };
  const onMove = (e) => {
    if(!dragRef.current) return;
    const {id,sx,sy,ox,oy} = dragRef.current;
    setPositions(p => ({...p, [id]:{x:ox+(e.clientX-sx)/zoom, y:oy+(e.clientY-sy)/zoom}}));
  };
  const onUp = () => dragRef.current = null;
  const onWheel = (e) => { e.preventDefault(); setZoom(z => Math.max(0.4, Math.min(2.5, z*(e.deltaY>0?0.9:1.1)))); };

  const nodeById = React.useMemo(()=>Object.fromEntries(nodes.map(n=>[n.id,n])),[nodes]);
  const connected = React.useMemo(() => {
    if (!selected) return [];
    return edges.filter(e=>e.source===selected.id||e.target===selected.id);
  }, [edges,selected]);
  const connIds = React.useMemo(()=>new Set(connected.flatMap(e=>[e.source,e.target])),[connected]);

  return (
    <div style={{display:'grid',gridTemplateColumns:'1fr 320px',gap:16,marginTop:16}}>
      <div style={{background:'#0F172A',borderRadius:12,overflow:'hidden',position:'relative'}}>
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`}
             style={{width:'100%',height:H,cursor:dragRef.current?'grabbing':'default',background:'radial-gradient(circle at 50% 50%, #1E293B 0%, #0F172A 70%)'}}
             onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp} onWheel={onWheel}>
          <defs>
            <marker id="kg-arrow" markerWidth="10" markerHeight="10" refX="18" refY="4" orient="auto"><path d="M0,0 L0,8 L8,4 z" fill="#475569"/></marker>
            <marker id="kg-arrow-hi" markerWidth="10" markerHeight="10" refX="18" refY="4" orient="auto"><path d="M0,0 L0,8 L8,4 z" fill="#38BDF8"/></marker>
          </defs>
          <g transform={`scale(${zoom})`} style={{transformOrigin:'center'}}>
            {edges.map((e,i)=>{
              const a=positions[e.source],b=positions[e.target]; if(!a||!b) return null;
              const hi = selected && (e.source===selected.id||e.target===selected.id);
              const faded = selected && !hi;
              const dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)||1;
              const ax=a.x+dx/d*26, ay=a.y+dy/d*26;
              const bx=b.x-dx/d*26, by=b.y-dy/d*26;
              const mx=(ax+bx)/2, my=(ay+by)/2;
              return (
                <g key={i}>
                  <line x1={ax} y1={ay} x2={bx} y2={by}
                        stroke={hi?'#38BDF8':'#334155'} strokeWidth={hi?2.5:1.2}
                        opacity={faded?0.2:1}
                        markerEnd={hi?'url(#kg-arrow-hi)':'url(#kg-arrow)'}/>
                  <text x={mx} y={my-4} fontSize={10} fill={hi?'#BAE6FD':'#64748B'} textAnchor="middle" opacity={faded?0.3:1} style={{pointerEvents:'none'}}>{e.relation}</text>
                </g>
              );
            })}
            {nodes.map(n=>{
              const p=positions[n.id]; if(!p) return null;
              const isSel = selected && selected.id===n.id;
              const isConn = connIds.has(n.id);
              const isHover = hover===n.id;
              const color = KG_NODE_COLORS[n.type]||'#64748B';
              const r = n.id==='orchestrator'?32:22;
              return (
                <g key={n.id} transform={`translate(${p.x},${p.y})`} style={{cursor:'grab'}}
                   onMouseDown={e=>onNodeDown(e,n.id)}
                   onMouseEnter={()=>setHover(n.id)} onMouseLeave={()=>setHover(null)}
                   onClick={e=>{e.stopPropagation();setSelected(n);}}>
                  <circle r={r+6} fill="none" stroke={color} strokeWidth={isSel?3:isConn?2:0} opacity={isSel?0.6:isConn?0.4:0}/>
                  <circle r={r} fill={color} opacity={selected && !isSel && !isConn ? 0.35 : 1}
                          stroke={isHover?'#F8FAFC':color} strokeWidth={isHover?2:0}/>
                  <text textAnchor="middle" dy={isHover?-r-8:5} fontSize={isHover?13:16} fill={isHover?'#F8FAFC':'#FFF'} style={{pointerEvents:'none',fontWeight:600}}>
                    {KG_NODE_ICONS[n.type]||'●'}
                  </text>
                  {isHover && <text textAnchor="middle" y={r+16} fontSize={11} fill="#E2E8F0" style={{pointerEvents:'none'}}>{n.label}</text>}
                </g>
              );
            })}
          </g>
        </svg>
        <div style={{position:'absolute',bottom:8,right:12,display:'flex',gap:6}}>
          <button onClick={()=>setZoom(z=>Math.min(2.5,z*1.2))} style={zb}>+</button>
          <button onClick={()=>setZoom(1)} style={zb}>⟲</button>
          <button onClick={()=>setZoom(z=>Math.max(0.4,z*0.8))} style={zb}>−</button>
        </div>
        <div style={{position:'absolute',top:8,left:12,fontSize:11,color:'#94A3B8'}}>
          💡 Перетаскивайте узоры мышью · колесо = zoom · клик = детали
        </div>
        <div style={{position:'absolute',top:8,right:12,display:'flex',gap:8,fontSize:11}}>
          {Object.entries(KG_NODE_COLORS).map(([t,c])=>(
            <span key={t} style={{display:'flex',alignItems:'center',gap:4,color:'#CBD5E1'}}>
              <span style={{width:10,height:10,borderRadius:'50%',background:c,display:'inline-block'}}/>{t}
            </span>
          ))}
        </div>
      </div>

      <div style={{background:'#1E293B',borderRadius:12,padding:18}}>
        {selected ? (
          <>
            <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:10}}>
              <div style={{width:40,height:40,borderRadius:10,background:KG_NODE_COLORS[selected.type]||'#334155',display:'flex',alignItems:'center',justifyContent:'center',fontSize:22}}>{KG_NODE_ICONS[selected.type]||'●'}</div>
              <div>
                <div style={{fontSize:15,fontWeight:700}}>{selected.label}</div>
                <div style={{fontSize:11,color:'#94A3B8',textTransform:'uppercase',letterSpacing:1}}>{selected.type} · {selected.id}</div>
              </div>
            </div>
            {selected.detail && <div style={{fontSize:13,color:'#CBD5E1',marginBottom:14,lineHeight:1.5}}>{selected.detail}</div>}
            <div style={{fontSize:12,fontWeight:600,color:'#94A3B8',marginBottom:6,textTransform:'uppercase',letterSpacing:1}}>Связи ({connected.length})</div>
            <div style={{display:'grid',gap:6}}>
              {connected.map((e,i)=>{
                const otherId = e.source===selected.id ? e.target : e.source;
                const other = nodeById[otherId];
                const dir = e.source===selected.id?'→':'←';
                return (
                  <button key={i} onClick={()=>setSelected(other)}
                    style={{background:'#0F172A',border:'1px solid #334155',color:'#E2E8F0',padding:'8px 10px',borderRadius:8,textAlign:'left',cursor:'pointer',fontSize:12,display:'flex',alignItems:'center',gap:8}}>
                    <span style={{color:'#38BDF8',fontWeight:700}}>{dir}</span>
                    <span style={{marginRight:'auto'}}>{other?other.label:otherId}</span>
                    <span style={{color:'#94A3B8',fontSize:11}}>{e.relation}</span>
                  </button>
                );
              })}
              {connected.length===0 && <div style={{fontSize:12,color:'#64748B',fontStyle:'italic'}}>Нет связей</div>}
            </div>
          </>
        ) : (
          <div style={{color:'#94A3B8',fontStyle:'italic'}}>Кликните на узел для деталей</div>
        )}
      </div>
    </div>
  );
}
const zb = {background:'#0F172A',color:'#CBD5E1',border:'1px solid #334155',borderRadius:6,width:28,height:28,cursor:'pointer',fontSize:14,lineHeight:1};

export function KnowledgeGraphView() {
  const [kg, setKg] = useState(null);
  useEffect(() => { fetchKnowledgeGraph().then(setKg); }, []);
  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <h2 style={{fontSize:20,fontWeight:700,marginBottom:8}}>🕸 Executive Knowledge Graph</h2>
      <div style={{fontSize:13,color:'#94A3B8',marginBottom:4}}>
        Интерактивная карта агентов, правил конституции, памяти и ML-моделей AIOS
      </div>
      {kg && kg.nodes && kg.nodes.length > 0
        ? <InteractiveKnowledgeGraph data={kg}/>
        : <div style={{padding:40,textAlign:'center',color:'#94A3B8'}}>Загрузка графа...</div>}
    </div>
  );
}
