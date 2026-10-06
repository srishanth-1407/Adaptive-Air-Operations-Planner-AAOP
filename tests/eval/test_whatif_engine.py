"""
Unit and integration tests for What-If Analysis Engine (eval/whatif_engine.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.solver import CPSatOptimizer
from eval.whatif_engine import WhatIfEngine, WhatIfHypothesis


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "whatif_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_whatif_engine_resource_removal_isolation(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    solver = CPSatOptimizer()
    current_plan = solver.solve(snapshot)

    engine = WhatIfEngine()
    hypothesis = WhatIfHypothesis(remove_asset_id="A-0001", time_limit_sec=1.0)

    res = engine.evaluate_hypothesis(snapshot, current_plan, hypothesis)

    assert "Removed resource A-0001" in res.hypothesis_summary
    assert res.baseline_plan_id == current_plan.plan_id
    assert res.whatif_plan_id != current_plan.plan_id

    # VERIFY ZERO LIVE STATE MUTATION: A-0001 MUST STILL BE AVAILABLE IN LIVE STORE!
    assert store.get_current_state().assets["A-0001"].status == "AVAILABLE"


def test_whatif_engine_task_injection(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    solver = CPSatOptimizer()
    current_plan = solver.solve(snapshot)

    engine = WhatIfEngine()
    hypothesis = WhatIfHypothesis(
        add_task={
            "task_id": "T-URGENT-INJECT",
            "priority": 5,
            "required_resource_type": "LIGHT_TRANSPORT",
        },
        time_limit_sec=1.0,
    )

    res = engine.evaluate_hypothesis(snapshot, current_plan, hypothesis)

    assert any("Injected high-priority task" in s for s in res.hypothesis_summary)
    assert res.whatif_metrics.tasks_served > 0

    # Ensure live state was NOT modified
    assert "T-URGENT-INJECT" not in store.get_current_state().tasks
