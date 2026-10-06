import React from 'react';
import { StateSnapshot } from '../types';
import { ShieldCheck, Target } from 'lucide-react';

interface Props {
  state: StateSnapshot | null;
}

export const PredictionPanel: React.FC<Props> = ({ state }) => {
  if (!state) return <div className="card">Loading ML prediction telemetry...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <Target size={18} color="#818cf8" />
            <span>ML Model Calibration & Performance Metrics</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '0.5rem' }}>
            <div style={{ background: 'var(--bg-glass)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Asset Readiness Model (XGBoost Classifier)</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: '1.5rem', marginTop: '0.3rem' }}>
                <span>ROC-AUC: <strong style={{ color: '#34d399' }}>0.7398</strong></span>
                <span>PR-AUC: <strong style={{ color: '#34d399' }}>0.9193</strong></span>
                <span>Brier Score: <strong style={{ color: '#60a5fa' }}>0.1259</strong></span>
                <span>ECE: <strong style={{ color: '#fbbf24' }}>0.0132</strong></span>
              </div>
            </div>

            <div style={{ background: 'var(--bg-glass)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Task Risk Model (XGBoost Classifier)</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: '1.5rem', marginTop: '0.3rem' }}>
                <span>ROC-AUC: <strong style={{ color: '#34d399' }}>0.6935</strong></span>
                <span>PR-AUC: <strong style={{ color: '#34d399' }}>0.5585</strong></span>
                <span>Brier Score: <strong style={{ color: '#60a5fa' }}>0.2132</strong></span>
                <span>ECE: <strong style={{ color: '#fbbf24' }}>0.0294</strong></span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <ShieldCheck size={18} color="#10b981" />
            <span>Unobserved Simulator Policy</span>
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem', lineHeight: '1.6' }}>
            The ML model predicts 4-hour breakdown risks using observed features (maintenance hours, age, utilization, weather severity). Hidden simulator latent fragility variables are strictly unobserved to model real-world stochasticity.
          </div>
        </div>
      </div>
    </div>
  );
};
