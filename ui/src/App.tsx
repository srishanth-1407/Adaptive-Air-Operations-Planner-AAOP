import React, { useEffect, useState } from 'react';
import { StateSnapshot, AllocationPlan, PlanDiffExplanation } from './types';
import { fetchState, fetchPlan } from './api';
import { OverviewPanel } from './components/OverviewPanel';
import { MapPanel } from './components/MapPanel';
import { TimelinePanel } from './components/TimelinePanel';
import { OptimizationPanel } from './components/OptimizationPanel';
import { PredictionPanel } from './components/PredictionPanel';
import { WhatIfPanel } from './components/WhatIfPanel';
import { LayoutDashboard, Map as MapIcon, Clock, Cpu, LineChart, GitBranch, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'map' | 'timeline' | 'optimization' | 'prediction' | 'whatif'>('overview');
  const [state, setState] = useState<StateSnapshot | null>(null);
  const [plan, setPlan] = useState<AllocationPlan | null>(null);
  const [explanation] = useState<PlanDiffExplanation | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    setRefreshing(true);
    try {
      const stateData = await fetchState();
      setState(stateData);

      const planData = await fetchPlan();
      setPlan(planData);
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <header className="navbar">
        <div className="brand">
          <Cpu size={24} color="#38bdf8" />
          <span>Adaptive Air Operations Planner (AAOP)</span>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <LayoutDashboard size={16} /> Overview
          </button>
          <button
            className={`nav-btn ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            <MapIcon size={16} /> Tactical Map
          </button>
          <button
            className={`nav-btn ${activeTab === 'timeline' ? 'active' : ''}`}
            onClick={() => setActiveTab('timeline')}
          >
            <Clock size={16} /> Event Timeline
          </button>
          <button
            className={`nav-btn ${activeTab === 'optimization' ? 'active' : ''}`}
            onClick={() => setActiveTab('optimization')}
          >
            <Cpu size={16} /> Optimization
          </button>
          <button
            className={`nav-btn ${activeTab === 'prediction' ? 'active' : ''}`}
            onClick={() => setActiveTab('prediction')}
          >
            <LineChart size={16} /> ML Risk Models
          </button>
          <button
            className={`nav-btn ${activeTab === 'whatif' ? 'active' : ''}`}
            onClick={() => setActiveTab('whatif')}
          >
            <GitBranch size={16} /> What-If Sandbox
          </button>
        </nav>

        <button
          className="nav-btn"
          onClick={loadData}
          disabled={refreshing}
          style={{ background: 'var(--bg-glass)', border: '1px solid var(--border-color)' }}
        >
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
          Refresh
        </button>
      </header>

      <main className="content-area">
        {activeTab === 'overview' && <OverviewPanel state={state} plan={plan} />}
        {activeTab === 'map' && <MapPanel state={state} plan={plan} />}
        {activeTab === 'timeline' && <TimelinePanel state={state} explanation={explanation} />}
        {activeTab === 'optimization' && <OptimizationPanel currentPlan={plan} onPlanUpdate={(p) => setPlan(p)} />}
        {activeTab === 'prediction' && <PredictionPanel state={state} />}
        {activeTab === 'whatif' && <WhatIfPanel state={state} />}
      </main>
    </div>
  );
};
