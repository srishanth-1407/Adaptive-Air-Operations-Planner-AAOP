"""
Unit tests for Plan Explanation Engine (optimize/explain.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from state.models import StateSnapshot
from generator.schemas import EventSchema
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer
from optimize.explain import PlanExplainer


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "explain_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_explain_diff_initial_plan(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    solver = CPSatOptimizer()
    plan = solver.solve(snapshot)

    explanation = PlanExplainer.explain_diff(old_plan=None, new_plan=plan, snapshot=snapshot)

    assert explanation.plan_id_old == "NONE"
    assert explanation.plan_id_new == plan.plan_id
    assert len(explanation.newly_assigned_tasks) == len(plan.assignments)
    assert explanation.objective_change == plan.metrics.objective_value


def test_explain_diff_asset_failure_reassignment(scenario_dir):
    store = LiveStateStore()
    snapshot_0 = store.initialize_from_parquet_dir(scenario_dir)

    solver = CPSatOptimizer()
    plan_0 = solver.solve(snapshot_0)

    # Pick an assigned task and fail its asset
    assigned_t = plan_0.assignments[0]
    failed_asset_id = assigned_t.asset_id
    target_task_id = assigned_t.task_id

    event = EventSchema(
        event_id="E-EX-1",
        timestamp=2.0,
        kind="ASSET_UNAVAILABLE",
        payload={"asset_id": failed_asset_id},
    )
    snapshot_1 = store.process_event(event)
    plan_1 = solver.solve(snapshot_1, previous_plan=plan_0)

    explanation = PlanExplainer.explain_diff(old_plan=plan_0, new_plan=plan_1, snapshot=snapshot_1)

    assert explanation.state_version == 1
    assert len(explanation.binding_constraints) > 0

    # Verify reassignment reason mentions failed asset
    reassigned_rec = next((r for r in explanation.reassigned_tasks if r.task_id == target_task_id), None)
    assert reassigned_rec is not None
    assert failed_asset_id in str(reassigned_rec.primary_reasons)
