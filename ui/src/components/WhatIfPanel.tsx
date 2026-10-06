import React, { useState } from 'react';
import { StateSnapshot, WhatIfResponse } from '../types';
import { runWhatIf } from '../api';
import { GitBranch, AlertCircle, Play } from 'lucide-react';

interface Props {
  state: StateSnapshot | null;
}

export const WhatIfPanel: React.FC<Props> = ({ state }) => {
  const [selectedAsset, setSelectedAsset] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhatIfResponse | null>(null);

  if (!state) return <div className="card">Loading state...</div>;

  const assets = Object.values(state.assets);

  const handleRunWhatIf = async () => {
    setLoading(true);
    try {
      const payload: any = {};
      if (selectedAsset) payload.remove_asset_id = selectedAsset;
      const res = await runWhatIf(payload);
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div className="card-title">
          <GitBranch size={18} color="#06b6d4" />
          <span>What-If Hypothetical Scenario Branch Sandbox</span>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginTop: '1rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Simulate Asset Failure:
          </label>
          <select
            value={selectedAsset}
            onChange={(e) => setSelectedAsset(e.target.value)}
            style={{
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '0.4rem 0.8rem',
              fontSize: '0.85rem',
            }}
          >
            <option value="">-- None --</option>
            {assets.map((a) => (
              <option key={a.asset_id} value={a.asset_id}>
                {a.asset_id} ({a.asset_type})
              </option>
            ))}
          </select>

          <button
            onClick={handleRunWhatIf}
            disabled={loading}
            className="nav-btn active"
            style={{ padding: '0.45rem 1.2rem', fontSize: '0.85rem' }}
          >
            <Play size={14} />
            {loading ? 'Evaluating...' : 'Simulate What-If Branch'}
          </button>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          * What-If analysis runs on a isolated deepcopy branch state and does NOT mutate live operations.
        </div>
      </div>

      {result ? (
        <div className="card">
          <div className="card-title">
            <AlertCircle size={18} color="#fbbf24" />
            <span>Hypothetical Impact Summary</span>
          </div>

          <div className="grid-3" style={{ marginTop: '0.75rem' }}>
            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Objective Delta</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: result.objective_difference >= 0 ? '#34d399' : '#fb7185' }}>
                {result.objective_difference >= 0 ? `+${result.objective_difference}` : result.objective_difference}
              </div>
            </div>

            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Coverage Delta</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: result.coverage_difference >= 0 ? '#34d399' : '#fb7185' }}>
                {(result.coverage_difference * 100).toFixed(2)}%
              </div>
            </div>

            <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Hypothetical Plan Churn</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fbbf24' }}>
                {(result.plan_churn_score * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
