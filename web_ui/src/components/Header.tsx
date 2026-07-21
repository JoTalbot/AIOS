import React from 'react';
import { SystemHealth } from '../types';

interface HeaderProps {
  health: SystemHealth | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  wsConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ health, activeTab, setActiveTab, wsConnected }) => {
  const tabs = [
    { id: 'overview', label: '📊 System Overview' },
    { id: 'safety', label: '🛡 Safety Dashboard' },
    { id: 'swarm', label: '🤖 Agent Swarm' },
    { id: 'constitution', label: '📜 Constitution (67 Articles)' },
    { id: 'kg', label: '🕸 Knowledge Graph' },
    { id: 'ml', label: '🧠 ML Registry & Serving' }
  ];

  return (
    <header style={styles.header}>
      <div style={styles.branding}>
        <div style={styles.logoBadge}>AIOS</div>
        <div>
          <h1 style={styles.title}>Autonomous Intelligence Operating System</h1>
          <div style={styles.subTitle}>v4.2.0-alpha Executive Control Hub</div>
        </div>
      </div>

      <nav style={styles.nav}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tabButton,
              ...(activeTab === tab.id ? styles.activeTab : {})
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div style={styles.statusGroup}>
        <div style={styles.badge}>
          <span style={{ ...styles.dot, backgroundColor: wsConnected ? '#10B981' : '#F59E0B' }}></span>
          {wsConnected ? 'Live WS' : 'SSE Polling'}
        </div>
        <div style={styles.badge}>
          <span style={{ ...styles.dot, backgroundColor: health?.status === 'ok' ? '#10B981' : '#EF4444' }}></span>
          {health?.status ? health.status.toUpperCase() : 'CONNECTING'}
        </div>
      </div>
    </header>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 28px',
    backgroundColor: '#0F172A',
    borderBottom: '1px solid #1E293B',
    color: '#F8FAFC'
  },
  branding: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px'
  },
  logoBadge: {
    backgroundColor: '#3B82F6',
    color: '#FFFFFF',
    fontWeight: 800,
    fontSize: '20px',
    padding: '8px 14px',
    borderRadius: '8px',
    letterSpacing: '1px'
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 700,
    color: '#F8FAFC'
  },
  subTitle: {
    fontSize: '12px',
    color: '#94A3B8'
  },
  nav: {
    display: 'flex',
    gap: '8px'
  },
  tabButton: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#94A3B8',
    padding: '8px 14px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease'
  },
  activeTab: {
    backgroundColor: '#1E293B',
    color: '#38BDF8',
    borderBottom: '2px solid #38BDF8'
  },
  statusGroup: {
    display: 'flex',
    gap: '10px'
  },
  badge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#1E293B',
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#CBD5E1'
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%'
  }
};
