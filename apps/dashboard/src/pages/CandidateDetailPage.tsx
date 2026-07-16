import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchCandidate } from '../api';
import type { CandidateDetail } from '../api';
import { StatusBadge } from './StatusPage';

export default function CandidateDetailPage() {
  const { id } = useParams();
  const [data, setData] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchCandidate(id).then(setData).catch(() => null).finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) return <div className="loading">Loading candidate...</div>;
  if (!data) return <div className="error">Candidate not found.</div>;

  const { candidate, validation_report, deployments } = data;

  return (
    <div>
      <h1>{candidate.title}</h1>
      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div className="stat"><div className="stat-label">Domain</div><div className="stat-value" style={{ fontSize: 16 }}>{candidate.domain}</div></div>
        <div className="stat"><div className="stat-label">Status</div><div><StatusBadge status={candidate.status} /></div></div>
        {candidate.predicted_improvement != null && (
          <div className="stat"><div className="stat-label">Predicted Improvement</div><div className="stat-value ok">{candidate.predicted_improvement.toFixed(1)}%</div></div>
        )}
        {candidate.predicted_risk != null && (
          <div className="stat"><div className="stat-label">Risk</div><div className="stat-value warn">{candidate.predicted_risk.toFixed(2)}</div></div>
        )}
      </div>

      <div className="section">
        <h2>Description</h2>
        <div className="card">{candidate.description || 'No description.'}</div>
      </div>

      {candidate.ddl_statements?.length > 0 && (
        <div className="section">
          <h2>DDL Statements</h2>
          <div className="card">
            {candidate.ddl_statements.map((stmt: any, i: number) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <div className="meta" style={{ marginBottom: 4 }}>Statement #{i + 1} (order: {stmt.order})</div>
                <pre>{stmt.sql}</pre>
                {stmt.rollback_sql && (
                  <>
                    <div className="meta" style={{ marginTop: 8, marginBottom: 4 }}>Rollback:</div>
                    <pre style={{ color: '#f87171' }}>{stmt.rollback_sql}</pre>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {validation_report && (
        <div className="section">
          <h2>Validation Report</h2>
          <div className="card">
            <div style={{ marginBottom: 12 }}>
              <strong>Result: </strong>
              <StatusBadge status={validation_report.passed ? 'completed' : 'failed'} />
            </div>
            {validation_report.correctness_results?.length > 0 && (
              <>
                <h3>Correctness</h3>
                <table style={{ marginBottom: 12 }}>
                  <thead><tr><th>Criterion</th><th>Result</th><th>Details</th></tr></thead>
                  <tbody>
                    {validation_report.correctness_results.map((r: any, i: number) => (
                      <tr key={i}>
                        <td>{r.criterion}</td>
                        <td><StatusBadge status={r.passed ? 'completed' : 'failed'} /></td>
                        <td className="meta">{r.details || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            {validation_report.performance_results?.length > 0 && (
              <>
                <h3>Performance</h3>
                <table>
                  <thead><tr><th>Metric</th><th>Result</th><th>Baseline</th><th>Candidate</th><th>Delta</th></tr></thead>
                  <tbody>
                    {validation_report.performance_results.map((r: any, i: number) => (
                      <tr key={i}>
                        <td>{r.criterion}</td>
                        <td><StatusBadge status={r.passed ? 'completed' : 'failed'} /></td>
                        <td className="meta">{r.baseline_value ?? '-'}</td>
                        <td className="meta">{r.candidate_value ?? '-'}</td>
                        <td className="meta">{r.delta_percent != null ? `${r.delta_percent.toFixed(1)}%` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        </div>
      )}

      {deployments?.length > 0 && (
        <div className="section">
          <h2>Deployments</h2>
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Status</th>
                  <th>Health Check</th>
                  <th>Duration</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((d: any) => (
                  <tr key={d.id}>
                    <td>{d.strategy}</td>
                    <td><StatusBadge status={d.status} /></td>
                    <td>{d.health_check_passed != null ? (d.health_check_passed ? '✓' : '✗') : '-'}</td>
                    <td className="meta">{d.duration_seconds ? `${d.duration_seconds}s` : '-'}</td>
                    <td className="meta">{new Date(d.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {candidate.rejection_reason && (
        <div className="section">
          <h2>Rejection Reason</h2>
          <div className="card" style={{ borderColor: '#7f1d1d' }}>
            <span style={{ color: '#f87171' }}>{candidate.rejection_reason}</span>
          </div>
        </div>
      )}
    </div>
  );
}
