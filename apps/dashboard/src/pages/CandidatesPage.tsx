import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCandidates } from '../api';
import type { CandidateSummary } from '../api';
import { StatusBadge } from './StatusPage';

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCandidates().then(setCandidates).catch(() => setCandidates([])).finally(() => setLoading(false));
  }, []);

  const filtered = filter ? candidates.filter(c => c.domain === filter || c.status === filter) : candidates;

  return (
    <div>
      <h1>Candidates</h1>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span className="meta">Filter:</span>
        {['', 'indexing', 'partitioning', 'compression', 'storage_layout', 'execution_config'].map(d => (
          <button key={d} onClick={() => setFilter(d)}
            style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid #374151', background: filter === d ? '#1d4ed8' : '#1f2937', color: 'white', cursor: 'pointer', fontSize: 12 }}>
            {d || 'All'}
          </button>
        ))}
      </div>

      {loading ? <div className="loading">Loading...</div> : (
        <div className="card">
          {filtered.length === 0 ? (
            <div className="loading">No candidates found.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Improvement</th>
                  <th>Risk</th>
                  <th>Confidence</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id}>
                    <td><Link to={`/candidates/${c.id}`}>{c.title}</Link></td>
                    <td><span className={`badge badge-${c.domain === 'indexing' ? 'blue' : c.domain === 'partitioning' ? 'yellow' : 'gray'}`}>{c.domain}</span></td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>{c.predicted_improvement != null ? `${c.predicted_improvement.toFixed(1)}%` : '-'}</td>
                    <td className="meta">-</td>
                    <td className="meta">-</td>
                    <td className="meta">{new Date(c.timestamp).toLocaleString()}</td>
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
