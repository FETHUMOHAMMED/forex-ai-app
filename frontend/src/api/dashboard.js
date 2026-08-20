// V3 Dashboard API - Clean data for React frontend
const API_BASE = 'http://localhost:8002';

export async function getV3Dashboard() {
  const res = await fetch(`${API_BASE}/v3/dashboard`);
  if (!res.ok) throw new Error('Dashboard API failed');
  return await res.json();
}

export async function getV3Health() {
  const res = await fetch(`${API_BASE}/v3/health`);
  return await res.json();
}
