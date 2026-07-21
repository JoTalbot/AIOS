import React, { useEffect, useState } from 'react';
import { fetchModels } from '../services/aiosApi';
import { MLModelInfo } from '../types';

export const MLModelRegistryView: React.FC = () => {
  const [models, setModels] = useState<MLModelInfo[]>([]);

  useEffect(() => {
    fetchModels().then(setModels);
  }, []);

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>ML Model Registry & Serving Platform</h2>
      <div style={{ fontSize: '13px', color: '#94A3B8', marginBottom: '20px' }}>
        ONNX & Scikit-Learn Model Versioning, Stage Promotion & A/B Traffic Routing
      </div>

      <div style={{ backgroundColor: '#1E293B', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#0F172A', color: '#94A3B8', borderBottom: '1px solid #334155' }}>
              <th style={{ padding: '12px 16px' }}>Model Name</th>
              <th style={{ padding: '12px 16px' }}>Version</th>
              <th style={{ padding: '12px 16px' }}>Framework</th>
              <th style={{ padding: '12px 16px' }}>Stage</th>
              <th style={{ padding: '12px 16px' }}>SHA256 Checksum</th>
              <th style={{ padding: '12px 16px' }}>Metrics</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                <td style={{ padding: '12px 16px', fontWeight: 700, color: '#38BDF8' }}>{m.name}</td>
                <td style={{ padding: '12px 16px', fontWeight: 600 }}>{m.version}</td>
                <td style={{ padding: '12px 16px', color: '#A855F7', textTransform: 'uppercase', fontSize: '12px', fontWeight: 700 }}>{m.framework}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ backgroundColor: m.stage === 'production' ? '#065F46' : '#1E40AF', color: '#FFF', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                    {m.stage.toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#94A3B8' }}>{m.sha256}</td>
                <td style={{ padding: '12px 16px', color: '#CBD5E1' }}>
                  {Object.entries(m.eval_metrics || {}).map(([k, v]) => `${k}: ${v}`).join(' | ') || 'Untested'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
