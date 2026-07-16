import { useEffect, useState } from 'react';
import { fetchDeployments, fetchRollbacks } from '../api';
import { StatusBadge } from './StatusPage';

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<any[]>([]);
  const [rollbacks, setRollbacks] = useState<any[]>([]);
  const [tab, setTab] = useState<'deployments' | 'rollbacks'>('deployments');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchDeployments().then(setDeployments).catch(() => []),
      fetchRollbacks().then(setRollbacks).catch(() => []),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Deployments & Rollbacks</h1>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <button onClick={() => setTab('deployments')}
          style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #374151', background: tab === 'deployments' ? '#1d4ed8' : '#1f2937', color: 'white', cursor: 'pointer' }}>
          Deployments ({deployments.length})
        </button>
        <button onClick={() => setTab('rollbacks')}
          style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #374151', background: tab === 'rollbacks' ? '#1d4ed8' : '#1f2937', color: 'white', cursor: 'pointer' }}>
          Rollbacks ({rollbacks.length})
        </button>
      </div>

      {loading ? <div className="loading">Loading...</div> : (
        <div className="card">
          {tab === 'deployments' && (
            deployments.length === 0 ? <div className="loading">No deployments yet.</div>
            : <table>
                <thead>
                  <tr>
                    <th>Candidate ID</th>
                    <th>Strategy</th>
                    <th>Status</th>
                    <th>Health Check</th>
                    <th>Duration</th>
                    <th>Error</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.map(d => (
                    <tr key={d.id}>
                      <td className="meta">{d.candidate_id?.substring(0, 12)}...</td>
                      <td>{d.strategy}</td>
                      <td><StatusBadge status={d.status} /></td>
                      <td>{d.health_check_passed != null ? (d.health_check_passed ? '✓' : '✗') : '-'}</td>
                      <td className="meta">{d.duration_seconds ? `${d.duration_seconds.toFixed(1)}s` : '-'}</td>
                      <td className="meta" style={{ color: d.error ? '#f87171' : undefined }}>{d.error || '-'}</td>
                      <td className="meta">{new Date(d.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
          )}
          {tab === 'rollbacks' && (
            rollbacks.length === 0 ? <div className="loading">No rollbacks recorded.</div>
            : <table>
                <thead>
                  <tr>
                    <th>Candidate ID</th>
                    <th>Trigger Reason</th>
                    <th>Success</th>
                    <th>Duration</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {rollbacks.map(r => (
                    <tr key={r.id}>
                      <td className="meta">{r.candidate_id?.substring(0, 12)}...</td>
                      <td><span style={{ color: '#f87171' }}>{r.trigger_reason}</span></td>
                      <td><StatusBadge status={r.success ? 'completed' : 'failed'} /></td>
                      <td className="meta">{r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : '-'}</td>
                      <td className="meta">{new Date(r.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
          )}
        </div>
      )}
    </div>
  );
}
