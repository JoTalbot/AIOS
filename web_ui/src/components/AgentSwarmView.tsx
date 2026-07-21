import React, { useEffect, useState } from 'react';
import { fetchAgents } from '../services/aiosApi';
import { AgentProfile } from '../types';

export const AgentSwarmView: React.FC = () => {
  const [agents, setAgents] = useState<AgentProfile[]>([]);

  useEffect(() => {
    fetchAgents().then(setAgents);
  }, []);

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>Active Multi-Agent Swarm Topology</h2>
      <div style={{ fontSize: '13px', color: '#94A3B8', marginBottom: '20px' }}>
        Dynamic Level 1-5 Autonomy Regulation & Inter-Agent Delegation
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {agents.map(ag => (
          <div key={ag.agent_id} style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#38BDF8' }}>{ag.name}</div>
              <span style={{
                backgroundColor: ag.status === 'executing' ? '#065F46' : ag.status === 'thinking' ? '#1E40AF' : '#374151',
                color: '#FFF', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700
              }}>
                {ag.status.toUpperCase()}
              </span>
            </div>

            <div style={{ fontSize: '13px', color: '#CBD5E1', marginTop: '8px' }}>Role: <strong>{ag.role}</strong></div>
            
            <div style={{ marginTop: '16px', backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#94A3B8' }}>Autonomy Level</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#F59E0B' }}>
                Level {ag.autonomy_level} ({ag.autonomy_label})
              </div>
            </div>

            <div style={{ marginTop: '12px', fontSize: '12px', color: '#94A3B8', display: 'flex', justifyContent: 'space-between' }}>
              <span>Completed Tasks: <strong>{ag.completed_tasks}</strong></span>
              <span>ID: {ag.agent_id}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
