const API_BASE = 'http://127.0.0.1:8080/api';

export interface Status {
  service: string;
  status: string;
  uptime: number;
  version: string;
}

export interface CandidateSummary {
  id: string;
  title: string;
  domain: string;
  status: string;
  timestamp: string;
  predicted_improvement: number | null;
}

export interface CandidateDetail {
  candidate: any;
  validation_report: any;
  deployments: any[];
}

export async function fetchStatus(): Promise<Status> {
  const r = await fetch(`${API_BASE}/status`);
  return r.json();
}

export async function fetchCandidates(domain?: string, status?: string): Promise<CandidateSummary[]> {
  const params = new URLSearchParams();
  if (domain) params.set('domain', domain);
  if (status) params.set('status', status);
  const r = await fetch(`${API_BASE}/candidates?${params}`);
  return r.json();
}

export async function fetchCandidate(id: string): Promise<CandidateDetail> {
  const r = await fetch(`${API_BASE}/candidates/${id}`);
  return r.json();
}

export async function fetchDeployments(): Promise<any[]> {
  const r = await fetch(`${API_BASE}/deployments`);
  return r.json();
}

export async function fetchRollbacks(): Promise<any[]> {
  const r = await fetch(`${API_BASE}/rollbacks`);
  return r.json();
}
