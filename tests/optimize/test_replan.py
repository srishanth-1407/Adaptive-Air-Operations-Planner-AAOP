"""
Unit and integration tests for Dynamic Replanning Engine (optimize/replan.py).
"""

import pytest
from generator.schemas import EventSchema
from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.replan import ReplanTriggerEvaluator, DynamicReplanner


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "replan_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_replan_trigger_evaluator():
    store = LiveStateStore()
    v0_state = store.initialize_from_parquet_dir("data/scenarios/run_001")

    # Critical asset failure event -> MUST trigger replan
    e1 = EventSchema(
        event_id="E-T1",
        timestamp=1.0,
        kind="ASSET_UNAVAILABLE",
        payload={"asset_id": "A-0001"},
    )
    should, reason = ReplanTriggerEvaluator.should_replan(e1, v0_state)
    assert should is True
    assert "unavailable" in reason

    # Minor task arrival (priority 1) -> Should NOT trigger replan
    e2 = EventSchema(
        event_id="E-T2",
        timestamp=2.0,
        kind="NEW_TASK",
        payload={"task_id": "T-MINOR", "priority": 1},
    )
    should, _ = ReplanTriggerEvaluator.should_replan(e2, v0_state)
    assert should is False

    # High-priority task arrival (priority 5) -> MUST trigger replan
    e3 = EventSchema(
        event_id="E-T3",
        timestamp=3.0,
        kind="NEW_TASK",
        payload={"task_id": "T-URGENT", "priority": 5},
    )
    should, _ = ReplanTriggerEvaluator.should_replan(e3, v0_state)
    assert should is True


def test_dynamic_replanner_end_to_end(scenario_dir):
    from ingest.replay import EventReplayer

    store = LiveStateStore()
    store.initialize_from_parquet_dir(scenario_dir)

    replanner = DynamicReplanner(store=store)
    replayer = EventReplayer(f"{scenario_dir}/events.jsonl")

    replans_triggered = 0
    total_events = 0

    for event in replayer.replay(speed_factor=0, max_events=30):
        total_events += 1
        res = replanner.handle_event(event)

        assert res["state_version"] == total_events
        assert res["event_to_plan_latency_ms"] >= 0.0

        if res["replan_triggered"]:
            replans_triggered += 1
            assert res["current_plan"] is not None
            assert res["cpsat_solve_time_ms"] >= 0.0

    assert replans_triggered > 0
    assert len(replanner.replan_history) == total_events
