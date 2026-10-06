"""
Unit and integration tests for CP-SAT Optimizer (optimize/solver.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.greedy import GreedyAllocator


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "solver_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_cpsat_solver_small_scenario(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    config = OptimizerConfig(time_limit_sec=2.0)
    optimizer = CPSatOptimizer(config=config)
    plan = optimizer.solve(snapshot)

    assert "CP_SAT" in plan.solver_type
    assert len(plan.assignments) > 0
    assert plan.metrics.priority_weighted_coverage > 0.0
    assert plan.metrics.high_priority_coverage > 0.0
    assert plan.metrics.runtime_ms >= 0.0

    total = len(plan.assignments) + len(plan.unassigned_tasks)
    assert total == len(snapshot.tasks)


def test_cpsat_solver_plan_stability_churn_penalty(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    config = OptimizerConfig(weight_churn_penalty=500.0, time_limit_sec=2.0)
    optimizer = CPSatOptimizer(config=config)

    # First solve
    plan_1 = optimizer.solve(snapshot)

    # Re-solve passing previous plan 1 -> should preserve assignments to minimize churn
    plan_2 = optimizer.solve(snapshot, previous_plan=plan_1)

    # Check assignment match count
    assign_map_1 = {a.task_id: a.asset_id for a in plan_1.assignments}
    assign_map_2 = {a.task_id: a.asset_id for a in plan_2.assignments}

    same_assignments = sum(1 for t, a in assign_map_1.items() if assign_map_2.get(t) == a)
    assert same_assignments >= len(assign_map_1) - 1


def test_cpsat_solver_configurable_time_limit(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    config_fast = OptimizerConfig(time_limit_sec=0.1)
    optimizer = CPSatOptimizer(config=config_fast)
    plan = optimizer.solve(snapshot)

    assert plan.metrics.runtime_ms < 5000.0  # Should complete very quickly
