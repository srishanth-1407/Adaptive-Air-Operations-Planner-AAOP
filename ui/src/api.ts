import {
  StateSnapshot,
  AllocationPlan,
  WhatIfResponse,
  AssetState,
  TaskState,
} from './types';

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchState(): Promise<StateSnapshot> {
  const res = await fetch(`${API_BASE}/state`);
  return res.json();
}

export async function fetchAssets(): Promise<AssetState[]> {
  const res = await fetch(`${API_BASE}/assets`);
  return res.json();
}

export async function fetchTasks(): Promise<TaskState[]> {
  const res = await fetch(`${API_BASE}/tasks`);
  return res.json();
}

export async function fetchPlan(): Promise<AllocationPlan> {
  const res = await fetch(`${API_BASE}/plan`);
  return res.json();
}

export async function triggerReplan(solverType: string = 'CP_SAT_ML', timeLimit: number = 2.0) {
  const res = await fetch(`${API_BASE}/replan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ solver_type: solverType, time_limit_sec: timeLimit }),
  });
  return res.json();
}

export async function runWhatIf(requestData: any): Promise<WhatIfResponse> {
  const res = await fetch(`${API_BASE}/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData),
  });
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  return res.json();
}
