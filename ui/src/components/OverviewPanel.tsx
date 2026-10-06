import React from 'react';
import { StateSnapshot, AllocationPlan } from '../types';
import { Activity, ShieldAlert, CheckCircle2, Cpu, BarChart3 } from 'lucide-react';

interface Props {
  state: StateSnapshot | null;
  plan: AllocationPlan | null;
}

export const OverviewPanel: React.FC<Props> = ({ state, plan }) => {
  if (!state) return <div className="card">Loading state telemetry...</div>;

  const assets = Object.values(state.assets);
  const tasks = Object.values(state.tasks);
  const weather = Object.values(state.weather_cells);
  const airspace = Object.values(state.airspace_zones);

  const availableAssets = assets.filter((a) => a.status === 'AVAILABLE').length;
  const unavailableAssets = assets.filter((a) => a.status === 'UNAVAILABLE').length;
  const assignedTasks = tasks.filter((t) => t.status === 'ASSIGNED').length;
  const unassignedTasks = tasks.filter((t) => t.status === 'UNASSIGNED').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="grid-3">
        <div className="card">
          <div className="card-title">
            <Activity size={18} color="#06b6d4" />
            <span>State Version & Time</span>
          </div>
          <div className="metric-value">v{state.version.version}</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Simulated Hour: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{state.version.timestamp.toFixed(2)}h</span>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <CheckCircle2 size={18} color="#10b981" />
            <span>Resource Availability</span>
          </div>
          <div className="metric-value" style={{ color: '#34d399' }}>
            {availableAssets} <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/ {assets.length}</span>
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {unavailableAssets} in maintenance / breakdown
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <BarChart3 size={18} color="#3b82f6" />
            <span>Task Coverage</span>
          </div>
          <div className="metric-value" style={{ color: '#60a5fa' }}>
            {plan ? `${(plan.metrics.priority_weighted_coverage * 100).toFixed(1)}%` : 'N/A'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            {assignedTasks} assigned, {unassignedTasks} unserved
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <Cpu size={18} color="#818cf8" />
            <span>Active Asset Fleet Status</span>
          </div>
          <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.5rem' }}>Asset ID</th>
                  <th style={{ padding: '0.5rem' }}>Type</th>
                  <th style={{ padding: '0.5rem' }}>Base</th>
                  <th style={{ padding: '0.5rem' }}>Status</th>
                  <th style={{ padding: '0.5rem' }}>Maint. Hours</th>
                  <th style={{ padding: '0.5rem' }}>Utilization</th>
                </tr>
              </thead>
              <tbody>
                {assets.slice(0, 8).map((a) => (
                  <tr key={a.asset_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{a.asset_id}</td>
                    <td style={{ padding: '0.5rem' }}>{a.asset_type}</td>
                    <td style={{ padding: '0.5rem' }}>{a.base_id}</td>
                    <td style={{ padding: '0.5rem' }}>
                      <span className={a.status === 'AVAILABLE' ? 'badge badge-emerald' : 'badge badge-rose'}>
                        {a.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{a.hours_since_maintenance.toFixed(1)}h</td>
                    <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{(a.utilization * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <ShieldAlert size={18} color="#f59e0b" />
            <span>Active Active Constraints</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{ background: 'var(--bg-glass)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>Weather Hazard Cells</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{weather.length} active weather regions</div>
            </div>
            <div style={{ background: 'var(--bg-glass)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>Restricted Airspace Zones</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{airspace.length} dynamic polygon restrictions</div>
            </div>
            <div style={{ background: 'var(--bg-glass)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontWeight: '600', fontSize: '0.85rem' }}>Current Active Solver</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                {plan ? plan.solver_type : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
