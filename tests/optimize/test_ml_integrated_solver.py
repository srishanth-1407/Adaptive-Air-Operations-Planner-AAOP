"""
Unit and integration tests for ML + CP-SAT Integrated Optimizer (optimize/ml_integrated_solver.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer
from optimize.ml_integrated_solver import MLIntegratedOptimizer


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "ml_solver_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_ml_integrated_optimizer(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    ml_solver = MLIntegratedOptimizer()
    plan_ml = ml_solver.solve(snapshot)

    assert "CP_SAT + ML" in plan_ml.solver_type
    assert len(plan_ml.assignments) > 0
    assert plan_ml.metrics.priority_weighted_coverage > 0.0


def test_three_way_ablation_comparison(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    # 1. Greedy
    greedy = GreedyAllocator()
    plan_g = greedy.solve(snapshot)

    # 2. CP-SAT Static
    cpsat = CPSatOptimizer()
    plan_cp = cpsat.solve(snapshot)

    # 3. CP-SAT + ML
    ml_solver = MLIntegratedOptimizer()
    plan_ml = ml_solver.solve(snapshot)

    assert plan_g.solver_type == "GREEDY"
    assert "CP_SAT" in plan_cp.solver_type
    assert "CP_SAT + ML" in plan_ml.solver_type

    # All solvers produce valid metrics
    for p in [plan_g, plan_cp, plan_ml]:
        assert 0.0 <= p.metrics.priority_weighted_coverage <= 1.0
        assert p.metrics.runtime_ms >= 0.0
