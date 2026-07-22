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
    { id: 'overview', label: '📊 Overview' },
    { id: 'android', label: '📱 Android Fleet M8' },
    { id: 'marketplace', label: '🧩 Marketplace' },
    { id: 'safety', label: '🛡 Safety' },
    { id: 'swarm', label: '🤖 Swarm' },
    { id: 'constitution', label: '📜 Constitution' },
    { id: 'kg', label: '🕸 KG' },
    { id: 'ml', label: '🧠 ML' }
  ];

  return (
    <header style={styles.header}>
      <div style={styles.branding}>
        <div style={styles.logoBadge}>AIOS</div>
        <div>
          <h1 style={styles.title}>Autonomous Intelligence Operating System</h1>
          <div style={styles.subTitle}>v9.1.0 Executive Hub — M8 Cross-App + Predictive • 1000+ tests • 67 Articles</div>
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
          {wsConnected ? 'Live WS' : 'Polling'}
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
    color: '#F8FAFC',
    flexWrap: 'wrap',
    gap: '12px'
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
    fontSize: '16px',
    fontWeight: 700,
    color: '#F8FAFC'
  },
  subTitle: {
    fontSize: '11px',
    color: '#94A3B8'
  },
  nav: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap'
  },
  tabButton: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#94A3B8',
    padding: '6px 10px',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer'
  },
  activeTab: {
    backgroundColor: '#1E293B',
    color: '#38BDF8',
    borderBottom: '2px solid #38BDF8'
  },
  statusGroup: {
    display: 'flex',
    gap: '8px'
  },
  badge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#1E293B',
    padding: '6px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#CBD5E1'
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%'
  }
};
