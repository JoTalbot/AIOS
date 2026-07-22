import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { OverviewView } from './components/OverviewView';
import { SafetyDashboardView } from './components/SafetyDashboardView';
import { AgentSwarmView } from './components/AgentSwarmView';
import { ConstitutionViewer } from './components/ConstitutionViewer';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { MLModelRegistryView } from './components/MLModelRegistryView';
import { AndroidFleetView } from './components/AndroidFleetView';
import { MarketplaceView } from './components/MarketplaceView';
import { fetchHealth, fetchStats } from './services/aiosApi';
import { SystemHealth, SystemStats } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const loadData = () => {
      fetchHealth().then(setHealth).catch(() => setHealth({ status: 'degraded', version: '9.1.0', timestamp: Date.now() }));
      fetchStats().then(setStats).catch(() => {});
    };

    loadData();
    const interval = setInterval(loadData, 5000);

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
    } catch (e) {
      setWsConnected(false);
    }

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ backgroundColor: '#0F172A', minHeight: '100vh', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Header health={health} activeTab={activeTab} setActiveTab={setActiveTab} wsConnected={wsConnected} />

      <main style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {activeTab === 'overview' && <OverviewView stats={stats} />}
        {activeTab === 'android' && <AndroidFleetView />}
        {activeTab === 'marketplace' && <MarketplaceView />}
        {activeTab === 'safety' && <SafetyDashboardView />}
        {activeTab === 'swarm' && <AgentSwarmView />}
        {activeTab === 'constitution' && <ConstitutionViewer />}
        {activeTab === 'kg' && <KnowledgeGraphView />}
        {activeTab === 'ml' && <MLModelRegistryView />}
      </main>
    </div>
  );
}

export default App;
