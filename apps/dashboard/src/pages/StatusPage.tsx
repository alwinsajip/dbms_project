import { useEffect, useState } from 'react';
import { fetchStatus, fetchCandidates, fetchDeployments, fetchRollbacks } from '../api';
import type { Status } from '../api';

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [rollbacks, setRollbacks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchStatus().then(setStatus).catch(() => null),
      fetchCandidates().then(setCandidates).catch(() => []),
      fetchDeployments().then(d => setDeployments(d || [])).catch(() => []),
      fetchRollbacks().then(r => setRollbacks(r || [])).catch(() => []),
    ]).finally(() => setLoading(false));
    const id = setInterval(() => {
      fetchStatus().then(setStatus).catch(() => null);
    }, 5000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <div className="loading">Loading system status...</div>;
  if (!status) return <div className="error">Cannot connect to SEDBMS API at http://127.0.0.1:8080. Make sure the system is running.</div>;

  const deployed = candidates.filter(c => c.status === 'deployed').length;
  const failed = candidates.filter(c => c.status === 'failed').length;

  return (
    <div>
      <h1>System Status</h1>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-label">Status</div>
          <div className="stat-value ok">{status.status}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Uptime</div>
          <div className="stat-value">{Math.round(status.uptime)}s</div>
        </div>
        <div className="stat">
          <div className="stat-label">Candidates</div>
          <div className="stat-value">{candidates.length}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Deployed</div>
          <div className="stat-value ok">{deployed}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Failed</div>
          <div className="stat-value warn">{failed}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Rollbacks</div>
          <div className="stat-value fail">{rollbacks.length}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Version</div>
          <div className="stat-value" style={{ fontSize: 16 }}>{status.version}</div>
        </div>
      </div>

      <div className="section">
        <h2>Recent Candidates</h2>
        <div className="card">
          {candidates.length === 0 ? (
            <div className="loading">No candidates yet. Generate a workload to trigger the system.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Improvement</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {candidates.slice(0, 10).map(c => (
                  <tr key={c.id}>
                    <td><a href={`#/candidates/${c.id}`}>{c.title}</a></td>
                    <td><span className={`badge badge-${c.domain === 'indexing' ? 'blue' : c.domain === 'partitioning' ? 'yellow' : 'gray'}`}>{c.domain}</span></td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>{c.predicted_improvement != null ? `${c.predicted_improvement.toFixed(1)}%` : '-'}</td>
                    <td className="meta">{new Date(c.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="section">
        <h2>Recent Deployments</h2>
        <div className="card">
          {deployments.length === 0 ? (
            <div className="loading">No deployments yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Candidate ID</th>
                  <th>Strategy</th>
                  <th>Status</th>
                  <th>Health Check</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {deployments.slice(0, 10).map(d => (
                  <tr key={d.id}>
                    <td className="meta">{d.candidate_id?.substring(0, 12)}...</td>
                    <td>{d.strategy}</td>
                    <td><StatusBadge status={d.status} /></td>
                    <td>{d.health_check_passed != null ? (d.health_check_passed ? '✓' : '✗') : '-'}</td>
                    <td className="meta">{new Date(d.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cls = status === 'completed' || status === 'deployed' || status === 'validated' ? 'badge-green'
    : status === 'failed' || status === 'rejected' ? 'badge-red'
    : status === 'proposed' || status === 'deploying' ? 'badge-yellow'
    : 'badge-gray';
  return <span className={`badge ${cls}`}>{status}</span>;
}
