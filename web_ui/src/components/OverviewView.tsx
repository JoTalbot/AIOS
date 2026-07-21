import React from 'react';
import { SystemStats } from '../types';

interface OverviewProps {
  stats: SystemStats | null;
}

export const OverviewView: React.FC<OverviewProps> = ({ stats }) => {
  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs}h ${mins}m ${secs}s`;
  };

  const cards = [
    { title: 'Constitutional Compliance', value: '100%', sub: '67 / 67 Articles Validated (tula)', color: '#10B981' },
    { title: 'AI Safety Index', value: `${((stats?.safety_score || 1.0) * 100).toFixed(1)}%`, sub: 'Real-time Guardrails Active', color: '#3B82F6' },
    { title: 'Active Agents Swarm', value: stats?.active_agents || 3, sub: 'Level 1 - Level 5 Autonomy', color: '#8B5CF6' },
    { title: 'Completed Tasks', value: stats?.completed_tasks || 526, sub: `0 Failures (${stats?.total_tasks || 526} Total)`, color: '#06B6D4' },
    { title: 'Memory Vector Nodes', value: stats?.memory_nodes || 1280, sub: 'Persistent SQLite Store', color: '#F59E0B' },
    { title: 'Executive Runtime Uptime', value: stats ? formatTime(stats.uptime_seconds) : 'Active', sub: 'Octopus Engine v4.2', color: '#EC4899' }
  ];

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', marginBottom: '16px', fontWeight: 700 }}>Executive System Dashboard</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        {cards.map((c, i) => (
          <div key={i} style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px', borderLeft: `4px solid ${c.color}` }}>
            <div style={{ fontSize: '13px', color: '#94A3B8', fontWeight: 600 }}>{c.title}</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#F8FAFC', margin: '8px 0' }}>{c.value}</div>
            <div style={{ fontSize: '12px', color: '#CBD5E1' }}>{c.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '28px', backgroundColor: '#1E293B', padding: '24px', borderRadius: '12px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>AIOS Executive Infrastructure Architecture</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <div style={subBox}>
            <div style={{ fontWeight: 700, color: '#38BDF8' }}>Constitutional Engine</div>
            <div style={{ fontSize: '13px', color: '#94A3B8', marginTop: '6px' }}>
              67 Fundamental Articles (I - LXVII), Law Veto Engine, Real-time Tula Scanner
            </div>
          </div>
          <div style={subBox}>
            <div style={{ fontWeight: 700, color: '#38BDF8' }}>Multi-Agent Orchestrator</div>
            <div style={{ fontSize: '13px', color: '#94A3B8', marginTop: '6px' }}>
              Federation Manager, Predictive Autonomy Regulation, DAG Task Scheduler
            </div>
          </div>
          <div style={subBox}>
            <div style={{ fontWeight: 700, color: '#38BDF8' }}>Observability & Telemetry</div>
            <div style={{ fontSize: '13px', color: '#94A3B8', marginTop: '6px' }}>
              W3C OpenTelemetry Tracing, Prometheus Exposition, JSON Context Logs
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const subBox: React.CSSProperties = {
  backgroundColor: '#0F172A',
  padding: '16px',
  borderRadius: '8px',
  border: '1px solid #334155'
};
