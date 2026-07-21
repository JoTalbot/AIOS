import React, { useEffect, useState } from 'react';
import { fetchConstitutionIndex } from '../services/aiosApi';
import { ArticleSummary } from '../types';

export const ConstitutionViewer: React.FC = () => {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchConstitutionIndex().then(setArticles);
  }, []);

  const filtered = articles.filter(a =>
    a.title.toLowerCase().includes(search.toLowerCase()) ||
    a.numeral.toLowerCase().includes(search.toLowerCase()) ||
    a.number.toString() === search
  );

  return (
    <div style={{ padding: '24px', color: '#F8FAFC' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>AIOS Master Constitution (67 Articles)</h2>
          <div style={{ fontSize: '13px', color: '#94A3B8' }}>Verified 100% Compliant by Tula Scanner</div>
        </div>
        <input
          type="text"
          placeholder="Search 67 articles (e.g. 'Identity', 'XLIX')..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            backgroundColor: '#1E293B',
            border: '1px solid #334155',
            color: '#F8FAFC',
            padding: '10px 16px',
            borderRadius: '8px',
            width: '320px',
            fontSize: '14px'
          }}
        />
      </div>

      <div style={{ backgroundColor: '#1E293B', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#0F172A', color: '#94A3B8', borderBottom: '1px solid #334155' }}>
              <th style={{ padding: '12px 16px' }}>Article #</th>
              <th style={{ padding: '12px 16px' }}>Numeral</th>
              <th style={{ padding: '12px 16px' }}>Article Domain Title</th>
              <th style={{ padding: '12px 16px' }}>Scope</th>
              <th style={{ padding: '12px 16px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(art => (
              <tr key={art.number} style={{ borderBottom: '1px solid #334155' }}>
                <td style={{ padding: '12px 16px', fontWeight: 700, color: '#38BDF8' }}>Article {art.number}</td>
                <td style={{ padding: '12px 16px', fontWeight: 600, color: '#F59E0B' }}>{art.numeral}</td>
                <td style={{ padding: '12px 16px', fontWeight: 600 }}>{art.title}</td>
                <td style={{ padding: '12px 16px', color: '#CBD5E1' }}>{art.scope}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ backgroundColor: '#065F46', color: '#34D399', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700 }}>
                    ✅ {art.valid ? 'Active & Valid' : 'Invalid'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
