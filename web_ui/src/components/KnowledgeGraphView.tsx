import React, { useEffect, useState } from 'react';
import { fetchKnowledgeGraph } from '../services/aiosApi';
import { KnowledgeGraphData } from '../types';

export const KnowledgeGraphView: React.FC = () => {
  const [kg, setKg] = useState<KnowledgeGraphData | null>(null);

  useEffect(() => {
    fetchKnowledgeGraph().then(setKg);
  }, []);

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>Executive Knowledge Graph Visualizer</h2>
      <div style={{ fontSize: '13px', color: '#94A3B8', marginBottom: '20px' }}>
        Semantic relations across Agents, Constitutional Rules, Vector Stores, and ML Models
      </div>

      <div style={{ backgroundColor: '#1E293B', padding: '24px', borderRadius: '12px', minHeight: '380px' }}>
        <svg width="100%" height="320" style={{ backgroundColor: '#0F172A', borderRadius: '8px' }}>
          {/* Edge Lines */}
          <line x1="150" y1="160" x2="380" y2="80" stroke="#38BDF8" strokeWidth="2" strokeDasharray="4" />
          <line x1="150" y1="160" x2="380" y2="240" stroke="#10B981" strokeWidth="2" />
          <line x1="380" y1="80" x2="620" y2="160" stroke="#A855F7" strokeWidth="2" />
          <line x1="380" y1="240" x2="620" y2="160" stroke="#F59E0B" strokeWidth="2" />

          {/* Nodes */}
          <g transform="translate(150, 160)">
            <circle r="30" fill="#3B82F6" />
            <text textAnchor="middle" dy="5" fill="#FFF" fontSize="12" fontWeight="bold">Orchestrator</text>
          </g>

          <g transform="translate(380, 80)">
            <circle r="28" fill="#10B981" />
            <text textAnchor="middle" dy="5" fill="#FFF" fontSize="11" fontWeight="bold">Constitution</text>
          </g>

          <g transform="translate(380, 240)">
            <circle r="28" fill="#A855F7" />
            <text textAnchor="middle" dy="5" fill="#FFF" fontSize="11" fontWeight="bold">Vector Memory</text>
          </g>

          <g transform="translate(620, 160)">
            <circle r="28" fill="#F59E0B" />
            <text textAnchor="middle" dy="5" fill="#FFF" fontSize="11" fontWeight="bold">ML Scorer</text>
          </g>
        </svg>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '20px' }}>
          {kg?.nodes.map(n => (
            <div key={n.id} style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#38BDF8' }}>{n.label}</div>
              <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '4px' }}>TYPE: {n.type.toUpperCase()}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
