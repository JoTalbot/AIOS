import React, { useEffect, useState } from 'react';

interface DeviceStatus {
  device_id: string;
  status: string;
  package?: string;
  latency_ms?: number;
  failure_rate?: number;
  risk_score?: number;
  last_screen?: string;
}

interface WorkflowExecution {
  id: string;
  name: string;
  status: string;
  current_step: number;
  duration_ms: number;
}

export const AndroidFleetView: React.FC = () => {
  const [devices, setDevices] = useState<DeviceStatus[]>([
    { device_id: 'emulator-5554', status: 'online', package: 'ua.slando', latency_ms: 820, failure_rate: 0.04, risk_score: 0.12, last_screen: 'search_results' },
    { device_id: 'emulator-5556', status: 'online', package: 'com.instagram.android', latency_ms: 1240, failure_rate: 0.08, risk_score: 0.35, last_screen: 'feed' },
    { device_id: 'emulator-5558', status: 'offline', package: '', latency_ms: 0, failure_rate: 0, risk_score: 0.9, last_screen: '' }
  ]);

  const [workflows, setWorkflows] = useState<WorkflowExecution[]>([
    { id: 'wf_abc123', name: 'olx_to_messenger', status: 'completed', current_step: 3, duration_ms: 4520 },
    { id: 'wf_def456', name: 'broadcast_3', status: 'running', current_step: 1, duration_ms: 1200 }
  ]);

  const [predictions, setPredictions] = useState<any[]>([]);

  useEffect(() => {
    // Try fetch real data
    fetch('/api/v1/android/devices').then(r => r.json()).then(data => {
      if (data && data.devices) setDevices(data.devices);
    }).catch(()=>{});

    fetch('/api/v1/shards/stats').then(r => r.json()).then(data => {
      if (data && data.jobs) setWorkflows(data.jobs);
    }).catch(()=>{});

    // Simulate predictive data
    setPredictions([
      { device: 'emulator-5554', risk: 'low', score: 0.12, reasons: ['Система стабильна'], eta: null },
      { device: 'emulator-5556', risk: 'medium', score: 0.35, reasons: ['Высокая задержка 1240ms', 'Средний success rate 78%'], eta: 900 },
      { device: 'emulator-5558', risk: 'critical', score: 0.9, reasons: ['Устройство оффлайн', 'Критический уровень ошибок'], eta: 60 }
    ]);
  }, []);

  const getRiskColor = (score: number) => {
    if (score >= 0.7) return '#EF4444';
    if (score >= 0.5) return '#F59E0B';
    if (score >= 0.3) return '#3B82F6';
    return '#10B981';
  };

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>🤖 Android Fleet & M8 Cross-App Orchestration</h2>
      <div style={{ fontSize: '13px', color: '#94A3B8', marginBottom: '20px' }}>
        M1-M8: Execution, Driver, Registry, Fleet, AI Navigation, Observability, Cross-App, Predictive Maintenance
      </div>

      {/* Device Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px', marginBottom: '28px' }}>
        {devices.map(dev => (
          <div key={dev.device_id} style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8' }}>{dev.device_id}</div>
              <span style={{
                backgroundColor: dev.status === 'online' ? '#065F46' : '#7F1D1D',
                color: dev.status === 'online' ? '#34D399' : '#FCA5A5',
                padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700
              }}>
                {dev.status.toUpperCase()}
              </span>
            </div>

            <div style={{ marginTop: '12px', fontSize: '13px' }}>
              <div>Package: <strong style={{ color: '#F8FAFC' }}>{dev.package || '—'}</strong></div>
              <div>Last screen: <strong>{dev.last_screen || '—'}</strong></div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '16px' }}>
              <div style={{ backgroundColor: '#0F172A', padding: '10px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Latency</div>
                <div style={{ fontSize: '16px', fontWeight: 700 }}>{dev.latency_ms || 0} ms</div>
              </div>
              <div style={{ backgroundColor: '#0F172A', padding: '10px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Failure rate</div>
                <div style={{ fontSize: '16px', fontWeight: 700 }}>{((dev.failure_rate||0)*100).toFixed(1)}%</div>
              </div>
            </div>

            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '4px' }}>Risk score</div>
              <div style={{ backgroundColor: '#0F172A', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${(dev.risk_score||0)*100}%`, height: '100%', backgroundColor: getRiskColor(dev.risk_score||0) }}></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Predictive */}
        <div style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>🔮 Predictive Maintenance (M8.2)</h3>
          {predictions.map((p, idx) => (
            <div key={idx} style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px', marginBottom: '10px', borderLeft: `4px solid ${getRiskColor(p.score)}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{p.device}</strong>
                <span style={{ backgroundColor: getRiskColor(p.score), color: '#FFF', padding: '2px 8px', borderRadius: '10px', fontSize: '11px' }}>{p.risk} {Math.round(p.score*100)}%</span>
              </div>
              <div style={{ fontSize: '12px', color: '#CBD5E1', marginTop: '6px' }}>{p.reasons.join(' • ')}</div>
              {p.eta && <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '4px' }}>Predicted failure in {p.eta}s</div>}
            </div>
          ))}
        </div>

        {/* Workflows */}
        <div style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>🔗 Cross-App Workflows (M8.1)</h3>
          {workflows.map(wf => (
            <div key={wf.id} style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px', marginBottom: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong style={{ color: '#38BDF8' }}>{wf.name}</strong>
                <span style={{
                  backgroundColor: wf.status === 'completed' ? '#065F46' : wf.status === 'running' ? '#1E40AF' : '#374151',
                  color: '#FFF', padding: '2px 8px', borderRadius: '10px', fontSize: '11px'
                }}>{wf.status}</span>
              </div>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '4px' }}>ID: {wf.id} • Step {wf.current_step} • {wf.duration_ms}ms</div>
            </div>
          ))}

          <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#0F172A', borderRadius: '8px', border: '1px dashed #334155' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#F59E0B' }}>Example: OLX → Viber chain</div>
            <pre style={{ fontSize: '11px', color: '#94A3B8', marginTop: '6px', whiteSpace: 'pre-wrap' }}>
{`workflow = engine.workflow_olx_to_messenger(
  search_query="iPhone 13",
  recipient="+380..."
)
result = engine.execute(workflow)`}
            </pre>
          </div>
        </div>
      </div>

      {/* Test Generator */}
      <div style={{ marginTop: '20px', backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>🧪 Auto Test Generation (M8.3)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          <div style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700 }}>Search Flow</div>
            <div style={{ fontSize: '11px', color: '#94A3B8' }}>Tap search → Type iPhone → Assert results</div>
          </div>
          <div style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700 }}>Login Flow</div>
            <div style={{ fontSize: '11px', color: '#94A3B8' }}>Generic login with credential rotation</div>
          </div>
          <div style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700 }}>Broadcast</div>
            <div style={{ fontSize: '11px', color: '#94A3B8' }}>Multi-platform message broadcast</div>
          </div>
          <div style={{ backgroundColor: '#0F172A', padding: '12px', borderRadius: '8px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700 }}>From Recorder</div>
            <div style={{ fontSize: '11px', color: '#94A3B8' }}>JSON recording → pytest</div>
          </div>
        </div>
      </div>
    </div>
  );
};
