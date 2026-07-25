import React, { useEffect, useState } from 'react';
import { fetchConstitutionIndex, fetchConstitutionArticle } from '../services/aiosApi';
import { InteractiveKnowledgeGraph } from './KnowledgeGraphInline';

// Re-using InteractiveKnowledgeGraph as a separate module — but we keep it inline
// in KnowledgeGraphView.tsx. For Constitution we just need list + body viewer.

export function ConstitutionViewer() {
  const [articles, setArticles] = useState([]);
  const [search, setSearch] = useState('');
  const [sel, setSel] = useState(null);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchConstitutionIndex().then(setArticles);
  }, []);

  useEffect(() => {
    if (!sel) { setBody(''); return; }
    setLoading(true);
    fetchConstitutionArticle(sel.number).then(a => {
      setLoading(false);
      setBody((a && a.body) ? a.body : '');
    }).catch(()=>{setLoading(false); setBody('');});
  }, [sel]);

  const filtered = articles.filter(a => {
    const q = search.toLowerCase().trim();
    if (!q) return true;
    return (a.title||'').toLowerCase().includes(q)
        || (a.numeral||'').toLowerCase().includes(q)
        || String(a.number) === q
        || (a.scope||'').toLowerCase().includes(q);
  });

  // Simple markdown -> html for article body (headings, hr, bold, lists, paragraphs)
  const renderMd = (md) => {
    if (!md) return <i style={{color:'#94A3B8'}}>Текст статьи недоступен.</i>;
    const lines = md.split('\n');
    const out = [];
    let para = [];
    const flush = () => {
      if (para.length) {
        const text = para.join(' ');
        // bold **x**
        const parts = text.split(/(\*\*[^*]+\*\*)/g).map((p,i)=>{
          if (p.startsWith('**') && p.endsWith('**')) return <b key={i} style={{color:'#F8FAFC'}}>{p.slice(2,-2)}</b>;
          return <span key={i}>{p}</span>;
        });
        out.push(<p key={'p'+out.length} style={{margin:'0 0 10px 0',lineHeight:1.6,color:'#CBD5E1'}}>{parts}</p>);
        para = [];
      }
    };
    lines.forEach((ln, i) => {
      if (!ln.trim()) { flush(); return; }
      if (ln.startsWith('# ')) { flush(); out.push(<h3 key={i} style={{color:'#38BDF8',margin:'12px 0 8px',fontSize:18}}>{ln.slice(2)}</h3>); return; }
      if (ln.startsWith('## ')) { flush(); out.push(<h4 key={i} style={{color:'#F8FAFC',margin:'10px 0 6px',fontSize:15}}>{ln.slice(3)}</h4>); return; }
      if (/^---+$/.test(ln.trim())) { flush(); out.push(<hr key={i} style={{border:'none',borderTop:'1px solid #334155',margin:'12px 0'}}/>); return; }
      if (/^[-*]\s+/.test(ln)) {
        flush(); out.push(<li key={i} style={{marginLeft:18,color:'#CBD5E1',marginBottom:4}}>{ln.replace(/^[-*]\s+/,'')}</li>); return;
      }
      if (/^Version:|^Status:|^Level:|^Scope:|^Category:/i.test(ln)) {
        flush();
        const [k,...v] = ln.split(':');
        out.push(<div key={i} style={{fontSize:12,color:'#94A3B8',marginBottom:2}}><b style={{color:'#CBD5E1'}}>{k}:</b>{v.join(':')}</div>);
        return;
      }
      para.push(ln);
    });
    flush();
    return out;
  };

  return (
    <div style={{padding:'24px',color:'#F8FAFC'}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:20,flexWrap:'wrap',gap:12}}>
        <div>
          <h2 style={{margin:0,fontSize:20,fontWeight:700}}>AIOS Master Constitution ({articles.length} Articles)</h2>
          <div style={{fontSize:13,color:'#94A3B8'}}>Нажмите на статью, чтобы прочитать полный текст</div>
        </div>
        <input type="text" placeholder="Поиск: Identity, Ethics, LXII ..." value={search}
               onChange={e=>setSearch(e.target.value)}
               style={{backgroundColor:'#1E293B',border:'1px solid #334155',color:'#F8FAFC',padding:'10px 16px',borderRadius:8,width:340,fontSize:14}}/>
      </div>

      <div style={{display:'grid',gridTemplateColumns: sel ? '1fr 1.4fr' : '1fr', gap:20}}>
        <div style={{backgroundColor:'#1E293B',borderRadius:12,overflow:'hidden',maxHeight:sel?620:'none',overflowY:sel?'auto':'visible'}}>
          <table style={{width:'100%',borderCollapse:'collapse',fontSize:13}}>
            <thead>
              <tr style={{backgroundColor:'#0F172A',color:'#94A3B8',borderBottom:'1px solid #334155',position:'sticky',top:0,zIndex:1}}>
                <th style={{padding:'12px 16px',textAlign:'left'}}>#</th>
                <th style={{padding:'12px 16px',textAlign:'left'}}>Numeral</th>
                <th style={{padding:'12px 16px',textAlign:'left'}}>Title</th>
                <th style={{padding:'12px 16px',textAlign:'left'}}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(art => (
                <tr key={art.number}
                    onClick={()=>setSel(art)}
                    style={{borderBottom:'1px solid #334155',cursor:'pointer',backgroundColor:sel&&sel.number===art.number?'#0F172A':'transparent'}}>
                  <td style={{padding:'10px 16px',fontWeight:700,color:'#38BDF8'}}>{art.number}</td>
                  <td style={{padding:'10px 16px',fontWeight:600,color:'#F59E0B',fontSize:12}}>{art.numeral}</td>
                  <td style={{padding:'10px 16px',fontWeight:600}}>{art.title}</td>
                  <td style={{padding:'10px 16px'}}>
                    <span style={{backgroundColor:'#065F46',color:'#34D399',padding:'4px 10px',borderRadius:12,fontSize:11,fontWeight:700}}>
                      ✅ {art.valid ? 'Active' : 'Invalid'}
                    </span>
                  </td>
                </tr>
              ))}
              {filtered.length===0 && <tr><td colSpan={4} style={{padding:20,textAlign:'center',color:'#94A3B8',fontStyle:'italic'}}>Ничего не найдено</td></tr>}
            </tbody>
          </table>
        </div>

        {sel && (
          <div style={{backgroundColor:'#1E293B',borderRadius:12,padding:24,maxHeight:620,overflowY:'auto'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:12}}>
              <div>
                <div style={{fontSize:12,color:'#94A3B8',textTransform:'uppercase',letterSpacing:1}}>Article {sel.number} · {sel.numeral}</div>
                <h3 style={{margin:'4px 0 0',fontSize:20,color:'#38BDF8'}}>{sel.title}</h3>
                <div style={{fontSize:12,color:'#94A3B8',marginTop:4}}>{sel.level} · Scope: {sel.scope}</div>
              </div>
              <button onClick={()=>setSel(null)} style={{background:'transparent',border:'1px solid #334155',color:'#94A3B8',borderRadius:6,padding:'4px 10px',cursor:'pointer',fontSize:16}}>✕</button>
            </div>
            <hr style={{border:'none',borderTop:'1px solid #334155',margin:'12px 0 16px'}}/>
            {loading ? <div style={{color:'#94A3B8'}}>Загрузка...</div> : renderMd(body)}
          </div>
        )}
      </div>
    </div>
  );
}
