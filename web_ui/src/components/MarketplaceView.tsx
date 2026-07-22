import React, { useEffect, useState } from 'react';

interface Capability {
  id: string;
  name: string;
  description: string;
  author: string;
  tags: string[];
  downloads: number;
  kind: string;
}

interface PlatformPlugin {
  id: string;
  platform: string;
  version: string;
  author: string;
  verified: boolean;
  downloads: number;
}

export const MarketplaceView: React.FC = () => {
  const [caps, setCaps] = useState<Capability[]>([
    { id: 'cap1', name: 'olx-parser', description: 'OLX card parser + link extractor + SQLite', author: 'system', tags: ['olx','parser'], downloads: 124, kind: 'capability' },
    { id: 'cap2', name: 'instagram-collector', description: 'IG collector + details + Direct', author: 'system', tags: ['instagram','collector'], downloads: 89, kind: 'capability' },
    { id: 'cap3', name: 'ai-advisor-draft', description: 'AI Advisor - draft replies with approval gate', author: 'system', tags: ['ai','advisor'], downloads: 42, kind: 'capability' }
  ]);

  const [plugins, setPlugins] = useState<PlatformPlugin[]>([
    { id: 'pl1', platform: 'olx', version: '1.0.0', author: 'community', verified: true, downloads: 52 },
    { id: 'pl2', platform: 'instagram', version: '1.0.0', author: 'community', verified: true, downloads: 38 },
    { id: 'pl3', platform: 'facebook', version: '0.9.0', author: 'community', verified: false, downloads: 12 },
    { id: 'pl4', platform: 'viber', version: '1.0.0', author: 'community', verified: false, downloads: 8 }
  ]);

  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch('/api/v1/marketplace/search').then(r=>r.json()).then(d=>{
      if (d && d.capabilities) setCaps(d.capabilities);
    }).catch(()=>{});
    fetch('/api/v1/marketplace/plugins').then(r=>r.json()).then(d=>{
      if (d && d.plugins) setPlugins(d.plugins);
    }).catch(()=>{});
  }, []);

  const filtered = caps.filter(c => c.name.toLowerCase().includes(search.toLowerCase()) || c.description.toLowerCase().includes(search.toLowerCase()));

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>🧩 Capability Marketplace + Platform Plugins (H3.14)</h2>
      <div style={{ fontSize: '13px', color: '#94A3B8', marginBottom: '20px' }}>
        Publish & discover capabilities, onboarding packages (descriptor + hints + drivers) — guarded publishing
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="Search capabilities (olx, instagram, advisor...)"
          value={search}
          onChange={e=>setSearch(e.target.value)}
          style={{ backgroundColor: '#1E293B', border: '1px solid #334155', color: '#F8FAFC', padding: '10px 16px', borderRadius: '8px', width: '400px' }}
        />
        <div style={{ backgroundColor: '#1E293B', padding: '10px 16px', borderRadius: '8px', fontSize: '13px' }}>
          Total caps: <strong>{caps.length}</strong> • Plugins: <strong>{plugins.length}</strong> • Verified: <strong>{plugins.filter(p=>p.verified).length}</strong>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px' }}>Capabilities</h3>
          <div style={{ display: 'grid', gap: '12px' }}>
            {filtered.map(c=>(
              <div key={c.id} style={{ backgroundColor: '#1E293B', padding: '16px', borderRadius: '12px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <div style={{ fontWeight: 700, color: '#38BDF8' }}>{c.name}</div>
                  <span style={{ backgroundColor: '#334155', color: '#CBD5E1', padding: '2px 8px', borderRadius: '10px', fontSize: '11px' }}>{c.kind}</span>
                </div>
                <div style={{ fontSize: '13px', color: '#CBD5E1', marginTop: '6px' }}>{c.description}</div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                  {c.tags.map(t=>(
                    <span key={t} style={{ backgroundColor: '#0F172A', color: '#94A3B8', padding: '2px 8px', borderRadius: '10px', fontSize: '11px' }}>#{t}</span>
                  ))}
                </div>
                <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '8px' }}>By {c.author} • ⬇️ {c.downloads} downloads</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px' }}>Platform Plugins (H3.14)</h3>
          <div style={{ display: 'grid', gap: '12px' }}>
            {plugins.map(p=>(
              <div key={p.id} style={{ backgroundColor: '#1E293B', padding: '16px', borderRadius: '12px', border: `1px solid ${p.verified ? '#065F46' : '#334155'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontWeight: 700 }}>{p.platform} <span style={{ fontSize: '11px', color: '#94A3B8' }}>v{p.version}</span></div>
                  {p.verified ? <span style={{ backgroundColor: '#065F46', color: '#34D399', padding: '2px 8px', borderRadius: '10px', fontSize: '11px' }}>✓ Verified</span> : <span style={{ backgroundColor: '#7C2D12', color: '#FDBA74', padding: '2px 8px', borderRadius: '10px', fontSize: '11px' }}>Unverified</span>}
                </div>
                <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '6px' }}>By {p.author} • ⬇️ {p.downloads}</div>
                <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
                  <button style={{ backgroundColor: '#3B82F6', color: '#FFF', border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>Install</button>
                  <button style={{ backgroundColor: '#1E293B', color: '#94A3B8', border: '1px solid #334155', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>View YAML</button>
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '20px', backgroundColor: '#0F172A', padding: '16px', borderRadius: '8px', border: '1px dashed #334155' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#F59E0B' }}>Publish flow (guarded)</div>
            <pre style={{ fontSize: '11px', color: '#94A3B8', marginTop: '6px', whiteSpace: 'pre-wrap' }}>
{`from aios_core.marketplace import CapabilityMarketplace
mp = CapabilityMarketplace()
plugin = mp.publish_platform_plugin(
  platform="prom",
  descriptor_yaml=open("platforms/prom.yaml").read(),
  hints={"feed": "resource-id=..." },
  readme="Prom marketplace parser"
)
mp.verify_plugin(plugin.id)`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
