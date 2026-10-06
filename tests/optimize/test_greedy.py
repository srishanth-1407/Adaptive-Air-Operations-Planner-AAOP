"""
Unit and integration tests for Greedy Baseline Allocator (optimize/greedy.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "greedy_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_greedy_allocator_small_scenario(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    allocator = GreedyAllocator()
    plan = allocator.solve(snapshot)

    assert plan.solver_type == "GREEDY"
    assert len(plan.assignments) > 0
    assert plan.metrics.priority_weighted_coverage > 0.0
    assert plan.metrics.high_priority_coverage > 0.0
    assert plan.metrics.runtime_ms >= 0.0

    # Ensure assigned tasks match total tasks count
    total = len(plan.assignments) + len(plan.unassigned_tasks)
    assert total == len(snapshot.tasks)


def test_greedy_allocator_no_available_assets(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    # Set all assets unavailable
    for asset in snapshot.assets.values():
        asset.status = "UNAVAILABLE"
        asset.availability = 0.0

    allocator = GreedyAllocator()
    plan = allocator.solve(snapshot)

    assert len(plan.assignments) == 0
    assert len(plan.unassigned_tasks) == len(snapshot.tasks)
    assert plan.metrics.priority_weighted_coverage == 0.0
    assert plan.metrics.high_priority_coverage == 0.0
