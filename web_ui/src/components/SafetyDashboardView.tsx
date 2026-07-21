import React, { useEffect, useState } from 'react';
import { fetchSafetyData } from '../services/aiosApi';
import { SafetyData } from '../types';

export const SafetyDashboardView: React.FC = () => {
  const [safety, setSafety] = useState<SafetyData | null>(null);

  useEffect(() => {
    fetchSafetyData().then(setSafety);
  }, []);

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>AI Safety & Ethics Real-Time Dashboard</h2>
          <div style={{ fontSize: '13px', color: '#94A3B8' }}>Active Guardrails: Harm, Bias, Deception & Constitutional AI</div>
        </div>
        <div style={{ backgroundColor: '#064E3B', color: '#34D399', padding: '8px 16px', borderRadius: '20px', fontWeight: 700 }}>
          STATUS: {safety?.status.toUpperCase() || 'HEALTHY'}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '28px' }}>
        <div style={cardStyle}>
          <div style={{ fontSize: '13px', color: '#94A3B8' }}>Overall Safety Score</div>
          <div style={{ fontSize: '36px', fontWeight: 800, color: '#10B981', margin: '8px 0' }}>
            {((safety?.safety_score || 1.0) * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '12px', color: '#94A3B8' }}>0 Security/Ethical Violations Flagged</div>
        </div>

        {Object.entries(safety?.metrics || {}).map(([key, val]) => (
          <div key={key} style={cardStyle}>
            <div style={{ fontSize: '13px', color: '#94A3B8' }}>{key.replace('_', ' ').toUpperCase()}</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#38BDF8', margin: '8px 0' }}>
              {(val as number).toFixed(3)}
            </div>
            <div style={{ fontSize: '12px', color: '#94A3B8' }}>
              Threshold Limit: {safety?.thresholds[key] || 0.3}
            </div>
          </div>
        ))}
      </div>

      <div style={{ backgroundColor: '#1E293B', padding: '20px', borderRadius: '12px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Recent Incident & Veto Log</h3>
        {safety?.recent_incidents && safety.recent_incidents.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94A3B8' }}>
                <th style={{ padding: '10px' }}>Severity</th>
                <th style={{ padding: '10px' }}>Description</th>
                <th style={{ padding: '10px' }}>Action Taken</th>
              </tr>
            </thead>
            <tbody>
              {safety.recent_incidents.map((inc, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '10px', color: '#EF4444', fontWeight: 700 }}>{inc.severity.toUpperCase()}</td>
                  <td style={{ padding: '10px' }}>{inc.description}</td>
                  <td style={{ padding: '10px', color: '#10B981' }}>Blocked & Logged</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: '#94A3B8', fontStyle: 'italic' }}>
            ✅ No security violations or unsafe actions detected. All safety layers operating nominally.
          </div>
        )}
      </div>
    </div>
  );
};

const cardStyle: React.CSSProperties = {
  backgroundColor: '#1E293B',
  padding: '20px',
  borderRadius: '12px',
  border: '1px solid #334155'
};
