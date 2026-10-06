import React from 'react';
import { StateSnapshot, PlanDiffExplanation } from '../types';
import { RefreshCw } from 'lucide-react';

interface Props {
  state: StateSnapshot | null;
  explanation: PlanDiffExplanation | null;
}

export const TimelinePanel: React.FC<Props> = ({ state, explanation }) => {
  if (!state) return <div className="card">Loading event timeline...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div className="card-title">
          <RefreshCw size={18} color="#06b6d4" />
          <span>Latest Plan Transition & Diff Explanation</span>
        </div>

        {explanation ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem' }}>
              <div>State Version: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>v{explanation.state_version}</span></div>
              <div>Objective Delta: <span style={{ fontFamily: 'var(--font-mono)', color: explanation.objective_change >= 0 ? '#34d399' : '#fb7185' }}>{explanation.objective_change >= 0 ? `+${explanation.objective_change}` : explanation.objective_change}</span></div>
              <div>Plan Churn Score: <span style={{ fontFamily: 'var(--font-mono)', color: '#fbbf24' }}>{(explanation.plan_churn_score * 100).toFixed(1)}%</span></div>
            </div>

            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>Binding Constraints:</div>
              {explanation.binding_constraints.map((c, i) => (
                <div key={i} style={{ fontSize: '0.8rem', color: '#fb7185', background: 'rgba(244,63,94,0.1)', padding: '0.4rem 0.75rem', borderRadius: '6px', marginBottom: '0.3rem' }}>
                  • {c}
                </div>
              ))}
            </div>

            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>Reassignments Rationale:</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {explanation.reassigned_tasks.slice(0, 5).map((r, i) => (
                  <div key={i} style={{ background: 'var(--bg-glass)', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
                    <div style={{ fontWeight: 600, color: '#60a5fa' }}>Task {r.task_id} ({r.reassignment_type})</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.2rem' }}>
                      {r.primary_reasons.join(' | ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            No recent plan transition. Click 'Replan' to generate.
          </div>
        )}
      </div>
    </div>
  );
};
