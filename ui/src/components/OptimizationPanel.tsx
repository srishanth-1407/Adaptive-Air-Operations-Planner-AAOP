import React, { useState } from 'react';
import { AllocationPlan } from '../types';
import { triggerReplan } from '../api';
import { Cpu, Play, CheckCircle2 } from 'lucide-react';

interface Props {
  currentPlan: AllocationPlan | null;
  onPlanUpdate: (plan: AllocationPlan) => void;
}

export const OptimizationPanel: React.FC<Props> = ({ currentPlan, onPlanUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [selectedSolver, setSelectedSolver] = useState('CP_SAT_ML');

  const handleRunReplan = async () => {
    setLoading(true);
    try {
      const res = await triggerReplan(selectedSolver, 2.0);
      if (res.success && res.plan) {
        onPlanUpdate(res.plan);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div className="card-title" style={{ marginBottom: 0 }}>
            <Cpu size={18} color="#3b82f6" />
            <span>Solver Algorithm Controls</span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <select
              value={selectedSolver}
              onChange={(e) => setSelectedSolver(e.target.value)}
              style={{
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                padding: '0.4rem 0.8rem',
                fontFamily: 'var(--font-sans)',
                fontSize: '0.85rem',
              }}
            >
              <option value="GREEDY">Greedy Baseline</option>
              <option value="CP_SAT">OR-Tools CP-SAT (Static)</option>
              <option value="CP_SAT_ML">CP-SAT + ML (Predictive Risk-Aware)</option>
            </select>

            <button
              onClick={handleRunReplan}
              disabled={loading}
              className="nav-btn active"
              style={{ padding: '0.45rem 1.2rem', fontSize: '0.85rem' }}
            >
              <Play size={14} />
              {loading ? 'Solving...' : 'Run Replan'}
            </button>
          </div>
        </div>

        {currentPlan ? (
          <div className="grid-3" style={{ marginTop: '1rem' }}>
            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Active Solver</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>{currentPlan.solver_type}</div>
            </div>

            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Solve Time</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{currentPlan.metrics.runtime_ms.toFixed(2)} ms</div>
            </div>

            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Objective Score</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#60a5fa', fontFamily: 'var(--font-mono)' }}>{currentPlan.metrics.objective_value.toFixed(2)}</div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="card">
        <div className="card-title">
          <CheckCircle2 size={18} color="#10b981" />
          <span>Active Task Assignments ({currentPlan?.assignments.length || 0})</span>
        </div>

        <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.5rem' }}>Task ID</th>
                <th style={{ padding: '0.5rem' }}>Assigned Asset</th>
                <th style={{ padding: '0.5rem' }}>Crew</th>
                <th style={{ padding: '0.5rem' }}>Distance</th>
                <th style={{ padding: '0.5rem' }}>Travel Time</th>
                <th style={{ padding: '0.5rem' }}>Candidate Score</th>
              </tr>
            </thead>
            <tbody>
              {currentPlan?.assignments.map((a) => (
                <tr key={a.task_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)', color: '#60a5fa' }}>{a.task_id}</td>
                  <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{a.asset_id}</td>
                  <td style={{ padding: '0.5rem', color: 'var(--text-muted)' }}>{a.crew_id || 'Auto-Assigned'}</td>
                  <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{a.distance_km} km</td>
                  <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)' }}>{a.estimated_travel_hours} h</td>
                  <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)', color: '#34d399' }}>{a.candidate_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
